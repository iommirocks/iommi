from typing import (
    Dict,
    Optional,
    Type,
    Union,
    List,
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
    render_template,
    Template,
    format_html,
)
from iommi.attrs import (
    Attrs,
    render_attrs,
)
from iommi.base import build_as_view_wrapper
from iommi.debug import (
    endpoint__debug_tree,
    iommi_debug_on,
)
from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.part import (
    as_html,
    Part,
    PartType,
)
from iommi.traversable import (
    evaluate_strict_container,
    EvaluatedRefinable,
    reinvokable,
    Traversable,
    get_root,
)

# https://html.spec.whatwg.org/multipage/syntax.html#void-elements
_void_elements = ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']


def fragment__render(fragment, context):
    if not fragment.include:
        return ''

    rendered_children = fragment.render_text_or_children(context=context)

    if fragment.template:
        return render_template(fragment.get_request(), fragment.template, {**context, **fragment._evaluate_parameters, rendered_children: rendered_children})

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

        h1 = Fragment(children__text='Tony', tag='h1')

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

    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    tag = EvaluatedRefinable()
    template: Union[str, Template] = EvaluatedRefinable()

    @reinvokable
    @dispatch(
        tag=None,
        children=EMPTY,
        attrs__class=EMPTY,
        attrs__style=EMPTY,
    )
    def __init__(self, text=None, *, children: Optional[Dict[str, PartType]] = None, **kwargs):
        super(Fragment, self).__init__(**kwargs)
        collect_members(self, name='children', items=children, cls=Fragment, unknown_types_fall_through=True)

    def render_text_or_children(self, context):
        return format_html(
            '{}' * len(self.children),
            *[
                as_html(part=x, context=context)
                for x in self.children.values()
            ])

    def __repr__(self):
        return f'<{self.__class__.__name__} tag:{self.tag} attrs:{dict(self.attrs) if self.attrs else None!r}>'

    def on_bind(self) -> None:
        bind_members(self, name='children', unknown_types_fall_through=True)

        # Fragment children are special and they can be raw str/int etc but
        # also callables. We need to evaluate them!
        self.children = evaluate_strict_container(self.children, **self._evaluate_parameters)
        self._bound_members.children._bound_members = self.children

    @dispatch(
        render=fragment__render,
    )
    def __html__(self, *, render=None):
        return render(fragment=self, context=self._evaluate_parameters)

    def own_evaluate_parameters(self):
        return dict(fragment=self)


class Header(Fragment):
    """
    `Header` is a special fragment that automatically calculates its level.
    This means that you will get `h1` for the top level, `h2` for the next level,
    and so on. If you want a specific `h1`/`h2`/etc tag use `Fragment`.

    The header level is only increased by the existence of `Header` objects,
    so putting a manual `h1` somewhere won't make the next `Header` into a
    `h2` tag.
    """

    def on_bind(self):
        if self.tag is None:
            root = get_root(self)
            if not hasattr(root, '_iommi_auto_header_set'):
                root._iommi_auto_header_set = set()

            real_level = self.iommi_dunder_path.count('__')
            root._iommi_auto_header_set.add(real_level)

            level = 0
            for i in range(real_level+1):
                if i in root._iommi_auto_header_set:
                    level += 1

            self.tag = f'h{level}'
        super(Header, self).on_bind()


@with_meta
@declarative(
    parameter='_parts_dict',
    is_member=lambda obj: isinstance(obj, (Part, str, Template)),
    sort_key=lambda x: 0,
)
class Page(Part):
    title: str = EvaluatedRefinable()
    member_class: Type[Fragment] = Refinable()
    context = Refinable()  # context is evaluated, but in a special way so gets no EvaluatedRefinable type

    class Meta:
        member_class = Fragment

    @reinvokable
    @dispatch(
        parts=EMPTY,
        endpoints__debug_tree=Namespace(
            include=lambda endpoint, **_: iommi_debug_on(),
            func=endpoint__debug_tree,
        ),
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
            if not isinstance(v, (dict, Traversable)):
                return Fragment(children__text=v, _name=k)
            else:
                return v

        _parts_dict = {k: as_fragment_if_needed(k, v) for k, v in _parts_dict.items()}
        parts = Namespace({k: as_fragment_if_needed(k, v) for k, v in parts.items()})

        collect_members(self, name='parts', items=parts, items_dict=_parts_dict, cls=self.get_meta().member_class)

    def on_bind(self) -> None:
        bind_members(self, name='parts')
        self.context = evaluate_strict_container(self.context or {}, **self._evaluate_parameters)
        if self.context and self._parent != None:
            assert False, 'context is only valid on the root page'

    def own_evaluate_parameters(self):
        return dict(page=self)

    @dispatch(
        render=lambda rendered: format_html('{}' * len(rendered), *rendered.values())
    )
    def __html__(self, *, render=None):
        rendered = {
            name: as_html(part=part, context=self._evaluate_parameters)
            for name, part in self.parts.items()
        }

        return render(rendered)

    def as_view(self):
        return build_as_view_wrapper(self)


class Html:
    def __getattr__(self, tag):
        def fragment_constructor(*parts: List[PartType], children=None, **kwargs):
            if parts is not None:
                children = children or {}
                for i, child in enumerate(parts):
                    children[f'child{i if i>0 else ""}'] = child

            return Fragment(tag=tag, children=children, **kwargs)

        return fragment_constructor


html = Html()
