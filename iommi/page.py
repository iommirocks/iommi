from typing import (
    Dict,
    Type,
)

from tri_declarative import (
    declarative,
    dispatch,
    EMPTY,
    Namespace,
    Refinable,
    with_meta,
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
from iommi.evaluate import evaluate_strict_container
from iommi.fragment import Fragment
from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.part import (
    as_html,
    Part,
    PartType,
)
from iommi.reinvokable import reinvokable
from iommi.traversable import (
    EvaluatedRefinable,
    Traversable,
)


@with_meta
@declarative(
    parameter='_parts_dict',
    is_member=lambda obj: isinstance(obj, (Part, str) + template_types),
    sort_key=lambda x: 0,
)
class Page(Part):
    """
    A page is used to compose iommi parts into a bigger whole.

    See the `howto <https://docs.iommi.rocks/en/latest/howto.html#parts-pages>`_ for example usages.
    """

    title: str = EvaluatedRefinable()
    member_class: Type[Fragment] = Refinable()
    context = Refinable()  # context is evaluated, but in a special way so gets no EvaluatedRefinable type

    class Meta:
        member_class = Fragment

    @reinvokable
    @dispatch(
        parts=EMPTY,
        context=EMPTY,
    )
    def __init__(
        self,
        *,
        _parts_dict: Dict[str, PartType] = None,
        parts: dict,
        **kwargs
    ):
        super(Page, self).__init__(**kwargs)
        
        self.parts = {}  # This is just so that the repr can survive if it gets triggered before parts is set properly

        # First we have to up sample parts that aren't Part into Fragment
        def as_fragment_if_needed(k, v):
            if v is None:
                return None
            if not isinstance(v, (dict, Traversable)):
                return Fragment(children__text=v, _name=k)
            else:
                return v

        _parts_dict = {k: as_fragment_if_needed(k, v) for k, v in items(_parts_dict)}
        parts = Namespace({k: as_fragment_if_needed(k, v) for k, v in items(parts)})

        collect_members(self, name='parts', items=parts, items_dict=_parts_dict, cls=self.get_meta().member_class)

    def on_bind(self) -> None:
        bind_members(self, name='parts')
        if self.context and self.iommi_parent() != None:
            assert False, 'The context property is only valid on the root page'

    def own_evaluate_parameters(self):
        return dict(page=self)

    @dispatch(
        render=lambda rendered: format_html('{}' * len(rendered), *values(rendered))
    )
    def __html__(self, *, render=None):
        self.context = evaluate_strict_container(self.context or {}, **self.iommi_evaluate_parameters())
        rendered = {
            name: as_html(request=self.get_request(), part=part, context=self.iommi_evaluate_parameters())
            for name, part in items(self.parts)
        }

        return render(rendered)

    def as_view(self):
        return build_as_view_wrapper(self)
