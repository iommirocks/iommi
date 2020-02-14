import copy
import json
from abc import abstractmethod
from collections import defaultdict
from os.path import (
    isabs,
    join,
)
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
from django.utils.safestring import mark_safe
from tri_declarative import (
    dispatch,
    EMPTY,
    evaluate,
    evaluate_strict,
    get_callable_description,
    LAST,
    Namespace,
    Refinable,
    refinable,
    RefinableObject,
    setdefaults_path,
)
from tri_struct import Struct

from iommi._web_compat import (
    format_html,
    get_template_from_string,
    HttpRequest,
    QueryDict,
)

DEFAULT_STYLE = 'bootstrap'
DEFAULT_BASE_TEMPLATE = 'base.html'
DEFAULT_CONTENT_BLOCK = 'content'

MISSING = object()


def iommi_debug_on():
    return getattr(settings, 'IOMMI_DEBUG', settings.DEBUG)


def should_include(item):
    if callable(item.include):
        assert False, "`include` was a callable. You probably forgot to evaluate it. The callable was: {}".format(get_callable_description(item.include))

    return item.include


def sort_after(l):
    unmoved = []
    to_be_moved_by_index = []
    to_be_moved_by_name = defaultdict(list)
    to_be_moved_last = []
    for x in l:
        after = getattr(x, 'after', None)
        if after is None:
            unmoved.append(x)
        elif after is LAST:
            to_be_moved_last.append(x)
        elif isinstance(after, int):
            to_be_moved_by_index.append(x)
        else:
            to_be_moved_by_name[x.after].append(x)

    to_be_moved_by_index = sorted(to_be_moved_by_index, key=lambda x: x.after)  # pragma: no mutate (infinite loop when x.after changed to None, but if changed to a number manually it exposed a missing test)

    def place(x):
        yield x
        for y in to_be_moved_by_name.pop(x._name, []):
            for z in place(y):
                yield z

    def traverse():
        count = 0
        while unmoved or to_be_moved_by_index:
            while to_be_moved_by_index:
                next_by_position_index = to_be_moved_by_index[0].after
                if count < next_by_position_index:  # pragma: no mutate (infinite loop when mutating < to <=)
                    break  # pragma: no mutate (infinite loop when mutated to continue)

                objects_with_index_due = place(to_be_moved_by_index.pop(0))
                for x in objects_with_index_due:
                    yield x
                    count += 1  # pragma: no mutate
            if unmoved:
                next_unmoved_and_its_children = place(unmoved.pop(0))
                for x in next_unmoved_and_its_children:
                    yield x
                    count += 1  # pragma: no mutate

        for x in to_be_moved_last:
            for y in place(x):
                yield y

    result = list(traverse())

    if to_be_moved_by_name:
        available_names = "\n   ".join(sorted([x._name for x in l]))
        raise KeyError(f'Tried to order after {", ".join(sorted(to_be_moved_by_name.keys()))} but {"that key does" if len(to_be_moved_by_name) == 1 else "those keys do"} not exist.\nAvailable names:\n    {available_names}')

    return result


def evaluate_strict_container(c, **kwargs):
    return Namespace(
        {
            k: evaluate_strict(v, **kwargs)
            for k, v in c.items()
        }
    )


class EvaluatedRefinable(Refinable):
    pass


def evaluated_refinable(f):
    f = refinable(f)
    f.__iommi__evaluated = True
    return f


def is_evaluated_refinable(x):
    return isinstance(x, EvaluatedRefinable) or getattr(x, '__iommi__evaluated', False)


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

    return target.endpoint_handler(value=value, **target.evaluate_parameters)


def perform_post_dispatch(*, root, path, value):
    assert root._is_bound
    assert path[0] in ('/', '-')
    path = '/' + path[1:]  # replace initial - with / to convert from post-y paths to ajax-y paths
    target = find_target(path=path, root=root)

    if getattr(target, 'post_handler', None) is None:
        raise InvalidEndpointPathException(f'Target {target!r} has no registered post_handler')

    return target.post_handler(value=value, **target.evaluate_parameters)


