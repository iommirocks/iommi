from typing import (
    Dict,
    Type,
    Union,
)

from iommi._web_compat import (
    format_html,
    template_types,
)
from iommi.base import (
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
from iommi.declarative.with_meta import with_meta
from iommi.evaluate import (
    evaluate_as_needed,
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


@with_meta
@declarative(
    parameter='parts_dict',
    is_member=lambda obj: isinstance(obj, (Part, str) + template_types),
    sort_key=lambda x: 0,
    add_init_kwargs=False,
)
class Page(Part):
    """
    A page is used to compose iommi parts into a bigger whole.

    See the `howto <https://docs.iommi.rocks/en/latest/cookbook_parts_pages.html#parts-pages>`_ for example usages.
    """

    title: str = EvaluatedRefinable()
    member_class: Type[Fragment] = Refinable()
    context = SpecialEvaluatedRefinable()
    h_tag: Union[Fragment, str] = SpecialEvaluatedRefinable()
    parts: Dict[str, PartType] = RefinableMembers()

    class Meta:
        member_class = Fragment

        parts = EMPTY
        context = EMPTY

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
            if not isinstance(v, (dict, Traversable)):
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
            cls=self.get_meta().member_class,
        )
        find_static_items(self.context)
        super(Page, self).on_refine_done()

    def on_bind(self) -> None:
        bind_members(self, name='parts')
        if self.context and self.iommi_parent() is not None:
            assert False, 'The context property is only valid on the root page'

        build_and_bind_h_tag(self)

    def own_evaluate_parameters(self):
        return dict(page=self)

    @dispatch(render=lambda rendered: format_html('{}' * len(rendered), *values(rendered)))
    def __html__(self, *, render=None):
        self.context = evaluate_as_needed(self.context or {}, self.iommi_evaluate_parameters())
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
