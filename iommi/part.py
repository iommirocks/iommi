import inspect
import json
from abc import abstractmethod
from typing import (
    Any,
    Dict,
    Union,
)

from django.core.serializers.json import DjangoJSONEncoder

from iommi._web_compat import (
    HttpResponse,
    HttpResponseBase,
    Template,
    get_template_from_string,
    render_template,
)
from iommi.base import (
    MISSING,
    NOT_BOUND_MESSAGE,
    items,
)
from iommi.debug import (
    get_instantiated_at_info,
    iommi_debug_on,
)
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    Namespace,
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
    refine_done_members,
)
from iommi.shortcut import with_defaults
from iommi.style import get_style_object
from iommi.traversable import Traversable

from ._web_compat import (
    QueryDict,
    settings,
    template_types,
)
from .refinable import (
    EvaluatedRefinable,
    Refinable,
    RefinableMembers,
    SpecialEvaluatedRefinable,
)
from .sort_after import sort_after


class Part(Traversable):
    """
    `Part` is the base class for parts of a page that can be rendered as html, and can respond to ajax and post.

    See the `howto <https://docs.iommi.rocks/en/latest/cookbook_parts_pages.html#parts-pages>`_ for example usages.
    """

    include: bool = SpecialEvaluatedRefinable()
    after: Union[int, str] = EvaluatedRefinable()
    extra: Dict[str, Any] = Refinable()
    # not EvaluatedRefinable because this is an evaluated container so is special
    extra_evaluated: Dict[str, Any] = Refinable()
    assets: Namespace = RefinableMembers()
    endpoints: Namespace = RefinableMembers()
    # Only the assets used by this part
    assets: Namespace = RefinableMembers()

    class Meta:
        extra = EMPTY

    @with_defaults(
        include=True,
    )
    def __init__(self, _collect_instantiated_at_info=True, **kwargs):
        super(Part, self).__init__(**kwargs)

        if _collect_instantiated_at_info:
            frame = inspect.currentframe()
            self._instantiated_at_info = get_instantiated_at_info(frame.f_back)

    def on_refine_done(self):
        from iommi.asset import Asset

        refine_done_members(self, name='endpoints', members_from_namespace=self.endpoints, cls=Endpoint)
        refine_done_members(self, name='assets', members_from_namespace=self.assets, cls=Asset)
        super().on_refine_done()

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
    def perform_dispatch(self, **kwargs):
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
                return HttpResponse(json.dumps(r, cls=DjangoJSONEncoder), content_type='application/json')

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

        return None

    @dispatch
    def render_to_response(self, **kwargs):
        dispatch = self.perform_dispatch(**kwargs)
        if dispatch is not None:
            return dispatch

        response = HttpResponse(render_root(part=self, **kwargs))
        response.iommi_part = self
        return response

    def iommi_collected_assets(self):
        main_menu = getattr(self.get_request(), 'iommi_main_menu', None)
        menu_assets = main_menu.assets() if main_menu else {}

        return {**menu_assets, **sort_after(self.iommi_root()._iommi_collected_assets)}


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
    root_style = get_style_object(part)
    template_name = root_style.base_template
    content_block_name = root_style.content_block

    # Render early so that all the binds are forced before we look at all_assets,
    # since they are populated as a side-effect
    content = part.__html__(**render)

    assets = part.iommi_collected_assets()

    assert template_name, f"{root_style} doesn't have a base_template defined"
    assert content_block_name, f"{root_style} doesn't have a content_block defined"

    title = get_title(part)

    from iommi import Page
    from iommi.debug import iommi_debug_panel
    from iommi.fragment import Container

    request = part.get_request()

    context = dict(
        container=Container(_name='Container').refine_done(parent=part).bind(parent=part),
        content=content,
        title=title if title not in (None, MISSING) else '',
        iommi_debug_panel=(
            iommi_debug_panel(part) if iommi_debug_on() and '_iommi_disable_debug_panel' not in request.GET else ''
        ),
        iommi_language_code=getattr(request, 'LANGUAGE_CODE', settings.LANGUAGE_CODE),
        assets=assets,
        request=request,
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
    return get_template_from_string(template_string).render(context=context, request=request)


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
        return render_template(template=template, request=request, context=context)
    elif hasattr(part, '__html__'):
        return part.__html__()
    elif part is None:
        return ''
    else:
        return str(part)
