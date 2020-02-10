import copy
import json
from abc import abstractmethod
from pprint import pprint
from typing import (
    Any,
    Dict,
    List,
    Type,
    Union,
)

from django.conf import settings
from django.db.models import QuerySet
from django.http.response import (
    HttpResponse,
    HttpResponseBase,
)
from django.template import (
    Template,
)
from iommi._web_compat import (
    QueryDict,
    get_template_from_string,
)
from iommi.render import Attrs
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

DEFAULT_STYLE = 'bootstrap'
DEFAULT_BASE_TEMPLATE = 'base.html'
DEFAULT_CONTENT_BLOCK = 'content'

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


def find_target(*, path, root):
    assert path.startswith(DISPATCH_PATH_SEPARATOR)
    p = path[1:]

    long_path = root._long_path_by_path.get(p)
    if long_path is None:
        long_path = p
        if long_path not in root._path_by_long_path.keys():
            def format_paths(paths):
                return '\n        '.join(["''" if not x else x for x in paths.keys()])
            short_paths = format_paths(root._long_path_by_path)
            long_paths = format_paths(root._path_by_long_path)
            raise InvalidEndpointPathException(
                f"Given path {path} not found.\n"
                f"    Short alternatives:\n        {short_paths}\n"
                f"    Long alternatives:\n        {long_paths}"
            )

    node = root
    for part in long_path.split('/'):
        if part == '':
            continue
        node = node.bound_members.get(part)
        assert node is not None, f'Failed to traverse long path {long_path}'

    return node


def perform_ajax_dispatch(*, root, path, value):
    assert root._is_bound

    target = find_target(path=path, root=root)

    if getattr(target, 'endpoint_handler', None) is None:
        raise InvalidEndpointPathException(f'Target {target!r} has no registered endpoint_handler')

    return target.endpoint_handler(value=value, **target.evaluate_parameters())


def perform_post_dispatch(*, root, path, value):
    assert root._is_bound
    assert path[0] in ('/', '-')
    path = '/' + path[1:]  # replace initial - with / to convert from post-y paths to ajax-y paths
    target = find_target(path=path, root=root)

    if getattr(target, 'post_handler', None) is None:
        raise InvalidEndpointPathException(f'Target {target!r} has no registered post_handler')

    return target.post_handler(value=value, **target.evaluate_parameters())


@dispatch(
    render=EMPTY,
)
def render_root(*, part, template_name=MISSING, content_block_name=MISSING, context=None, **render):
    if context is None:
        context = {}

    if template_name is MISSING:
        template_name = getattr(settings, 'IOMMI_BASE_TEMPLATE', DEFAULT_BASE_TEMPLATE)
        print('template name', template_name)
    if content_block_name is MISSING:
        content_block_name = getattr(settings, 'IOMMI_CONTENT_BLOCK', DEFAULT_CONTENT_BLOCK)

    content = part.__html__(context=context, **render)

    assert 'content' not in context
    context['content'] = content

    template_string = '{% extends "' + template_name + '" %} {% block ' + content_block_name + ' %} {{ content }} {% endblock %}'
    return get_template_from_string(template_string).render(context=context, request=part.request())


def apply_style(obj):
    # Avoid circular import
    from iommi.style import (
        apply_style_recursively,
        get_style_obj_for_object,
    )
    style = get_style_obj_for_object(style=get_style_for(obj), obj=obj)
    apply_style_recursively(style_data=style, obj=obj)


def get_style_for(obj):
    if obj.style is not None:
        return obj.style
    if obj.parent is not None:
        return get_style_for(obj.parent)

    return getattr(settings, 'IOMMI_DEFAULT_STYLE', DEFAULT_STYLE)


class Traversable(RefinableObject):
    parent = None
    _is_bound = False
    # TODO: would be nice to not have this here
    style: str = Refinable()

    def __init__(self, **kwargs):
        self.declared_members = Struct()
        super(Traversable, self).__init__(**kwargs)

    def __repr__(self):
        n = f' {self.name}' if self.name is not None else ''
        b = ' (bound)' if self._is_bound else ''
        try:
            p = f" path:'{self.path()}'" if self.parent is not None else ""
        except AssertionError:
            p = ' path:<no path>'
        c = ''
        if self._is_bound:
            members = self.bound_members
            if members:
                c = f" members:{list(members.keys())!r}"

        return f'<{self.__class__.__module__}.{self.__class__.__name__}{n}{b}{p}{c}>'

    def path(self) -> str:
        path_by_long_path = get_root(self)._path_by_long_path
        long_path = build_long_path(self)
        path = path_by_long_path.get(long_path)
        if path is None:
            candidates = '\n'.join(path_by_long_path.keys())
            assert False, f"Path not found(!) (Searched for {long_path} among the following:\n{candidates}"
        return path

    def dunder_path(self) -> str:
        assert self._is_bound
        return build_long_path(self).replace('/', '__')

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

        result._is_bound = True
        result.bound_members = Struct()

        apply_style(result)
        result.on_bind()
        if hasattr(result, 'attrs'):
            result.attrs = evaluate_attrs(result, **result.evaluate_parameters())

        if hasattr(result, 'extra_evaluated'):
            result.extra_evaluated = evaluate_strict_container(result.extra_evaluated, **result.evaluate_parameters())

        return result

    def on_bind(self) -> None:
        pass

    # TODO: this should be a variable, created at bind time, just before on_bind()
    def evaluate_parameters(self):
        return {
            **(self.parent.evaluate_parameters() if self.parent is not None else {}),
            **self.own_evaluate_parameters(),
        }

    def own_evaluate_parameters(self):
        return {}

    def _evaluate_attribute(self, key, strict=True):
        evaluate_member(self, key, **self.evaluate_parameters(), strict=strict)

    def _evaluate_include(self):
        self._evaluate_attribute('include')


