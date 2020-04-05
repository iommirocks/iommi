import pytest
from django.template import RequestContext
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from tri_struct import Struct

from iommi import (
    Fragment,
    Header,
    html,
    Page,
)
from iommi._web_compat import Template
from iommi.part import as_html
from tests.helpers import req


def test_basic_render():
    f = Fragment('foo').bind(request=None)
    assert f.__html__() == 'foo'


def test_render_multiple_children():
    f = Fragment('foo', children__bar='bar').bind(request=None)
    assert f.__html__() == 'foobar'


def test_nested():
    f = Fragment('foo', children__bar=Fragment('bar')).bind(request=None)
    assert f._is_bound
    assert f._bound_members.children._bound_members.bar._is_bound
    assert f.__html__() == 'foobar'


def test_tag():
    f = Fragment('foo', tag='div').bind(request=None)
    assert f.__html__() == '<div>foo</div>'


def test_attrs():
    f = Fragment(
        'foo',
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
    nested = Fragment('bar')
    f = Fragment('foo', children__bar=nested).bind(request=None)
    assert f._is_bound
    assert f._bound_members.children._bound_members.bar._is_bound
    assert not nested._is_bound
    assert f.__html__() == 'foobar'


def test_auto_h_tag():
    # Start at h1
    assert Header().bind(request=None).tag == 'h1'

    # Nesting doesn't increase level
    assert Fragment(Fragment(Header())).bind(request=None).__html__() == '<h1></h1>'

    # A header on a level increases the level for the next header
    assert Fragment(Fragment(Header(Header('h2')))).bind(request=None).__html__() == '<h1><h2>h2</h2></h1>'

    # Sibling headers get the same level
    assert Fragment(Fragment(Header(Header('h2'), children__another=Header('another h2')))).bind(request=None).__html__() == '<h1><h2>h2</h2><h2>another h2</h2></h1>'


def test_render_simple_tag():
    assert html.a('bar', attrs__href='foo').bind(parent=None).__html__() == '<a href="foo">bar</a>'


def test_render_empty_tag():
    assert html.br().bind(parent=None).__html__() == '<br>'


def test_fragment():
    foo = html.h1('asd').bind(parent=None)
    assert foo.__html__() == '<h1>asd</h1>'


def test_as_html():
    # str case
    assert format_html('{}', as_html(part='foo', context={})) == 'foo'
    assert format_html('{}', as_html(part='<foo>bar</foo>', context={})) == '&lt;foo&gt;bar&lt;/foo&gt;'
    assert format_html('{}', as_html(part=mark_safe('<foo>bar</foo>'), context={})) == '<foo>bar</foo>'

    # Template case
    c = RequestContext(req('get'))
    assert format_html('{}', as_html(part=Template('foo'), context=c)) == 'foo'
    assert format_html('{}', as_html(part=Template('<foo>bar</foo>'), context=c)) == '<foo>bar</foo>'

    # __html__ attribute case
    assert format_html('{}', as_html(part=Struct(__html__=lambda: 'foo'), context={})) == 'foo'
    assert format_html('{}', as_html(part=Struct(__html__=lambda: '<foo>bar</foo>'), context={})) == '&lt;foo&gt;bar&lt;/foo&gt;'
    assert format_html('{}', as_html(part=Struct(__html__=lambda: mark_safe('<foo>bar</foo>')), context={})) == '<foo>bar</foo>'


def test_html_builder():
    assert html.h1('foo').bind(request=None).__html__() == '<h1>foo</h1>'


def test_fragment_basic():
    assert Fragment('foo').bind(request=None).__html__() == 'foo'


def test_fragment_with_tag():
    assert Fragment('foo', tag='h1').bind(request=None).__html__() == '<h1>foo</h1>'


def test_fragment_with_two_children():
    assert Fragment('foo', tag='h1', children__foo='asd').bind(request=None).__html__() == '<h1>fooasd</h1>'


def test_void_element():
    for tag in ['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']:
        assert Fragment(tag=tag).bind(request=None).__html__() == f'<{tag}>'


def test_void_element_error():
    with pytest.raises(AssertionError):
        assert html.br('foo').bind(request=None).__html__()


@pytest.skip('Broken right now')
def test_override_attrs():
    class MyPage(Page):
       title = html.h1('Supernaut')

    assert MyPage().bind().__html__() == '<h1>Supernaut</h1>'

    assert MyPage(parts__title__attrs__class__foo=True).bind().__html__() == '<h1 class="foo">Supernaut</h1>'
