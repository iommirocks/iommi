import copy
import json
from collections import defaultdict
from typing import (
    Any,
    Dict,
    Type,
    Union,
)

from django.conf import settings
from django.db.models import QuerySet
from django.http.response import (
    HttpResponse,
)
from django.template import Template
from iommi._web_compat import (
    get_template_from_string,
    render_template,
)
from iommi.render import Attrs
from iommi.style import (
    apply_style_recursively,
    get_style_for_object,
)
from tri_declarative import (
    EMPTY,
    Namespace,
    Refinable,
    RefinableObject,
    dispatch,
    evaluate,
    evaluate_strict,
    get_callable_description,
    setdefaults_path,
    sort_after,
)
from tri_struct import Struct

MISSING = object()


def should_include(item):
    if callable(item.include):
        assert False, "`include` was a callable. You probably forgot to evaluate it. The callable was: {}".format(get_callable_description(item.include))

    return item.include


def evaluate_strict_container(c, **kwargs):
    return Namespace(
        {
            k: evaluate_strict(v, **kwargs)
            for k, v in c.items()
        }
    )


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
    def __init__(self, func, parent):
        self.func = func
        self.parent = parent
        assert callable(func)

    def endpoint_handler(self, value, **kwargs):
        return self.func(value=value, **kwargs)

    def evaluate_attribute_kwargs(self):
        return self.parent.evaluate_attribute_kwargs()


def setup_endpoint_proxies(parent: 'PagePart') -> Dict[str, EndPointHandlerProxy]:
    return Namespace({
        k: EndPointHandlerProxy(v, parent=parent)
        for k, v in parent.endpoint.items()
    })


def find_target(*, path, root):
    assert path.startswith(DISPATCH_PATH_SEPARATOR)
    p = path[1:]
    sentinel = object()
    next_node = root
    parents = [root]

    # TODO: what if the path is just / ? We can't get to that object as is. If we allow this then it can't work with default_child

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


def perform_ajax_dispatch(*, root, path, value):
    assert root._is_bound

    target, parents = find_target(path=path, root=root)
    if target.endpoint_handler is None:
        raise InvalidEndpointPathException(f'Target {target} has no registered endpoint_handler')

    return target.endpoint_handler(value=value, **target.evaluate_attribute_kwargs())


def perform_post_dispatch(*, root, path, value):
    assert root._is_bound
    assert path[0] in ('/', '-')
    path = '/' + path[1:]  # replace initial - with / to convert from post-y paths to ajax-y paths
    target, parents = find_target(path=path, root=root)

    if target.post_handler is None:
        parents_str = '        \n'.join([str(p) for p in parents])
        raise InvalidEndpointPathException(f'Target {target} has no registered post_handler.\n    Path: "{path}"\n    Parents:\n        {parents_str}')

    return target.post_handler(value=value, **target.evaluate_attribute_kwargs())


@dispatch(
    render=EMPTY,
)
def render_root(*, part, template_name=MISSING, content_block_name=MISSING, context=None, **render):
    if context is None:
        context = {}

    if template_name is MISSING:
        template_name = getattr(settings, 'IOMMI_BASE_TEMPLATE', 'base.html')
    if content_block_name is MISSING:
        content_block_name = getattr(settings, 'IOMMI_CONTENT_BLOCK', 'content')


    content = part.__html__(context=context, **render)

    assert 'content' not in context
    context['content'] = content

    template_string = '{% extends "' + template_name + '" %} {% block ' + content_block_name + ' %} {{ content }} {% endblock %}'
    return get_template_from_string(template_string).render(context=context, request=part.request())


# TODO: abc?
class PagePart(RefinableObject):
    name: str = Refinable()
    include: bool = Refinable()
    after: Union[int, str] = Refinable()
    default_child = Refinable()
    extra: Namespace = Refinable()
    extra_evaluated: Namespace = Refinable()
    style: str = Refinable()

    parent = None
    _is_bound = False

    @dispatch(
        extra=EMPTY,
        extra_evaluated=EMPTY,
        include=True,
        name=None,
    )
    def __init__(self, **kwargs):
        super(PagePart, self).__init__(**kwargs)

    @dispatch(
        context=EMPTY,
        render=EMPTY,
    )
    def __html__(self, *, context=None, render=None):
        assert False, 'Not implemented'

    def __str__(self):
        assert self._is_bound
        return self.__html__()

    # TODO: ick! why is this on ALL PageParts?
    @dispatch
    def render_to_response(self, **kwargs):
        request = self.request()
        req_data = request_data(request)

        if request.method == 'GET':
            dispatch_prefix = DISPATCH_PATH_SEPARATOR
            dispatcher = perform_ajax_dispatch
            dispatch_error = 'Invalid endpoint path'

            def dispatch_response_handler(r):
                return HttpResponse(json.dumps(r), content_type='application/json')

        elif request.method == 'POST':
            dispatch_prefix = '-'
            dispatcher = perform_post_dispatch
            dispatch_error = 'Invalid post path'

            def dispatch_response_handler(r):
                return r

        else:
            assert False  # This has already been checked in request_data()

        dispatch_commands = {key: value for key, value in req_data.items() if key.startswith(dispatch_prefix)}
        assert len(dispatch_commands) in (0, 1), 'You can only have one or no dispatch commands'
        if dispatch_commands:
            dispatch_target, value = next(iter(dispatch_commands.items()))
            try:
                result = dispatcher(root=self, path=dispatch_target, value=value)
            except InvalidEndpointPathException:
                if settings.DEBUG:
                    raise
                result = dict(error=dispatch_error)

            if result is not None:
                return dispatch_response_handler(result)

        return HttpResponse(render_root(part=self, **kwargs))

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
        del self  # to prevent mistakes when changing the code below

        result.parent = parent
        result._is_bound = True

        result.apply_style()
        result.on_bind()

        if len(result.children()) == 1:
            for the_only_part in result.children().values():
                if the_only_part.default_child is None:
                    the_only_part.default_child = True

        return result

    def on_bind(self) -> None:
        pass

    def apply_style(self):
        style = get_style_for_object(style=self.get_style(), self=self)
        apply_style_recursively(style_data=style, obj=self)

    def children(self):
        assert self._is_bound

        return Struct()

    def request(self):
        if self.parent is None:
            return self._request
        else:
            return self.parent.request()

    def get_style(self):
        if self.style is not None:
            return self.style
        if self.parent is not None:
            return self.parent.get_style()

        return getattr(settings, 'IOMMI_DEFAULT_STYLE', 'bootstrap')

    def dunder_path(self) -> str:
        assert self._is_bound
        if self.parent is not None:
            return path_join(self.parent.dunder_path(), self.name, separator='__')
        else:
            assert self.name, f'{self} is missing a name, but it was asked about its path'
            return ''

    def path(self) -> str:
        assert self._is_bound
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

    def evaluate_attribute_kwargs(self):
        return {**self._evaluate_attribute_kwargs(), **(self.parent.evaluate_attribute_kwargs() if self.parent is not None else {})}

    def _evaluate_attribute_kwargs(self):
        return {}

    def _evaluate_attribute(self, key, strict=True):
        evaluate_member(self, key, **self.evaluate_attribute_kwargs(), strict=strict)

    def _evaluate_include(self):
        self._evaluate_attribute('include')


