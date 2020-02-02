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
    QueryDict,
)
from iommi.render import Attrs
from iommi.style import (
    apply_style_recursively,
    get_style_obj_for_object,
)
from tri_declarative import (
    dispatch,
    EMPTY,
    evaluate,
    evaluate_strict,
    get_callable_description,
    Namespace,
    Refinable,
    RefinableObject,
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


class InvalidEndpointPathException(Exception):
    pass


class Endpoint:
    declared_members = {}

    def __init__(self, name, func):
        self.name = name
        self.func = func


def setup_endpoints(parent, endpoints):
    members = Struct()
    for k, v in endpoints.items():
        members[k] = Endpoint(k, v)
    parent.declared_members.endpoints = members
    parent.declared_endpoints = members


class EndPointHandlerProxy:
    def __init__(self, name, func, parent):
        self.name = name
        self.func = func
        self.parent = parent
        assert callable(func)

    def endpoint_handler(self, value, **kwargs):
        return self.func(value=value, **kwargs)

    def evaluate_attribute_kwargs(self):
        return self.parent.evaluate_attribute_kwargs()

    def children(self):
        return {}


def setup_endpoint_proxies(parent: 'Part') -> Dict[str, EndPointHandlerProxy]:
    result = Struct({
        k: EndPointHandlerProxy(k, v.func, parent=parent)
        for k, v in parent.declared_endpoints.items()
    })

    result.children = lambda: result

    return result


def find_target(*, path, root):
    assert path.startswith(DISPATCH_PATH_SEPARATOR)
    p = path[1:]

    long_path = root._long_path_by_path.get(p)
    if long_path is None:
        long_path = p
        if not long_path in root._path_by_long_path.keys():
            short_paths = ', '.join(map(repr, root._long_path_by_path.keys()))
            long_paths = ', '.join(map(repr, root._path_by_long_path.keys()))
            assert False, (
                f"Given path {path} not found.\n"
                f"  Short alternatives: {short_paths}\n"
                f"  Long alternatives: {long_paths}"
            )

    node = root
    parents = []
    for part in long_path.split('/'):
        parents.append(node)
        children = node.children()
        node = children.get(part)
        assert node is not None, f'Failed to traverse long path {long_path}'
    parents.append(node)

    return node, parents


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
        parents_str = '        \n'.join([repr(p) for p in parents])
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


def apply_style(obj):
    style = get_style_obj_for_object(style=get_style_for(obj), obj=obj)
    apply_style_recursively(style_data=style, obj=obj)


def get_style_for(obj):
    if obj.style is not None:
        return obj.style
    if obj.parent is not None:
        return get_style_for(obj.parent)

    return getattr(settings, 'IOMMI_DEFAULT_STYLE', 'bootstrap')


class Part(RefinableObject):
    name: str = Refinable()
    include: bool = Refinable()
    after: Union[int, str] = Refinable()
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
        self.declared_members = Struct()
        super(Part, self).__init__(**kwargs)

    @dispatch(
        context=EMPTY,
        render=EMPTY,
    )
    def __html__(self, *, context=None, render=None):
        assert False, 'Not implemented'  # pragma: no cover

    def __str__(self):
        assert self._is_bound
        return self.__html__()

    def __repr__(self):
        n = f' {self.name}' if self.name is not None else ''
        b = ' (bound)' if self._is_bound else ''
        p = f" path:'{self.path()}'" if self.parent is not None else ""
        c = ''
        if self._is_bound:
            children = self.children()
            if children:
                c = f" children:{list(children.keys())!r}"

        return f'<{self.__class__.__module__}.{self.__class__.__name__}{n}{b}{p}{c}>'

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

        else:  # pragma: no cover
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

        long_path_by_path = None
        if parent is None:
            long_path_by_path = build_long_path_by_path(self)

        if hasattr(self, '_no_copy_on_bind'):
            result = self
        else:
            result = copy.copy(self)
            result._declared = self
        del self  # to prevent mistakes when changing the code below

        result.parent = parent
        if parent is None:
            result._long_path_by_path = long_path_by_path
            result._path_by_long_path = {v: k for k, v in result._long_path_by_path.items()}
            result._node_by_path = {}
            result._node_by_long_path = {}

        result._is_bound = True

        apply_style(result)
        result.on_bind()

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

    def dunder_path(self) -> str:
        assert self._is_bound
        if self.parent is not None:
            return path_join(self.parent.dunder_path(), self.name, separator='__')
        else:
            assert self.name, f'{self} is missing a name, but it was asked about its path'
            return ''

    def path(self) -> str:
        path_by_long_path = get_root(self)._path_by_long_path
        long_path = build_long_path(self)
        path = path_by_long_path.get(long_path)
        if path is None:
            candidates = '\n'.join(path_by_long_path.keys())
            assert False, f"Path not found(!) (Searched for {long_path} among the following:\n{candidates}"
        return path

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


def get_root(node):
    while node.parent is not None:
        node = node.parent
    return node


def build_long_path(node):
    def _traverse(node):
        assert node._is_bound
        if node.parent is None:
            return []
        return _traverse(node.parent) + [node.name]

    return '/'.join(_traverse(node))


def include_in_short_path(node):
    return getattr(node, 'name', None) is not None


def build_long_path_by_path(root) -> Dict[str, str]:
    result = dict()

    def _traverse(node, long_path_segments, short_path_candidate_segments):
        print(repr(node))
        if include_in_short_path(node):
            for i in range(len(short_path_candidate_segments), -1, -1):
                candidate = '/'.join(short_path_candidate_segments[i:])
                if candidate not in result:
                    result[candidate] = '/'.join(long_path_segments)
                    break
            else:
                assert False, f"Ran out of names... Any suitable short name for {'/'.join(long_path_segments)} already taken."

        children = getattr(node, 'declared_members', node)
        for name, child in children.items():
            if child:
                _traverse(
                    child,
                    long_path_segments=long_path_segments + [name],
                    short_path_candidate_segments=short_path_candidate_segments + (
                        [name]
                        if include_in_short_path(child)
                        else []
                    )
                )

    _traverse(root, [], [])

    return result


PartType = Union[Part, str, Template]


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
    if request is None:
        return QueryDict()

    if request.method == 'POST':
        return request.POST
    elif request.method == 'GET':
        return request.GET
    else:
        assert False, f'unsupported request method {request.method}'


def no_copy_on_bind(cls):
    cls._no_copy_on_bind = True
    return cls


def collect_members(obj, *, name: str, items_dict: Dict = None, items: Dict[str, Any] = None, cls: Type, unapplied_config: Dict) -> Dict[str, Any]:
    unbound_items = {}

    if items_dict is not None:
        for key, x in items_dict.items():
            x.name = key
            unbound_items[key] = x

    if items is not None:
        for key, item in items.items():
            if not isinstance(item, dict):
                item.name = key
                unbound_items[key] = item
            else:
                if key in unbound_items:
                    unapplied_config[key] = item
                else:
                    item = setdefaults_path(
                        Namespace(),
                        item,
                        call_target__cls=cls,
                        name=key,
                    )
                    unbound_items[key] = item()

    members = Struct({x.name: x for x in sort_after(list(unbound_items.values()))})
    obj.declared_members[name] = members
    setattr(obj, 'declared_' + name, members)


@no_copy_on_bind
class Members(Part):
    def __init__(self, *, declared_items, **kwargs):
        super(Members, self).__init__(**kwargs)
        self.members: Dict[str, Any] = {}
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
        except KeyError:  # pragma: no cover
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

    def __iter__(self):  # pragma: no cover
        raise NotImplementedError('Iterate with .keys(), .values() or .items()')


def bind_members(obj: Part, *, name: str) -> None:
    declared_items = getattr(obj, f'declared_{name}')
    m = Members(name=name, declared_items=declared_items)
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
    return Attrs({
        'class': classes,
        **attrs
    }, parent=obj)
