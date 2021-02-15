from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from tri_declarative import (
    dispatch,
    EMPTY,
    Namespace,
    Refinable,
    setdefaults_path,
)

from iommi._web_compat import (
    format_html,
    render_template,
    Template,
)
from iommi.attrs import (
    Attrs,
    render_attrs,
)
from iommi.base import (
    capitalize,
    MISSING,
    NOT_BOUND_MESSAGE,
    values,
)
from iommi.evaluate import evaluate_strict_container
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
)

# https://html.spec.whatwg.org/multipage/syntax.html#void-elements
_void_elements = [
    'area',
    'base',
    'br',
    'col',
    'embed',
    'hr',
    'img',
    'input',
    'link',
    'meta',
    'param',
    'source',
    'track',
    'wbr',
]


def fragment__render(fragment, context):
    if not fragment.include:
        return ''

    rendered_children = fragment.render_text_or_children(context=context)

    if fragment.template:
        return render_template(
            fragment.get_request(),
            fragment.template,
            dict(**context, **fragment.iommi_evaluate_parameters(), rendered_children=rendered_children),
        )

    is_void_element = fragment.tag in _void_elements

    if fragment.tag:
        if rendered_children:
            assert not is_void_element, f'{fragment.tag} is a void element, but it has children: {rendered_children}'
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


class Tag:
    def iommi_open_tag(self):
        if self.tag is None:
            return ''
        else:
            return format_html('<{}{}>', self.tag, self.attrs)

    def iommi_close_tag(self):
        if self.tag is None:
            return ''
        else:
            return format_html('</{}>', self.tag)


class Fragment(Part, Tag):
    """
    `Fragment` is a class used to build small HTML fragments that plug into iommis structure.

    .. test
        from iommi.fragment import Fragment

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
                    lambda request, **_: request.user.is_staff,
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
        if text is not None:
            setdefaults_path(
                children,
                text=text,
            )
        self._iommi_saved_params['text'] = text
        collect_members(self, name='children', items=children, cls=Fragment, unknown_types_fall_through=True)

    def render_text_or_children(self, context):
        request = self.get_request()
        return format_html(
            '{}' * len(self.children),
            *[as_html(part=x, context=context, request=request) for x in values(self.children)],
        )

    def __repr__(self):
        return f'<{self.__class__.__name__} tag:{self.tag} attrs:{dict(self.attrs) if self.attrs else None!r}>'

    def on_bind(self) -> None:
        bind_members(self, name='children', unknown_types_fall_through=True)

        # Fragment children are special and they can be raw str/int etc but
        # also callables. We need to evaluate them!
        children = evaluate_strict_container(self.children, **self.iommi_evaluate_parameters())
        self.children.update(children)
        self._bound_members.children._bound_members.update(children)

    @dispatch(
        render=fragment__render,
    )
    def __html__(self, *, render=None):
        assert self._is_bound, NOT_BOUND_MESSAGE
        return render(
            fragment=self,
            context=self.get_context(),
        )

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
            root = self.iommi_root()
            if not hasattr(root, '_iommi_auto_header_set'):
                root._iommi_auto_header_set = set()

            real_level = self.iommi_dunder_path.count('__')
            root._iommi_auto_header_set.add(real_level)

            level = 0
            for i in range(real_level + 1):
                if i in root._iommi_auto_header_set:
                    level += 1

            self.tag = f'h{level}'
        super(Header, self).on_bind()


def build_and_bind_h_tag(p):
    if isinstance(p.h_tag, Namespace):
        if p.title not in (None, MISSING):
            p.h_tag = p.h_tag(_name='h_tag', children__text=capitalize(p.title)).bind(parent=p)
        else:
            p.h_tag = ''
    else:
        p.h_tag = p.h_tag.bind(parent=p)


class Container(Fragment):
    """
    The main container for iommi. This class is useful when you want to apply styling or change the tag of what iommi produces for its content inside your body tag.
    """

    pass


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