def endpoint__debug_tree(endpoint, **_):
    root = endpoint._parent._parent
    assert root._is_bound

    def rows(node, name='', path=None):
        if path is None:
            path = []
        is_struct = type(node) is Struct
        is_bound = getattr(node, '_is_bound', False)

        try:
            p = node.iommi_path if is_bound else None
        except PathNotFoundException:
            p = None

        type_name = type(node).__name__ if not is_struct else None
        base_type_name = type_name
        if isinstance(node, Members) and node.declared_members:
            if name == 'parts':
                member_type = 'Part'
            else:
                member_type = type(list(node.declared_members.values())[0]).__name__
            type_name = f'Members[{member_type}]'

        yield Struct(
            name=name,
            obj=node,
            type=type_name,
            base_type=base_type_name,
            path=p,
            # TODO: seems a bit strange we can't use dunder_path on collected members. We should be able to set parent earlier
            # dunder_path=node.iommi_dunder_path if not is_struct else None,
            dunder_path='__'.join(path),
            included=is_bound
        )

        if isinstance(node, dict):
            children = list(node.items())
        elif isinstance(node, Traversable):
            children = [
                (k, v if not node.bound_members or k not in node.bound_members else node.bound_members[k])
                for k, v in node.declared_members.items()
            ]
        else:
            assert False

        for k, v in children:
            yield from rows(v, name=k, path=path + [k])

    from iommi import (
        Column,
        Table,
    )

    def dunder_path__value(row, **_):
        if row.dunder_path is None:
            return ''
        prefix = row.dunder_path.rpartition('__')[0]
        return format_html(
            '<span class="full-path">{prefix}{separator}</span>{name}',
            prefix=prefix,
            separator='__' if prefix else '',
            name=row.name
        )

    class TreeTable(Table):
        class Meta:
            template = Template("""
                <style>
                    .full-path {
                        opacity: 0.0;
                    }
                    tr:hover .full-path {
                        opacity: 0.6;
                    }
                    
                    tr {
                        opacity: 0.4;
                    }
                    tr.included {
                        opacity: 1;
                    }
                    
                </style>
                
                {% include "iommi/table/table.html" %}            
            """)
            sortable = False
            row__attrs__class__included = lambda row, **_: row.included

        dunder_path = Column(
            cell__value=dunder_path__value,
        )
        path = Column()
        type = Column(
            cell__url=lambda row, **_: f'https://docs.iommi.rocks/en/latest/{row.base_type}.html' if row.base_type else None
        )
        included = Column.boolean()

    request = HttpRequest()
    request.method = 'GET'

    return TreeTable(rows=rows(root)).bind(request=request).render_to_response()


def local_debug_url_builder(filename, lineno):
    if not isabs(filename):
        filename = join(settings.BASE_DIR, filename)
    if hasattr(settings, 'DEBUG_URL_MAPPING'):
        filename = filename.replace(*settings.DEBUG_URL_MAPPING)
    return "pycharm://open?file=%s" % (filename,) + ('' if lineno is None else "&line=%d" % (lineno,))


def src_debug_url_builder(filename, lineno=None):
    debug_url_builder = getattr(settings, 'IOMMI_DEBUG_URL_BUILDER', local_debug_url_builder)
    return debug_url_builder(filename, lineno)


def iommi_debug_panel(part):
    if not iommi_debug_on():
        return ''

    frame = part._instantiated_at_frame
    source_url = None
    for _ in range(100):
        frame = frame.f_back
        module_name = frame.f_globals.get('__name__')
        if frame is None:
            break

        if module_name in ('tri_declarative', 'iommi', ) or module_name.startswith('iommi.'):
            continue
        source_url = src_debug_url_builder(frame.f_code.co_filename, frame.f_lineno)
        break

    if not source_url:
        return ''

    # TODO: use a Menu here?
    return format_html(
        """
            <div class="iommi_debug_buttons" style="float: right; padding-left: 20px">
                <a href="{}">Code</a>
                <a href="?/debug_tree">Tree</a>
            </div>
        """, source_url)


@dispatch(
    render=EMPTY,
)
def render_root(*, part, template_name=MISSING, content_block_name=MISSING, context=None, **render):
    if context is None:
        context = {}

    if template_name is MISSING:
        template_name = getattr(settings, 'IOMMI_BASE_TEMPLATE', DEFAULT_BASE_TEMPLATE)
    if content_block_name is MISSING:
        content_block_name = getattr(settings, 'IOMMI_CONTENT_BLOCK', DEFAULT_CONTENT_BLOCK)

    content = part.__html__(context=context, **render)

    assert 'content' not in context
    context['content'] = content
    if 'title' not in context:
        context['title'] = getattr(part, 'title', '') or ''

    context['iommi_debug_panel'] = iommi_debug_panel(part)

    template_string = '{% extends "' + template_name + '" %} {% block ' + content_block_name + ' %}{{ iommi_debug_panel }}{{ content }}{% endblock %}'
    return get_template_from_string(template_string).render(context=context, request=part.get_request())


