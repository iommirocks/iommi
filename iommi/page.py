from collections.abc import Callable

from iommi._web_compat import (
    format_html,
    get_template_types,
)
from iommi.base import (
    NOT_BOUND_MESSAGE,
    build_as_view_wrapper,
    items,
    values,
)
from iommi.declarative import declarative
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    Namespace,
)
from iommi.evaluate import (
    find_static_items,
)
from iommi.fragment import (
    Fragment,
    Header,
    build_and_bind_h_tag,
)
from iommi.member import (
    bind_members,
    refine_done_members,
)
from iommi.part import (
    Part,
    PartType,
    as_html,
)
from iommi.refinable import (
    EvaluatedRefinable,
    Refinable,
    RefinableMembers,
    SpecialEvaluatedRefinable,
)
from iommi.shortcut import with_defaults
from iommi.sort_after import sort_after
from iommi.traversable import Traversable


@declarative(
    parameter='parts_dict',
    is_member=lambda obj: isinstance(obj, (Part, str) + get_template_types()),
    sort_key=lambda x: 0,
    add_init_kwargs=False,
)
class Page(Part):
    """
    A page is used to compose iommi parts into a bigger whole.

    See the `howto <https://docs.iommi.rocks//cookbook_parts_pages.html#parts-pages>`_ for example usages.
    """

    title: str = EvaluatedRefinable()
    member_class: type[Fragment] = Refinable()
    context: dict | Callable[..., dict] = Refinable()
    h_tag: Fragment | str = SpecialEvaluatedRefinable()
    parts: dict[str, PartType] = RefinableMembers()

    class Meta:
        member_class = Fragment

        parts = EMPTY

    @with_defaults(
        h_tag__call_target=Header,
    )
    def __init__(self, **kwargs):
        super(Page, self).__init__(**kwargs)

    def on_refine_done(self):
        # First we have to up sample parts that aren't Part into Fragment
        def as_fragment_if_needed(k, v):
            if v is None:
                return None
            if not isinstance(v, dict | Traversable):
                return Fragment(children__text=v, _name=k)
            else:
                return v

        _parts_dict = {k: as_fragment_if_needed(k, v) for k, v in items(self.get_declared('parts_dict'))}
        self.parts = Namespace({k: as_fragment_if_needed(k, v) for k, v in items(self.parts)})

        refine_done_members(
            self,
            name='parts',
            members_from_namespace=self.parts,
            members_from_declared=_parts_dict,
            cls=self.member_class,
        )
        if isinstance(self.context, dict):
            # A callable context stays as is, it is evaluated into a dict by get_context
            self.context = Namespace(self.context)
        find_static_items(self.context)
        super(Page, self).on_refine_done()

    def on_bind(self) -> None:
        bind_members(self, name='parts')

        build_and_bind_h_tag(self)

    def own_evaluate_parameters(self):
        return dict(page=self)

    @dispatch(render=lambda rendered: format_html('{}' * len(rendered), *values(rendered)))
    def __html__(self, *, render=None):
        assert self._is_bound, NOT_BOUND_MESSAGE
        request = self.get_request()
        context = {**self.get_context(), **self.iommi_evaluate_parameters()}
        parts = dict(h_tag=self.h_tag)
        parts.update(items(self.parts))
        rendered = {
            name: as_html(
                request=request,
                part=part,
                context=context,
            )
            for name, part in items(sort_after(parts))
        }
        return render(rendered)

    def as_view(self):
        return build_as_view_wrapper(self)
