import itertools
from unittest import mock

import pytest
from django.template import Template
from django.utils.html import format_html

from iommi import (
    Form,
    Fragment,
    Header,
    html,
    Page,
)
from iommi.attrs import Attrs
from iommi.evaluate import evaluate_strict
from iommi.fragment import fragment__render
from tests.helpers import (
    req,
    verify_part_html,
)


def test_basic_render():
    f = Fragment(children__text='foo').bind(request=None)
    assert f.__html__() == 'foo'


def test_render_multiple_children():
    f = Fragment(children__foo='foo', children__bar='bar').bind(request=None)
    assert f.__html__() == 'foobar'


def test_nested():
    f = Fragment(children__foo='foo', children__bar=Fragment(children__bar='bar')).bind(request=None)
    assert f._is_bound
    assert f._bound_members.children._bound_members.bar._is_bound
    assert f.__html__() == 'foobar'


def test_tag():
    f = Fragment(children__foo='foo', tag='div').bind(request=None)
    assert f.__html__() == '<div>foo</div>'


def test_attrs():
    f = Fragment(
        children__foo='foo',
        tag='div',
        attrs__class__foo=True,
        attrs__style__foo='foo',
        attrs__qwe='qwe',
    ).bind(request=None)
    assert f.__html__() == '<div class="foo" qwe="qwe" style="foo: foo">foo</div>'


def test_nested_attrs():
    f = Fragment(
        tag='div',
        children__text__tag='div',
        children__text__children__text='foo',
        children__text__attrs__class__foo=True,
        children__text__attrs__style__foo='foo',
        children__text__attrs__qwe='qwe',
    ).bind(request=None)
    assert f.__html__() == '<div><div class="foo" qwe="qwe" style="foo: foo">foo</div></div>'


def test_nested_attrs_lambda():
    f = Fragment(
        tag='div',
        children__text__tag='div',
        children__text__children__text='foo',
        children__text__attrs__qwe=lambda fragment, **_: fragment.tag,
    ).bind(request=None)
    assert f.__html__() == '<div><div qwe="div">foo</div></div>'


def test_nested_2():
    nested = Fragment(children__bar='bar')
    f = Fragment(children__foo='foo', children__bar=nested).bind(request=None)
    assert f._is_bound
    assert f._bound_members.children._bound_members.bar._is_bound
    assert not nested._is_bound
    assert f.__html__() == 'foobar'


def test_auto_h_tag():
    # Start at h1
    assert Header().bind(request=None).tag == 'h1'

    # Nesting doesn't increase level
    assert (
        Fragment(
            children__child=Fragment(
                children__child=Header(),
            )
        )
        .bind(request=None)
        .__html__()
        == '<h1></h1>'
    )

    # A header on a level increases the level for the next header
    assert (
        Fragment(
            children__child=Fragment(
                children__child=Header(
                    children__child=Header(
                        children__child='h2',
                    )
                )
            )
        )
        .bind(request=None)
        .__html__()
        == '<h1><h2>h2</h2></h1>'
    )

    # Sibling headers get the same level
    assert (
        Fragment(
            children__child=Fragment(
                children__child=Header(
                    children__child=Header(children__child='h2'),
                    children__another=Header(
                        children__child='another h2',
                    ),
                )
            )
        )
        .bind(request=None)
        .__html__()
        == '<h1><h2>h2</h2><h2>another h2</h2></h1>'
    )


def test_render_simple_tag():
    assert html.a('bar', attrs__href='foo').bind(parent=None).__html__() == '<a href="foo">bar</a>'


def test_render_empty_tag():
    assert html.br().bind(parent=None).__html__() == '<br>'


def test_fragment():
    foo = html.h1('asd').bind(parent=None)
    assert foo.__html__() == '<h1>asd</h1>'


def test_default_text():
    assert Fragment('foo').bind(request=None).__html__() == 'foo'


def test_html_builder():
    assert html.h1('foo').bind(request=None).__html__() == '<h1>foo</h1>'


def test_html_builder_multi_arg():
    assert html.h1('foo', 'bar').bind(request=None).__html__() == '<h1>foobar</h1>'
    nested = html.h1('foo', html.p('bar')).bind(request=None)
    assert nested.__html__() == '<h1>foo<p>bar</p></h1>'
    assert list(nested.children.keys()) == ['child', 'child2']


def test_fragment_basic():
    assert Fragment(children__child='foo').bind(request=None).__html__() == 'foo'


def test_fragment_with_tag():
    assert Fragment(children__child='foo', tag='h1').bind(request=None).__html__() == '<h1>foo</h1>'


def test_fragment_with_two_children():
    assert (
        Fragment(children__child='foo', tag='h1', children__foo='asd').bind(request=None).__html__()
        == '<h1>fooasd</h1>'
    )


def test_void_element():
    for tag in [
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
    ]:
        assert Fragment(tag=tag).bind(request=None).__html__() == f'<{tag}>'


def test_void_element_error():
    with pytest.raises(AssertionError):
        assert html.br('foo').bind(request=None).__html__()