def get_root(node: Traversable) -> Traversable:
    while node.parent is not None:
        node = node.parent
    return node


def build_long_path(node: Traversable) -> str:
    def _traverse(node: Traversable) -> List[str]:
        # noinspection PyProtectedMember
        assert node._is_bound
        assert node.name is not None
        if node.parent is None:
            return []
        return _traverse(node.parent) + [node.name]

    return '/'.join(_traverse(node))


def include_in_short_path(node):
    return getattr(node, 'name', None) is not None


def build_long_path_by_path(root) -> Dict[str, str]:
    result = dict()

    def _traverse(node, long_path_segments, short_path_candidate_segments):
        if include_in_short_path(node):
            def find_unique_suffix(parts):
                for i in range(len(parts), -1, -1):
                    candidate = '/'.join(parts[i:])
                    if candidate not in result:
                        return candidate

            long_path = '/'.join(long_path_segments)
            short_path = find_unique_suffix(short_path_candidate_segments)
            if short_path is not None:
                result[short_path] = long_path
            else:
                less_short_path = find_unique_suffix(long_path_segments)
                if less_short_path is not None:
                    result[less_short_path] = long_path
                else:
                    so_far = '\n'.join(f'{k}   ->   {v}' for k, v in result.items())
                    assert False, f"Ran out of names... Any suitable short name for {'/'.join(long_path_segments)} already taken.\n\nResult so far:\n{so_far}"

        if hasattr(node, 'declared_members'):
            members = node.declared_members
        elif isinstance(node, dict):
            members = node
        else:
            return

        for name, member in members.items():
            if member:
                _traverse(
                    member,
                    long_path_segments=long_path_segments + [name],
                    short_path_candidate_segments=short_path_candidate_segments + (
                        [name]
                        if include_in_short_path(member)
                        else []
                    )
                )

    _traverse(root, [], [])

    # TODO: remove
    pprint(result)

    return result


class Part(Traversable):
    name: str = Refinable()
    include: bool = Refinable()
    after: Union[int, str] = Refinable()
    extra: Namespace = Refinable()
    extra_evaluated: Namespace = Refinable()
    style: str = Refinable()

    @dispatch(
        extra=EMPTY,
        extra_evaluated=EMPTY,
        include=True,
        name=None,
    )
    def __init__(self, **kwargs):
        super(Part, self).__init__(**kwargs)

    @dispatch(
        context=EMPTY,
        render=EMPTY,
    )
    @abstractmethod
    def __html__(self, *, context=None, render=None):
        assert False, 'Not implemented'  # pragma: no cover

    def __str__(self):
        assert self._is_bound
        return self.__html__()

    @dispatch
    def render_to_response(self, **kwargs):
        request = self.request()
        req_data = request_data(request)

        if request.method == 'GET':
            dispatch_prefix = DISPATCH_PATH_SEPARATOR
            dispatcher = perform_ajax_dispatch
            dispatch_error = 'Invalid endpoint path'

            def dispatch_response_handler(r):
                if isinstance(r, dict):
                    return HttpResponse(json.dumps(r), content_type='application/json')
                else:
                    assert isinstance(r, HttpResponseBase)
                    return r

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

    def request(self):
        if self.parent is None:
            return self._request
        else:
            return self.parent.request()


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
    assert name != 'items'
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

    # TODO: shouldn't sort_after be done on the bound items?
    members = Struct({x.name: x for x in unbound_items.values()})
    obj.declared_members[name] = members


@no_copy_on_bind
class Members(Part):
    def __init__(self, *, declared_members, **kwargs):
        super(Members, self).__init__(**kwargs)
        self.declared_members = declared_members

    def on_bind(self) -> None:
        bound_items = sort_after([
            m.bind(parent=self)
            for m in self.declared_members.values()
        ])

        for item in bound_items:
            item._evaluate_include()

        self.bound_members = Struct({item.name: item for item in bound_items if should_include(item)})


def bind_members(obj: Part, *, name: str) -> None:
    m = Members(name=name, declared_members=obj.declared_members[name])
    m.bind(parent=obj)
    setattr(obj, name, m.bound_members)
    setattr(obj.bound_members, name, m)


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


class InvalidEndpointPathException(Exception):
    pass


class Endpoint(Traversable):
    name = Refinable()
    func = Refinable()
    include = Refinable()

    @dispatch(
        name=None,
        func=None,
        include=True,
    )
    def __init__(self, **kwargs):
        super(Endpoint, self).__init__(**kwargs)

    def on_bind(self) -> None:
        assert callable(self.func)

    def endpoint_handler(self, value, **kwargs):
        return self.func(value=value, **kwargs)

    def endpoint_path(self):
        return DISPATCH_PREFIX + self.path()