def apply_style(obj):
    # Avoid circular import
    from iommi.style import (
        apply_style_recursively,
        get_style_obj_for_object,
    )
    style = get_style_obj_for_object(style=get_style_for(obj), obj=obj)
    apply_style_recursively(style_data=style, obj=obj)


def get_style_for(obj):
    if obj.iommi_style is not None:
        return obj.iommi_style
    if obj._parent is not None:
        return get_style_for(obj._parent)

    return getattr(settings, 'IOMMI_DEFAULT_STYLE', DEFAULT_STYLE)


class PathNotFoundException(Exception):
    pass


class Traversable(RefinableObject):
    """
    Abstract API for objects that have a place in the iommi path structure.
    You should not need to care about this class as it is an implementation
    detail.
    """

    _name = None
    _parent = None
    _is_bound = False
    _request = None

    iommi_style: str = EvaluatedRefinable()

    @dispatch
    def __init__(self, _name=None, **kwargs):
        # TODO: _ prefix on some of these?
        self.declared_members = Struct()
        self.unapplied_config = Struct()
        self.bound_members = None
        self.evaluate_parameters = None
        self._name = _name

        super(Traversable, self).__init__(**kwargs)

    def __repr__(self):
        n = f' {self._name}' if self._name is not None else ''
        b = ' (bound)' if self._is_bound else ''
        try:
            p = f" path:'{self.iommi_path}'" if self._parent is not None else ""
        except AssertionError:
            p = ' path:<no path>'
        c = ''
        if self._is_bound:
            members = self.bound_members
            if members:
                c = f" members:{list(members.keys())!r}"

        return f'<{type(self).__module__}.{type(self).__name__}{n}{b}{p}{c}>'

    @property
    def iommi_path(self) -> str:
        long_path = build_long_path(self)
        path_by_long_path = get_root(self)._path_by_long_path
        path = path_by_long_path.get(long_path)
        if path is None:
            candidates = '\n'.join(path_by_long_path.keys())
            raise PathNotFoundException(f"Path not found(!) (Searched for {long_path} among the following:\n{candidates}")
        return path

    @property
    def iommi_dunder_path(self) -> str:
        assert self._is_bound
        return build_long_path(self).replace('/', '__')

    def bind(self, *, parent=None, request=None):
        assert parent is None or parent._is_bound
        assert not self._is_bound

        if parent is None:
            self._request = request
            if self._name is None:
                self._name = 'root'

        long_path_by_path = None
        if parent is None:
            long_path_by_path = build_long_path_by_path(self)

        if hasattr(self, '_no_copy_on_bind'):
            result = self
        else:
            result = copy.copy(self)
            result._declared = self

        del self  # to prevent mistakes when changing the code below

        result._parent = parent
        if parent is None:
            result._long_path_by_path = long_path_by_path
            result._path_by_long_path = {v: k for k, v in result._long_path_by_path.items()}

        result._is_bound = True
        result.bound_members = Struct()

        apply_style(result)

        if parent is not None:
            unapplied_config = parent.unapplied_config.get(result._name, {})
            for k, v in unapplied_config.items():
                if k in result.declared_members:
                    result.unapplied_config[k] = v
                    continue
                # TODO what to check for? isinstnace Members seems weird
                if not isinstance(result, Members) and hasattr(result, k):
                    setattr(result, k, v)
                    continue
                print(f'Unable to set {k} on {result._name}')

        result.evaluate_parameters = {
            **(result._parent.evaluate_parameters if result._parent is not None else {}),
            **result.own_evaluate_parameters(),
        }
        result.on_bind()

        if hasattr(result, 'attrs'):
            result.attrs = evaluate_attrs(result, **result.evaluate_parameters)

        evaluated_attributes = [k for k, v in result.get_declared('refinable_members').items() if is_evaluated_refinable(v)]
        evaluate_members(result, evaluated_attributes, **result.evaluate_parameters)

        if hasattr(result, 'extra_evaluated'):
            result.extra_evaluated = evaluate_strict_container(result.extra_evaluated or {}, **result.evaluate_parameters)

        return result

    def on_bind(self) -> None:
        pass

    def own_evaluate_parameters(self):
        return {}

    def get_request(self):
        if self._parent is None:
            return self._request
        else:
            return self._parent.get_request()