def test_override_attrs():
    class MyPage(Page):
        title = html.h1('Supernaut')

    assert MyPage().bind().__html__() == '<h1>Supernaut</h1>'

    assert MyPage(parts__title__attrs__class__foo=True).bind().__html__() == '<h1 class="foo">Supernaut</h1>'


def test_override_attrs_explicit_fragment():
    class MyPage(Page):
        title = Fragment(
            tag='h1',
            children__text='Supernaut',
        )

    assert MyPage().bind().__html__() == '<h1>Supernaut</h1>'

    assert MyPage(parts__title__attrs__class__foo=True).bind().__html__() == '<h1 class="foo">Supernaut</h1>'


def test_request_in_evaluate_parameters():
    request = req('get', foo=7)

    class MyPage(Page):
        title = Fragment(
            tag='h1',
            children__text=lambda request, **_: request.GET['foo'],
        )

    assert '<h1>7</h1>' in MyPage().bind(request=request).render_to_response().content.decode()


def test_render_not_included_fragment():
    assert html.div('foo', include=False).bind(request=None) is None


def test_fragment__render__simple_cases():
    assert format_html('{}', html.h1('foo').bind(parent=None)) == '<h1>foo</h1>'
    assert format_html('{}', Fragment(children__child='foo<foo>').bind(parent=None)) == 'foo&lt;foo&gt;'

    assert fragment__render(Fragment(include=False).refine_done(), {}) == ''


def test_fragment_repr():
    assert (
        repr(Fragment(tag='foo', attrs=Attrs(None, **{'foo-bar': 'baz'})).refine_done())
        == "<Fragment tag:foo attrs:{'class': Namespace(), 'style': Namespace(), 'foo-bar': 'baz'}>"
    )


def test_fragment_repr_not_done():
    assert repr(Fragment(tag='foo', attrs=Attrs(None, **{'foo-bar': 'baz'}))) == "<Fragment>"


def test_h_tag_callable():
    p = Page(title=lambda request, **_: request.GET['foo']).bind(request=req('get', foo='title here'))
    assert '<h1>Title here</h1>' in p.__html__()


def test_fragment_meta():
    class MyFragment(Fragment):
        class Meta:
            tag = 'span'
            attrs__class__foo = True

    assert str(MyFragment().bind(request=req('get'))) == '<span class="foo"></span>'


def test_fragment_template_as_child():
    f = Fragment(Template('<div>{{ fragment.extra.foo }}</div> {{ request.GET.param }}'), extra__foo=7)
    assert str(f.bind(request=req('get', param=11))) == '<div>7</div> 11'


def test_fragment_template_as_template_kwarg():
    f = Fragment(
        'child text',
        template=Template('<div>{{ fragment.extra.foo }}</div> {{ rendered_children }} {{ request.GET.param }}'),
        extra__foo=7,
    )
    assert str(f.bind(request=req('get', param=11))) == '<div>7</div> child text 11'


def test_foo():
    f = Fragment(children__child=Fragment('child'))
    assert f.bind().__html__() == 'child'
    assert f.bind().__html__() == 'child'


def test_barz():
    p = Page(
        parts__footer=html.div(
            html.hr(),
        )
    )
    assert p.bind().__html__() == '<div><hr></div>'
    assert p.bind().__html__() == '<div><hr></div>'


def test_bar():
    class ExamplesPage(Page):
        footer = html.div(
            html.hr(),
        )

    p = ExamplesPage()
    assert p.bind().__html__() == '<div><hr></div>'
    assert p.bind().__html__() == '<div><hr></div>'


def test_open_tag():
    f = Fragment().bind()
    assert f.iommi_open_tag() == ''
    assert f.iommi_close_tag() == ''

    f = Fragment(tag='div').bind()
    assert f.iommi_open_tag() == '<div>'
    assert f.iommi_close_tag() == '</div>'


def test_build_and_bind_h_tag():
    form = Form().bind()
    assert form.h_tag == ''

    form = Form(title='title').bind()
    assert form.h_tag._is_bound
    assert form.h_tag._name == 'h_tag'
    assert form.h_tag.iommi_parent() is form
    assert form.h_tag.__html__() == '<h1>Title</h1>'

    form = Form(h_tag=html.div('hello')).bind()
    assert form.h_tag._is_bound
    assert form.h_tag._name == 'h_tag'
    assert form.h_tag.iommi_parent() is form
    assert form.h_tag.__html__() == '<div>hello</div>'


@mock.patch('iommi.evaluate.evaluate_strict')
def test_only_evaluate_callbacks(mock_evaluate_strict):
    counter = itertools.count()

    def side_effect(func_or_value, __signature=None, __match_empty=True, **kwargs):
        assert callable(func_or_value)
        next(counter)
        return evaluate_strict(func_or_value, __signature, __match_empty, **kwargs)

    mock_evaluate_strict.side_effect = side_effect
    part = html.p(
        children__static='This is static ',
        children__dynamic=lambda **_: 'Not so static',
    ).bind()

    verify_part_html(part=part, expected_html='<p> This is static Not so static </p>')

    assert next(counter) == 1
