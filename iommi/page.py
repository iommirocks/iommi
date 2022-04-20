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
from iommi.evaluate import evaluate_strict_container
from iommi.fragment import (
    build_and_bind_h_tag,
    Fragment,
    Header,
)
from iommi.member import (
    bind_members,
    refine_done_members,
)
from iommi.part import (
    as_html,
    Part,
    PartType,
)
from iommi.refinable import (
    EvaluatedRefinable,
    Refinable,
    RefinableMembers,
)
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
    context = Refinable()  # context is evaluated, but in a special way so gets no EvaluatedRefinable type
    # h_tag is evaluated, but in a special way so gets no EvaluatedRefinable type
    h_tag: Union[Fragment, str] = Refinable()
    parts: Dict[str, PartType] = RefinableMembers()

    class Meta:
        member_class = Fragment

        parts = EMPTY
        context = EMPTY
        h_tag__call_target = Header

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

        refine_done_members(self, name='parts', members_from_namespace=self.parts, members_from_declared=_parts_dict, cls=self.get_meta().member_class)

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
        self.context = evaluate_strict_container(self.context or {}, **self.iommi_evaluate_parameters())
        request = self.get_request()
        context = {**self.get_context(), **self.iommi_evaluate_parameters()}
        rendered = {'h_tag': as_html(request=request, part=self.h_tag, context=context)}
        rendered.update(
            {
                name: as_html(request=request, part=part, context=context)
                for name, part in items(self.parts)
            }
        )

        return render(rendered)

    def as_view(self):
        return build_as_view_wrapper(self)
