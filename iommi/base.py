import json
from abc import abstractmethod
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
    HttpResponseBase,
)
from django.utils.safestring import mark_safe
from tri_declarative import (
    dispatch,
    EMPTY,
    Namespace,
    Refinable,
    refinable,
    setdefaults_path,
)
from tri_struct import Struct

from iommi._web_compat import (
    get_template_from_string,
    QueryDict,
    Template,
)
from iommi.endpoint import (
    DISPATCH_PATH_SEPARATOR,
    Endpoint,
    InvalidEndpointPathException,
    perform_ajax_dispatch,
    perform_post_dispatch,
)
from iommi.style import apply_style
from iommi.traversable import (
    EvaluatedRefinable,
    no_copy_on_bind,
    should_include,
    sort_after,
    Traversable,
)

DEFAULT_BASE_TEMPLATE = 'base.html'
DEFAULT_CONTENT_BLOCK = 'content'

MISSING = object()


def iommi_debug_on():
    return getattr(settings, 'IOMMI_DEBUG', settings.DEBUG)


def evaluated_refinable(f):
    f = refinable(f)
    f.__iommi__evaluated = True
    return f


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

    if iommi_debug_on():
        from iommi.debug import iommi_debug_panel
        context['iommi_debug_panel'] = iommi_debug_panel(part)
    else:
        context['iommi_debug_panel'] = ''

    template_string = '{% extends "' + template_name + '" %} {% block ' + content_block_name + ' %}{{ iommi_debug_panel }}{{ content }}{% endblock %}'
    return get_template_from_string(template_string).render(context=context, request=part.get_request())


class Part(Traversable):
    """
    `Part` is the base class for parts of a page that can be rendered as html, and can respond to ajax and post.
    """

    include: bool = EvaluatedRefinable()
    after: Union[int, str] = EvaluatedRefinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[str, Any] = Refinable()  # not EvaluatedRefinable because this is an evaluated container so is special
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
        return mark_safe(template.render(context=context))
    else:
        return part.__html__(context=context)


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


FORBIDDEN_NAMES = {x for x in dir(Traversable)}


class ForbiddenNamesException(Exception):
    pass


def collect_members(parent, *, name: str, items_dict: Dict = None, items: Dict[str, Any] = None, cls: Type) -> Dict[str, Any]:
    forbidden_names = FORBIDDEN_NAMES & (set((items_dict or {}).keys()) | set((items or {}).keys()))
    if forbidden_names:
        raise ForbiddenNamesException(f'The names {", ".join(sorted(forbidden_names))} are reserved by iommi, please pick other names')

    assert name != 'items'
    unbound_items = {}
    _unapplied_config = {}

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
                    _unapplied_config[key] = item
                else:
                    item = setdefaults_path(
                        Namespace(),
                        item,
                        call_target__cls=cls,
                        _name=key,
                    )
                    unbound_items[key] = item()

    if _unapplied_config:
        parent._unapplied_config[name] = _unapplied_config

    members = Struct({x._name: x for x in unbound_items.values()})
    parent._declared_members[name] = members


@no_copy_on_bind
class Members(Traversable):
    """
    Internal iommi class that holds members of another class, for example the columns of a `Table` instance.
    """

    @dispatch
    def __init__(self, *, _declared_members, **kwargs):
        super(Members, self).__init__(**kwargs)
        self._declared_members = _declared_members
        self._bound_members = Struct()

    def on_bind(self) -> None:
        for m in self._declared_members.values():
            bound = m.bind(parent=self)
            del m  # to not make a mistake below
            if should_include(bound):
                self._bound_members[bound._name] = bound

        sort_after(self._bound_members)


def bind_members(parent: Part, *, name: str) -> None:
    m = Members(
        _name=name,
        _declared_members=parent._declared_members[name],
    )
    setattr(parent, name, m._bound_members)
    setattr(parent._bound_members, name, m)
    m.bind(parent=parent)


def create_as_view_from_as_page(cls, name, *, kwargs, title, parts):
    def view_wrapper(request, **url_kwargs):
        return getattr(cls(**kwargs), f'{name}_page')(title=title, parts=parts, **url_kwargs).bind(request=request).render_to_response()

    view_wrapper.__name__ = f'{cls.__name__}{repr(Namespace(kwargs))[len("Namespace"):]}.{name}_view'
    view_wrapper.__doc__ = cls.__doc__

    return view_wrapper


class Errors(set):
    @dispatch(
        attrs=EMPTY,
    )
    def __init__(self, *, parent, attrs, errors=None, template=None):
        super(Errors, self).__init__(errors or [])
        self._parent = parent
        self.attrs = attrs
        self.template = template
        self.iommi_style = None
        apply_style(self)

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
            children=[Fragment(error, tag='li') for error in self],
        ).bind(parent=self._parent).__html__()
