import pytest
from django.test import override_settings
from tri_declarative import Namespace
from tri_struct import Struct

from iommi import MISSING
from iommi._web_compat import (
    format_html,
    mark_safe,
    RequestContext,
    Template,
)
from iommi.attrs import evaluate_attrs
from iommi.base import UnknownMissingValueException
from iommi.page import (
    Fragment,
    html,
)
from iommi.part import (
    as_html,
)
from iommi.traversable import (
    evaluate_strict_container,
)
from tests.helpers import (
    req,
)


def test_evaluate_attrs():
    actual = evaluate_attrs(
        Struct(
            attrs=Namespace(
                class__table=True,
                class__foo=lambda foo: True,
                data=1,
                data2=lambda foo: foo,
                style__foo=1,
                style__bar=lambda foo: f'foo{3}',
            ),
        ),
        foo=3
    )

    expected = {
        'class': {
            'table': True,
            'foo': True,
        },
        'style': {
            'foo': 1,
            'bar': 'foo3'
        },
        'data': 1,
        'data2': 3,
    }

    assert actual == expected


@override_settings(IOMMI_DEBUG=True)
def test_evaluate_attrs_show_debug_paths():
    actual = evaluate_attrs(
        Struct(
            attrs=Namespace(
                class__table=True,
            ),
            _name='foo',
            iommi_dunder_path='<path here>',
        ),
    )

    expected = {
        'class': {
            'table': True,
        },
        'data-iommi-path': '<path here>',
    }

    assert actual == expected


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
    assert format_html('{}', as_html(part=Struct(__html__=lambda context: 'foo'), context={})) == 'foo'
    assert format_html('{}', as_html(part=Struct(__html__=lambda context: '<foo>bar</foo>'), context={})) == '&lt;foo&gt;bar&lt;/foo&gt;'
    assert format_html('{}', as_html(part=Struct(__html__=lambda context: mark_safe('<foo>bar</foo>')), context={})) == '<foo>bar</foo>'


def test_evaluate_strict_container():
    assert evaluate_strict_container(Namespace(foo=1)) == Namespace(foo=1)
    assert evaluate_strict_container(Namespace(foo=lambda foo: foo), foo=3) == Namespace(foo=3)


def test_html_builder():
    assert html.h1('foo').bind(request=None).__html__() == '<h1>foo</h1>'


def test_fragment_basic():
    assert Fragment('foo').bind(request=None).__html__() == 'foo'


def test_fragment_with_tag():
    assert Fragment('foo', tag='h1').bind(request=None).__html__() == '<h1>foo</h1>'


def test_fragment_with_two_children():
    assert Fragment('foo', tag='h1', children__foo='asd').bind(request=None).__html__() == '<h1>fooasd</h1>'


def test_missing():
    assert str(MISSING) == 'MISSING'
    assert repr(MISSING) == 'MISSING'

    with pytest.raises(UnknownMissingValueException) as e:
        if MISSING:
            pass

    assert str(e.value) == 'MISSING is neither True nor False, is is unknown'
