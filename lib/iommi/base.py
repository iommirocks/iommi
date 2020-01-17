import copy
from collections import defaultdict
from functools import wraps
from typing import (
    Union,
    Any,
    Dict,
)

from django.conf import settings
from django.db.models import QuerySet
from django.http.response import HttpResponseBase, HttpResponse
from django.template import Template
from tri_declarative import (
    dispatch,
    EMPTY,
    Namespace,
    setattr_path,
    setdefaults_path,
    sort_after,
    should_show,
)
from iommi._web_compat import get_template_from_string, render_template
from tri_struct import Struct
from tri_struct._cstruct import _Struct


class GroupPathsByChildrenError(Exception):
    pass


def group_paths_by_children(*, children, data):
    results = defaultdict(dict)

    default_child = [k for k, v in children.items() if getattr(v, 'default_child', False)]
    assert len(default_child) in (0, 1), f'There can only be one default_child per level: found {default_child}'
    default_child = default_child[0] if default_child else None

    for path, value in data.items():
        first, _, rest = path.partition('/')
        if first in children:
            results[first][rest] = value
        else:
            if not default_child:
                raise GroupPathsByChildrenError(path)
            results[default_child][path] = value

    return results


class InvalidEndpointPathException(Exception):
    pass


class EndPointHandlerProxy:
    def __init__(self, func):
        self.func = func
        assert callable(func)

    def endpoint_handler(self, request, value, **kwargs):
        return self.func(request=request, value=value, **kwargs)

    def endpoint_kwargs(self):
        return {}


def setup_endpoint_proxies(endpoint: Namespace) -> Dict[str, EndPointHandlerProxy]:
    return Namespace({
        k: EndPointHandlerProxy(v)
        for k, v in endpoint.items()
    })


def find_target(*, path, root):
    assert path.startswith(DISPATCH_PATH_SEPARATOR)
    p = path[1:]
    sentinel = object()
    next_node = root
    parents = [root]

    while True:
        data = {p: sentinel}
        try:
            next_node.children
        except AttributeError:
            raise InvalidEndpointPathException(f"Invalid path {path}.\n{next_node} (of type {type(next_node)} has no attribute children so can't be traversed.\nParents so far: {parents}.\nPath left: {p}")
        children = next_node.children()
        assert children is not None
        try:
            foo = group_paths_by_children(children=children, data=data)
        except GroupPathsByChildrenError:
            raise InvalidEndpointPathException(f"Invalid path {path}.\nchildren does not contain what we're looking for, these are the keys available: {list(children.keys())}.\nParents so far: {parents}.\nPath left: {p}")

        assert len(foo) == 1
        name, rest = foo.popitem()
        p, _ = rest.popitem()
        next_node = children[name]
        if not p:
            return next_node, parents
        parents.append(next_node)


def is_response(obj):
    return isinstance(obj, HttpResponseBase)


class ResponseException(Exception):
    def __init__(self, response):
        self.response = response


def raise_on_response(result_or_response):
    if is_response(result_or_response):
        raise ResponseException(result_or_response)
    else:
        return result_or_response


# TODO: is catch_response obsolete now?
def catch_response(view_function):
    @wraps(view_function)
    def catch_response_view(*args, **kwargs):
        try:
            return view_function(*args, **kwargs)
        except ResponseException as e:
            return e.response

    return catch_response_view


# TODO: abc?
class PagePart:
    parent = None
    name = None
    default_child = None
    _is_bound = False

    @dispatch(
        context=EMPTY,
    )
    def render(self, *, context=None, render=None):
        pass

    # TODO: ick
    @dispatch(
        template_name=getattr(settings, 'TRI_BASE_TEMPLATE', 'base.html'),
        content_block_name=getattr(settings, 'TRI_CONTENT_BLOCK', 'content'),
    )
    def render_root(self, *, template_name, content_block_name, context=None):
        if context is None:
            context = {}

        content = self.render(context=context)

        assert 'content' not in context
        context['content'] = content

        template_string = '{% extends "' + template_name + '" %} {% block ' + content_block_name + ' %} {{ content }} {% endblock %}'
        return get_template_from_string(template_string).render(context=context, request=self.request())

    # TODO: ick
    @dispatch
    def render_to_response(self, **kwargs):
        return HttpResponse(self.render_root(**kwargs))

    def bind(self, *, parent=None, request=None):
        assert parent is None or parent._is_bound
        assert not self._is_bound

        if parent is None:
            self._request = request
            if self.name is None:
                self.name = 'root'
            if self.default_child is None:
                self.default_child = True

        if hasattr(self, '_no_copy_on_bind'):
            result = self
        else:
            result = copy.copy(self)
            result._declared = self

        result.parent = parent
        result._is_bound = True

        result.on_bind()

        if len(result.children()) == 1:
            for the_only_part in result.children().values():
                if the_only_part.default_child is None:
                    the_only_part.default_child = True

        return result

    def on_bind(self) -> None:
        pass

    def children(self):
        assert self._is_bound

        return Struct()

    def request(self):
        if self.parent is None:
            return self._request
        else:
            return self.parent.request()

    def path(self) -> str:
        # TODO: this assert seems like a good idea, but it fires in Table.prepare... not sure what to do about that right now
        # assert self._is_bound
        if self.default_child:
            if self.parent is not None:
                return self.parent.path()
            else:
                return ''

        if self.parent is not None:
            return path_join(self.parent.path(), self.name)
        else:
            assert self.name, f'{self} is missing a name, but it was asked about its path'
            return self.name

    def endpoint_path(self):
        return DISPATCH_PREFIX + self.path()


def render_template_name(template_name, **kwargs):
    return render_template(template=template_name, **kwargs)


PartType = Union[PagePart, str, Template]


def is_responding(request):
    if request.method == 'GET':
        return any(x.startswith(DISPATCH_PATH_SEPARATOR) for x in request.GET.keys())

    return False


def render_part(*, part: PartType, context):
    if isinstance(part, str):
        return part
    elif isinstance(part, Template):
        return part.render(context=context)
    else:
        return part.render(context=context)


def path_join(prefix, name) -> str:
    if not prefix:
        return name
    else:
        return prefix + DISPATCH_PATH_SEPARATOR + name


DISPATCH_PATH_SEPARATOR = '/'
DISPATCH_PREFIX = DISPATCH_PATH_SEPARATOR
MISSING = object()


def model_and_rows(model, rows):
    if rows is None and model is not None:
        rows = model.objects.all()

    if model is None and isinstance(rows, QuerySet):
        model = rows.model

    return model, rows


def request_data(request):
    # TODO: this seems wrong. should at least be a QueryDictThingie
    if request is None:
        return {}

    if request.method == 'POST':
        return request.POST
    elif request.method == 'GET':
        return request.GET
    else:
        assert False, f'unsupported request method {request.method}'
    # TODO: support more verbs here. OPTIONS seems reasonable for example


def no_copy_on_bind(cls):
    cls._no_copy_on_bind = True
    return cls


def collect_members(*, items, cls):
    def unbound_items():
        for name, item in items.items():
            if isinstance(item, dict):
                item = setdefaults_path(
                    Namespace(),
                    item,
                    call_target=cls,
                )
                item = item()
            setattr(item, 'name', name)
            yield item

    return list(unbound_items())


def bind_members(*, unbound_items, parent, **kwargs):
    bound_items = sort_after([x.bind(parent=parent) for x in unbound_items])

    for item in bound_items:
        item._evaluate_show(**kwargs)

    items = Struct({item.name: item for item in bound_items if should_show(item)})

    for item in items.values():
        item._evaluate(**kwargs)

    return items
