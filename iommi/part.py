import json
from abc import abstractmethod
from typing import (
    Any,
    Dict,
    Union,
)

from tri_declarative import (
    dispatch,
    EMPTY,
    Namespace,
    Refinable,
)

from iommi._web_compat import (
    get_template_from_string,
    HttpResponse,
    HttpResponseBase,
    mark_safe,
    Template,
)
from iommi.base import (
    items,
    MISSING,
    NOT_BOUND_MESSAGE,
)
from iommi.debug import (
    iommi_debug_on,
)
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
from iommi.style import (
    get_iommi_style_name,
    get_style,
)
from iommi.traversable import (
    EvaluatedRefinable,
    Traversable,
)
from ._web_compat import (
    QueryDict,
    settings,
    template_types,
)
from .reinvokable import reinvokable
from .sort_after import sort_after


class Part(Traversable):
    """
    `Part` is the base class for parts of a page that can be rendered as html, and can respond to ajax and post.

    See the `howto <https://docs.iommi.rocks/en/latest/howto.html#parts-pages>`_ for example usages.
    """

    include: bool = Refinable()  # This is evaluated, but first and in a special way
    after: Union[int, str] = EvaluatedRefinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[
        str, Any
    ] = Refinable()  # not EvaluatedRefinable because this is an evaluated container so is special
    endpoints: Namespace = Refinable()
    # Only the assets used by this part
    assets: Namespace = Refinable()

    @reinvokable
    @dispatch(
        extra=EMPTY,
        include=True,
    )
    def __init__(self, *, endpoints: Dict[str, Any] = None, assets: Dict[str, Any] = None, include, **kwargs):
        from iommi.asset import Asset

        super(Part, self).__init__(include=include, **kwargs)
        collect_members(self, name='endpoints', items=endpoints, cls=Endpoint)
        collect_members(self, name='assets', items=assets, cls=Asset)

        if iommi_debug_on():
            import inspect

            self._instantiated_at_frame = inspect.currentframe().f_back

    @dispatch(
        render=EMPTY,
    )
    @abstractmethod
    def __html__(self, *, render=None):
        assert False, 'Not implemented'  # pragma: no cover, no mutate

    def __str__(self):
        assert self._is_bound, NOT_BOUND_MESSAGE
        return self.__html__()

    def bind(self, *, parent=None, request=None):
        result = super(Part, self).bind(parent=parent, request=request)
        if result is None:
            return None
        del self
        bind_members(result, name='endpoints')
        bind_members(result, name='assets', lazy=False)
        result.iommi_root()._iommi_collected_assets.update(result.assets)

        return result

    @dispatch
    def render_to_response(self, **kwargs):
        request = self.get_request()
        req_data = request_data(request)

        def dispatch_response_handler(r):
            if isinstance(r, HttpResponseBase):
                return r
            elif isinstance(r, Part):
                if not r._is_bound:
                    r = r.bind(request=request)
                return HttpResponse(render_root(part=r, **kwargs))
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

        dispatch_commands = {key: value for key, value in items(req_data) if key.startswith(dispatch_prefix)}
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
        else:
            if request.method == 'POST':
                assert False, 'This request was a POST, but there was no dispatch command present.'

        response = HttpResponse(render_root(part=self, **kwargs))
        response.iommi_part = self
        return response

    def iommi_collected_assets(self):
        return sort_after(self.iommi_root()._iommi_collected_assets)


def get_title(part):
    from iommi import Header

    if isinstance(part, Header):
        for text in part.children.values():
            return text

    title = getattr(part, 'title', None)

    if title is None:
        parts = getattr(part, 'parts', None)
        if parts is not None:
            for p in parts.values():
                title = get_title(p)
                if title is not None:
                    break

    return title


@dispatch(
    render=EMPTY,
    context=EMPTY,
)
def render_root(*, part, context, **render):
    assert part._is_bound
    root_style_name = get_iommi_style_name(part)
    root_style = get_style(root_style_name)
    template_name = root_style.base_template
    content_block_name = root_style.content_block

    # Render early so that all the binds are forced before we look at all_assets,
    # since they are populated as a side-effect
    content = part.__html__(**render)

    assets = part.iommi_collected_assets()

    assert template_name, f"{root_style_name} doesn't have a base_template defined"
    assert content_block_name, f"{root_style_name} doesn't have a content_block defined"

    title = get_title(part)

    from iommi.debug import iommi_debug_panel
    from iommi import Page
    from iommi.fragment import Container

    context = dict(
        container=Container(_name='Container').bind(parent=part),
        content=content,
        title=title if title not in (None, MISSING) else '',
        iommi_debug_panel=iommi_debug_panel(part) if iommi_debug_on() and '_iommi_disable_debug_panel' not in part.get_request().GET else '',
        assets=assets,
        **(part.context if isinstance(part, Page) else {}),
        **context,
    )

    template_string = (
        '{% extends "'
        + template_name
        + '" %} {% block '
        + content_block_name
        + ' %}{{ iommi_debug_panel }}{{ content }}{% endblock %}'
    )
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


def as_html(*, request=None, part: PartType, context):
    if isinstance(part, str):
        return part
    elif isinstance(part, template_types):
        from django.template import RequestContext

        assert not isinstance(context, RequestContext)
        template = part
        return mark_safe(template.render(context=RequestContext(request, context)))
    elif hasattr(part, '__html__'):
        return part.__html__()
    elif part is None:
        return ''
    else:
        return str(part)
