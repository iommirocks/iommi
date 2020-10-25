import itertools
import json
from abc import abstractmethod
from typing import (
    Any,
    Dict,
    Union,
)

from ._web_compat import (
    QueryDict,
    settings,
    template_types,
)
from tri_declarative import (
    dispatch,
    EMPTY,
    Namespace,
    Refinable,
)

from iommi._web_compat import (
    get_template,
    get_template_from_string,
    HttpResponse,
    HttpResponseBase,
    mark_safe,
    Template,
    TemplateDoesNotExist,
)
from iommi.base import (
    items,
    MISSING,
)
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
    Members
)
from iommi.traversable import (
    EvaluatedRefinable,
    Traversable,
)
from .reinvokable import reinvokable
from iommi.style import (
    get_iommi_style_name,
    get_style,
)
from .sort_after import sort_after


class Part(Traversable):
    """
    `Part` is the base class for parts of a page that can be rendered as html, and can respond to ajax and post.
    """

    include: bool = Refinable()  # This is evaluated, but first and in a special way
    after: Union[int, str] = EvaluatedRefinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[str, Any] = Refinable()  # not EvaluatedRefinable because this is an evaluated container so is special
    endpoints: Namespace = Refinable()
    assets: Namespace = Refinable()

    @reinvokable
    @dispatch(
        extra=EMPTY,
        include=True,
        assets=EMPTY,
    )
    def __init__(self, *, endpoints: Dict[str, Any] = None, include, assets=None, **kwargs):
        super(Part, self).__init__(include=include, **kwargs)
        collect_members(self, name='endpoints', items=endpoints, cls=Endpoint)
        # What I would love to do here is collect all my childrens assets, but I think
        # I can't do that before my children are properly bound.  So instead I store
        # only my own assets in assets and later do a grand collecting exercise
        self.assets = {k: v for k, v in Namespace({}, assets).items() if v is not None}

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
        assert self._is_bound, 'This object is unbound, you probably forgot to call `.bind(request=request)` on it'
        return self.__html__()

    def bind(self, *, parent=None, request=None):
        result = super(Part, self).bind(parent=parent, request=request)
        if result is None:
            return None
        del self
        bind_members(result, name='endpoints')
        return result

    def all_assets(self) -> Namespace:
        """Return this parts assets as well as all assets used by its children."""
        assert self._is_bound
        # TODO: In this implementation only parts can have assets, traversables can not.
        # But for that to work in the current implementation it must further be true
        # that only parts can contain parts (and other traversables other than Members do not).
        # I believe that is correct, but one could envision a system where asset
        # collection is part of traversable.  Thoughts?

        def get_assets(t):
            if isinstance(t, Part):
                return Namespace(t.assets, *(get_assets(m) for m in t.iommi_bound_members().values()))
            elif isinstance(t, Members):
                return Namespace(*(get_assets(m) for m in t.iommi_bound_members().values()))
            else:
                return Namespace()

        return get_assets(self)

    @dispatch
    def render_to_response(self, **kwargs):
        request = self.get_request()
        req_data = request_data(request)

        def dispatch_response_handler(r):
            if isinstance(r, HttpResponseBase):
                return r
            elif isinstance(r, Part):
                # We can't do r.bind(...).render_to_response() because then we recurse in here
                # r also has to be bound already
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

        return HttpResponse(render_root(part=self, **kwargs))


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
    # Is this the right order?  That is should assets from the parts or from the style
    # take precedence (aka override each other when the name is identical).  I mean ideally
    # overriding only happens for deduplication (e.g. the same component is used
    # multiple times on the same page).
    style_assets = {
        k: v.bind(request=part.get_request())
        for k, v in itertools.chain(root_style.assets.items(), part.all_assets().items())
    }

    assert template_name, f"{root_style_name} doesn't have a base_template defined"
    assert content_block_name, f"{root_style_name} doesn't have a content_block defined"

    title = getattr(part, 'title', None)

    if title is None:
        parts = getattr(part, 'parts', None)
        if parts is not None:
            for p in parts.values():
                title = getattr(p, 'title', None)
                if title is not None:
                    break

    from iommi.debug import iommi_debug_panel
    from iommi import Page
    from iommi.fragment import Container

    context = dict(
        container=Container(_name='Container').bind(parent=part),
        content=part.__html__(**render),
        title=title if title not in (None, MISSING) else '',
        iommi_debug_panel=iommi_debug_panel(part) if iommi_debug_on() else '',
        assets=sort_after(style_assets),
        **(part.context if isinstance(part, Page) else {}),
        **context,
    )

    template_string = '{% extends "' + template_name + '" %} {% block ' + \
        content_block_name + \
        ' %}{{ iommi_debug_panel }}{{ content }}{% endblock %}'
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
    else:
        return str(part)
