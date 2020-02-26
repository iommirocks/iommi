import json
from abc import abstractmethod
from typing import (
    Any,
    Dict,
    Union,
)

from django.conf import settings
from django.http import (
    HttpResponse,
    QueryDict,
)
from django.http.response import HttpResponseBase
from django.utils.safestring import mark_safe
from tri_declarative import (
    dispatch,
    EMPTY,
    Namespace,
    Refinable,
)

from iommi._web_compat import (
    get_template_from_string,
    Template,
)
from iommi.base import MISSING
from iommi.debug import iommi_debug_on
from iommi.endpoint import (
    DISPATCH_PATH_SEPARATOR,
    Endpoint,
    InvalidEndpointPathException,
    perform_ajax_dispatch,
    perform_post_dispatch,
)
from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.traversable import (
    EvaluatedRefinable,
    Traversable,
)

DEFAULT_BASE_TEMPLATE = 'base.html'
DEFAULT_CONTENT_BLOCK = 'content'


class Part(Traversable):
    """
    `Part` is the base class for parts of a page that can be rendered as html, and can respond to ajax and post.
    """

    include: bool = Refinable()  # This is evaluated, but first and in a special way
    after: Union[int, str] = EvaluatedRefinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[str, Any] = Refinable()  # not EvaluatedRefinable because this is an evaluated container so is special
    endpoints: Namespace = Refinable()

    @dispatch(
        extra=EMPTY,
        include=True,
    )
    def __init__(self, *, endpoints: Dict[str, Any] = None, include, **kwargs):
        assert include is MISSING or isinstance(include, bool) or callable(include)
        super(Part, self).__init__(include=include, **kwargs)
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
        assert self._is_bound, 'This object is unbound, you probably forgot to call `.bind(request=request)` on it'
        return self.__html__()

    def bind(self, *, parent=None, request=None):
        result = super(Part, self).bind(parent=parent, request=request)
        if result is None:
            return None
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


PartType = Union[Part, str, Template]


def request_data(request):
    if request is None:
        return QueryDict()

    if request.method == 'POST':
        return request.POST
    elif request.method == 'GET':
        return request.GET
    else:
        assert False, f'unsupported request method {request.method}'


def as_html(*, part: PartType, context):
    if isinstance(part, str):
        return part
    elif isinstance(part, Template):
        template = part
        return mark_safe(template.render(context=context))
    elif hasattr(part, '__html__'):
        return part.__html__(context=context)
    else:
        return str(part)