def render_template_name(template_name, **kwargs):
    return render_template(template=template_name, **kwargs)


PartType = Union[PagePart, str, Template]


def as_html(*, part: PartType, context):
    if isinstance(part, str):
        return part
    elif isinstance(part, Template):
        template = part
        return template.render(context=context)
    else:
        # TODO: this isn't compatible with jinja2
        return part.__html__(context=context)


DISPATCH_PATH_SEPARATOR = '/'
DISPATCH_PREFIX = DISPATCH_PATH_SEPARATOR


def path_join(prefix, name, separator=DISPATCH_PATH_SEPARATOR) -> str:
    if not prefix:
        return name
    else:
        return prefix + separator + name


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


def collect_members(*, items_dict: Dict = None, items: Dict[str, Any] = None, cls: Type, unapplied_config: Dict) -> Dict[str, Any]:
    unbound_items = {}

    if items_dict is not None:
        for name, x in items_dict.items():
            x.name = name
            unbound_items[name] = x

    if items is not None:
        for name, item in items.items():
            if not isinstance(item, dict):
                item.name = name
                unbound_items[name] = item
            else:
                if name in unbound_items:
                    unapplied_config[name] = item
                else:
                    item = setdefaults_path(
                        Namespace(),
                        item,
                        call_target__cls=cls,
                        name=name,
                    )
                    unbound_items[name] = item()

    return Struct({x.name: x for x in sort_after(list(unbound_items.values()))})


@no_copy_on_bind
class Members(PagePart):
    def __init__(self, *, declared_items, **kwargs):
        super(Members, self).__init__(**kwargs)
        self.members: Dict[str, Any] = None
        self.declared_items = declared_items

    def children(self):
        return self.members

    def on_bind(self) -> None:
        bound_items = [item for item in sort_after([x.bind(parent=self) for x in self.declared_items.values()])]

        for item in bound_items:
            item._evaluate_include()

        self.members = {item.name: item for item in bound_items if should_include(item)}

    def get(self, key, default=None):
        return self.members.get(key, default)

    def __getattr__(self, item):
        if self.members is None:
            raise AttributeError()
        try:
            return self.members[item]
        except KeyError:
            raise AttributeError()

    def values(self):
        return self.members.values()

    def keys(self):
        return self.members.keys()

    def items(self):
        return self.members.items()

    def __contains__(self, item):
        return item in self.members

    def __setitem__(self, key, value):
        self.members[key] = value

    def __getitem__(self, item):
        return self.members[item]

    def __len__(self):
        return len(self.members)

    def __iter__(self):
        raise NotImplementedError('Iterate with .keys(), .values() or .items()')


def bind_members(obj: PagePart, *, name: str, default_child=False) -> None:
    declared_items = getattr(obj, f'declared_{name}')
    m = Members(name=name, declared_items=declared_items, default_child=default_child)
    m.bind(parent=obj)
    setattr(obj, name, m)


def evaluate_members(obj, keys, **kwargs):
    for key in keys:
        evaluate_member(obj, key, **kwargs)


def evaluate_member(obj, key, strict=True, **kwargs):
    value = getattr(obj, key)
    new_value = evaluate(value, __strict=strict, **kwargs)
    if new_value is not value:
        setattr(obj, key, new_value)


def evaluate_attrs(obj, **kwargs):
    attrs = obj.attrs
    classes = {
        k: evaluate_strict(v, **kwargs)
        for k, v in attrs.get('class', {}).items()
    }
    attrs = {
        k: evaluate_strict(v, **kwargs)
        for k, v in attrs.items()
        if k != 'class'
    }
    if getattr(settings, 'IOMMI_DEBUG_SHOW_PATHS', False) and getattr(obj, 'name', None) is not None:
        attrs['data-iommi-path'] = obj.dunder_path()
    return Attrs({
        'class': classes,
        **attrs
    })