def get_root(node: Traversable) -> Traversable:
    while node._parent is not None:
        node = node._parent
    return node


def build_long_path(node: Traversable) -> str:
    def _traverse(node: Traversable) -> List[str]:
        # noinspection PyProtectedMember
        assert node._is_bound
        assert node._name is not None
        if node._parent is None:
            return []
        return _traverse(node._parent) + [node._name]

    return '/'.join(_traverse(node))


def include_in_short_path(node):
    return getattr(node, '_name', None) is not None


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

    return result


class Part(Traversable):
    """
    `Part` is the base class for parts of a page that can be rendered as html, and can respond to ajax and post.
    """

    include: bool = EvaluatedRefinable()
    after: Union[int, str] = EvaluatedRefinable()
    extra: Namespace = Refinable()
    extra_evaluated: Namespace = Refinable()  # not EvaluatedRefinable because this is an evaluated container so is special
    endpoints: Namespace = Refinable()

    @dispatch(
        extra=EMPTY,
        include=True,
    )
    def __init__(self, endpoints: Dict[str, Any] = None, **kwargs):
        super(Part, self).__init__(**kwargs)
        collect_members(self, name='endpoints', items=endpoints, cls=Endpoint)

        if iommi_debug_on():
            import inspect
            self._instantiated_at_frame = inspect.currentframe().f_back

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

    def bind(self, *, parent=None, request=None):
        result = super(Part, self).bind(parent=parent, request=request)
        del self
        bind_members(result, name='endpoints')
        return result

    @dispatch
    def render_to_response(self, **kwargs):
        request = self.get_request()
        req_data = request_data(request)

        def dispatch_response_handler(r):
            if isinstance(r, HttpResponseBase):
                return r
            else:
                return HttpResponse(json.dumps(r), content_type='application/json')

        if request.method == 'GET':
            dispatch_prefix = DISPATCH_PATH_SEPARATOR
            dispatcher = perform_ajax_dispatch
            dispatch_error = 'Invalid endpoint path'

        elif request.method == 'POST':
            dispatch_prefix = '-'
            dispatcher = perform_post_dispatch
            dispatch_error = 'Invalid post path'

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


FORBIDDEN_NAMES = {x for x in dir(Traversable)}


class ForbiddenNamesException(Exception):
    pass


def collect_members(obj, *, name: str, items_dict: Dict = None, items: Dict[str, Any] = None, cls: Type) -> Dict[str, Any]:
    forbidden_names = FORBIDDEN_NAMES & (set((items_dict or {}).keys()) | set((items or {}).keys()))
    if forbidden_names:
        raise ForbiddenNamesException(f'The names {", ".join(sorted(forbidden_names))} are reserved by iommi, please pick other names')

    assert name != 'items'
    unbound_items = {}
    unapplied_config = {}

    if items_dict is not None:
        for key, x in items_dict.items():
            x._name = key
            unbound_items[key] = x

    if items is not None:
        for key, item in items.items():
            if not isinstance(item, dict):
                item._name = key
                unbound_items[key] = item
            else:
                if key in unbound_items:
                    unapplied_config[key] = item
                else:
                    item = setdefaults_path(
                        Namespace(),
                        item,
                        call_target__cls=cls,
                        _name=key,
                    )
                    unbound_items[key] = item()

    if unapplied_config:
        obj.unapplied_config[name] = unapplied_config

    members = Struct({x._name: x for x in unbound_items.values()})
    obj.declared_members[name] = members


@no_copy_on_bind
class Members(Traversable):
    """
    Internal iommi class that holds members of another class, for example the columns of a `Table` instance.
    """

    @dispatch
    def __init__(self, *, declared_members, **kwargs):
        super(Members, self).__init__(**kwargs)
        self.declared_members = declared_members

    def on_bind(self) -> None:
        bound_items = sort_after([
            m.bind(parent=self)
            for m in self.declared_members.values()
        ])

        self.bound_members = Struct({item._name: item for item in bound_items if should_include(item)})


