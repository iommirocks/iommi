from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

from django.conf import settings
from django.utils.html import format_html
from iommi._web_compat import (
    render_template,
    Template,
)
from iommi.base import (
    as_html,
    bind_members,
    collect_members,
    evaluate_attrs,
    no_copy_on_bind,
    Part,
    PartType,
    evaluate_strict_container,
    EvaluatedRefinable,
    endpoint__debug_tree,
    iommi_debug_on,
    render_attrs,
)
from tri_declarative import (
    declarative,
    dispatch,
    EMPTY,
    Namespace,
    Refinable,
    with_meta,
    evaluate_strict,
)

# https://html.spec.whatwg.org/multipage/syntax.html#void-elements
_void_elements = ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']


def fragment__render(fragment, context):
    rendered_children = fragment.render_text_or_children(context=context)

    if fragment.template:
        return render_template(fragment.get_request(), fragment.template, {**context, **fragment.evaluate_parameters, rendered_children: rendered_children})

    is_void_element = fragment.tag in _void_elements

    if fragment.tag:
        if rendered_children:
            assert not is_void_element
            return format_html(
                '<{tag}{attrs}>{children}</{tag}>',
                tag=fragment.tag,
                attrs=render_attrs(fragment.attrs),
                children=rendered_children,
            )
        else:
            return format_html(
                '<{tag}{attrs}>' if is_void_element else '<{tag}{attrs}></{tag}>',
                tag=fragment.tag,
                attrs=render_attrs(fragment.attrs),
            )

    else:
        return format_html(
            '{}',
            rendered_children,
        )


class Fragment(Part):
    """
    `Fragment` is a class used to build small HTML fragments that plug into iommis structure.

    .. code:: python

        h1 = Fragment('Tony', tag='h1')

    It's easiest to use via the html builder:

    .. code:: python

        h1 = html.h1('Tony')

    Fragments are useful because attrs, template and tag are evaluated, so if
    you have a `Page` with a fragment in it you can configure it later:

    .. code:: python

        class MyPage(Page):
            header = html.h1(
                'Hi!',
                attrs__class__staff=
                    lambda fragment, **_: fragment.get_request().user.is_staff,
            )

    Rendering a `MyPage` will result in a `<h1>`, but if you do
    `MyPage(parts__header__tag='h2')` it will be rendered with a `<h2>`.
    """

    attrs: Dict[str, Any] = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    tag = EvaluatedRefinable()
    template: Union[str, Template] = EvaluatedRefinable()

    @dispatch(
        tag=None,
    )
    def __init__(self, child: PartType = None, *, children: Optional[List[PartType]] = None, **kwargs):
        super(Fragment, self).__init__(**kwargs)

        self._children = []  # TODO: _children to avoid colliding with Parts children() API. Not nice. We should do something nicer here.
        if child is not None:
            self._children.append(child)

        self._children.extend(children or [])

    def render_text_or_children(self, context):
        return format_html(
            '{}' * len(self._children),
            *[
                as_html(part=x, context=context)
                for x in self._children
            ])

    def __repr__(self):
        return f'<Fragment tag:{self.tag} attrs:{dict(self.attrs)!r}>'

    def on_bind(self) -> None:
        self._children = [evaluate_strict(x, **self.evaluate_parameters) for x in self._children]

    @dispatch(
        context=EMPTY,
        render=fragment__render,
    )
    def __html__(self, *, context=None, render=None):
        return render(fragment=self, context=context)

    def own_evaluate_parameters(self):
        return dict(fragment=self)


@no_copy_on_bind
@with_meta
@declarative(
    parameter='_parts_dict',
    is_member=lambda obj: isinstance(obj, (Part, str, Template)),
    sort_key=lambda x: 0,
)
class Page(Part):
    title: str = EvaluatedRefinable()
    member_class: Type[Fragment] = Refinable()

    class Meta:
        member_class = Fragment

    @dispatch(
        parts=EMPTY,
        endpoints__debug_tree=Namespace(
            include=lambda endpoint, **_: iommi_debug_on(),
            func=endpoint__debug_tree,
        ),
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
            if not isinstance(v, Part):
                return Fragment(v, _name=k)
            else:
                return v

        _parts_dict = {k: as_fragment_if_needed(k, v) for k, v in _parts_dict.items()}
        parts = Namespace({k: as_fragment_if_needed(k, v) for k, v in parts.items()})

        collect_members(self, name='parts', items=parts, items_dict=_parts_dict, cls=self.get_meta().member_class)

    def on_bind(self) -> None:
        bind_members(self, name='parts')

    def own_evaluate_parameters(self):
        return dict(page=self)

    @dispatch(
        context=EMPTY,
        render=lambda rendered: format_html('{}' * len(rendered), *rendered.values())
    )
    def __html__(self, *, context=None, render=None):
        rendered = {}
        for part in self.parts.values():
            assert part._name not in context
            rendered[part._name] = as_html(part=part, context=context)

        return render(rendered)


class Html:
    def __getattr__(self, tag):
        def fragment_constructor(child: PartType = None, **kwargs):
            return Fragment(tag=tag, child=child, **kwargs)
        return fragment_constructor


html = Html()
