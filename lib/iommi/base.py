from collections import defaultdict
from functools import wraps
from typing import (
    Union,
    Any,
)

from django.conf import settings
from django.http.response import HttpResponseBase, HttpResponse
from django.template import Template
from tri_declarative import dispatch, EMPTY
from iommi._web_compat import get_template_from_string, render_template


class GroupPathsByChildrenError(Exception):
    pass


def group_paths_by_children(*, children, data):
    results = defaultdict(dict)

    default_child = [k for k, v in children.items() if getattr(v, 'default_child', False)]
    assert len(default_child) in (0, 1), 'There can only be one default_child per level'
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


def endpoint_path(obj):

    def _endpoint_path(obj):
        # TODO: handle default_child
        if obj.parent is None:
            return ''
        return path_join(_endpoint_path(obj.parent), obj.name)

    return '/' + _endpoint_path(obj)


class InvalidEndpointPathException(Exception):
    pass


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


def catch_response(view_function):
    @wraps(view_function)
    def catch_response_view(*args, **kwargs):
        try:
            return view_function(*args, **kwargs)
        except ResponseException as e:
            return e.response

    return catch_response_view


class PagePart:
    request = None
    parent = None
    name = None
    default_child = False
    _is_bound = False

    @dispatch(
        context=EMPTY,
    )
    def render_or_respond(self, *, request, context=None, render=None):
        pass

    @dispatch(
        template_name=getattr(settings, 'TRI_BASE_TEMPLATE', 'base.html'),
        content_block_name=getattr(settings, 'TRI_CONTENT_BLOCK', 'content'),
    )
    @catch_response
    def render_to_response(self, *, request, template_name, content_block_name, context=None):
        if context is None:
            context = {}

        content = raise_on_response(
            self.render_or_respond(request=request, context=context)
        )

        assert 'content' not in context
        context['content'] = content

        template_string = '{% extends "' + template_name + '" %} {% block ' + content_block_name + ' %} {{ content }} {% endblock %}'
        return HttpResponse(get_template_from_string(template_string).render(context=context, request=request))

    def bind(self, *, parent):
        if parent is None:
            if self.name is None:
                self.name = 'root'
            self.default_child = True

        if parent is not None:
            self.request = parent.request
        self.parent = parent
        result = self.on_bind()
        if result is None:
            return self
        self._is_bound = True
        return result

    def on_bind(self) -> Any:
        pass

    def path(self) -> str:
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


def render_template_name(template_name, **kwargs):
    return render_template(template=template_name, **kwargs)


PartType = Union[PagePart, str, Template]


def is_responding(request):
    if request.method == 'GET':
        return any(x.startswith(DISPATCH_PATH_SEPARATOR) for x in request.GET.keys())

    return False


def render_or_respond_part(*, part: PartType, request, context):
    if isinstance(part, str):
        return part
    elif isinstance(part, Template):
        return part.render(context)
    else:
        if callable(part):
            if is_responding(request):
                return None

            # compatibility with simple views, like admin_menu
            return part(request=request)
        return raise_on_response(part.render_or_respond(request=request, context=context))


def path_join(prefix, name) -> str:
    if not prefix:
        return name
    else:
        return prefix + DISPATCH_PATH_SEPARATOR + name


NO_ENDPOINT_PREFIX = ''
DISPATCH_PATH_SEPARATOR = '/'
MISSING = object()