def bind_members(obj: Part, *, name: str) -> None:
    m = Members(
        _name=name,
        declared_members=obj.declared_members[name],
    )
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
    attrs = obj.attrs or {}
    return Attrs(
        obj,
        **{
            'class': {
                k: evaluate_strict(v, **kwargs)
                for k, v in attrs.get('class', {}).items()
            }
        },
        style={
            k: evaluate_strict(v, **kwargs)
            for k, v in attrs.get('style', {}).items()
        },
        **{
            k: evaluate_strict(v, **kwargs)
            for k, v in attrs.items()
            if k not in ('class', 'style')
        },
    )


class InvalidEndpointPathException(Exception):
    pass


class Endpoint(Traversable):
    """
    Class that describes an endpoint in iommi. You can create your own custom
    endpoints on any :doc:`Part`.

    Example:

    .. code:: python

        def my_view(request):
            return Page(
                parts__h1=html.h1('Hi!'),
                endpoint__echo__func=lambda value, **_: value,
            )

    this page will respond to `?/echo=foo` by returning a json response `"foo"`.
    """

    name = Refinable()
    func = Refinable()
    include = EvaluatedRefinable()

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
        return DISPATCH_PREFIX + self.iommi_path

    def own_evaluate_parameters(self):
        return dict(endpoint=self)


def create_as_view_from_as_page(cls, name, *, kwargs, title, parts):
    def view_wrapper(request, **url_kwargs):
        return getattr(cls(**kwargs), f'{name}_page')(title=title, parts=parts, **url_kwargs).bind(request=request).render_to_response()

    view_wrapper.__name__ = f'{cls.__name__}{repr(Namespace(kwargs))[len("Namespace"):]}.{name}_view'
    view_wrapper.__doc__ = cls.__doc__

    return view_wrapper


def render_attrs(attrs):
    """
    Render HTML attributes, or return '' if no attributes needs to be rendered.
    """
    if attrs is not None:
        if not attrs:
            return ''

        def parts():
            for key, value in sorted(attrs.items()):
                if value is None:
                    continue
                if value is True:
                    yield f'{key}'
                    continue
                if isinstance(value, dict):
                    if key == 'class':
                        if not value:
                            continue
                        value = render_class(value)
                        if not value:
                            continue
                    elif key == 'style':
                        if not value:
                            continue
                        value = render_style(value)
                        if not value:
                            continue
                    else:
                        raise TypeError(f'Only the class and style attributes can be dicts, you sent {value}')
                elif isinstance(value, (list, tuple)):
                    raise TypeError(f"Attributes can't be of type {type(value).__name__}, you sent {value}")
                elif callable(value):
                    raise TypeError(f"Attributes can't be callable, you sent {value} for key {key}")
                v = f'{value}'.replace('"', '&quot;')
                yield f'{key}="{v}"'
        return mark_safe(' %s' % ' '.join(parts()))
    return ''


def render_class(class_dict):
    return ' '.join(sorted(name for name, flag in class_dict.items() if flag))


def render_style(class_dict):
    return '; '.join(sorted(f'{k}: {v}' for k, v in class_dict.items() if v))


class Attrs(Namespace):
    def __init__(self, parent, **attrs):
        from iommi.base import iommi_debug_on

        if iommi_debug_on() and getattr(parent, '_name', None) is not None:
            attrs['data-iommi-path'] = parent.iommi_dunder_path

        if 'style' in attrs and not attrs['style']:
            del attrs['style']

        if 'class' in attrs and not attrs['class']:
            del attrs['class']

        super(Attrs, self).__init__(attrs)

    def __str__(self):
        return self.__html__()

    # noinspection PyUnusedLocal
    def __html__(self, *, context=None):
        return render_attrs(self)


class Errors(set):
    @dispatch(
        attrs=EMPTY,
    )
    def __init__(self, *, parent, attrs, errors=None, template=None):
        super(Errors, self).__init__(errors or [])
        self._parent = parent
        self.attrs = attrs
        self.template = template

    def __str__(self):
        return self.__html__()

    def __bool__(self):
        return len(self) != 0

    # noinspection PyUnusedLocal
    def __html__(self, *, context=None):
        if not self:
            return ''

        from iommi.page import Fragment
        return Fragment(
            child='',
            tag='ul',
            attrs=self.attrs,
            template=self.template,
            children=[Fragment(tag='li') for error in self],
        ).bind(parent=self._parent).__html__()
