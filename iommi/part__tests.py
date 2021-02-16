from django.utils.html import format_html
from django.utils.safestring import mark_safe
from tri_struct import Struct

from iommi import (
    Header,
    Page,
    register_style,
)
from iommi._web_compat import Template
from iommi.part import (
    as_html,
    get_title,
    render_root,
    request_data,
)
from iommi.style import Style
from iommi.style_base import base
from tests.helpers import req


def test_request_data():
    r = Struct(method='POST', POST='POST', GET='GET')
    assert request_data(r) == 'POST'
    r.method = 'GET'
    assert request_data(r) == 'GET'


def test_as_html():
    # str case
    assert format_html('{}', as_html(part='foo', context={})) == 'foo'
    assert format_html('{}', as_html(part='<foo>bar</foo>', context={})) == '&lt;foo&gt;bar&lt;/foo&gt;'
    assert format_html('{}', as_html(part=mark_safe('<foo>bar</foo>'), context={})) == '<foo>bar</foo>'

    # Template case
    request = req('get')
    assert format_html('{}', as_html(request=request, part=Template('foo'), context={})) == 'foo'
    assert format_html('{}', as_html(request=request, part=Template('<foo>bar</foo>'), context={})) == '<foo>bar</foo>'

    # __html__ attribute case
    assert format_html('{}', as_html(part=Struct(__html__=lambda: 'foo'), context={})) == 'foo'
    assert (
        format_html('{}', as_html(part=Struct(__html__=lambda: '<foo>bar</foo>'), context={}))
        == '&lt;foo&gt;bar&lt;/foo&gt;'
    )
    assert (
        format_html('{}', as_html(part=Struct(__html__=lambda: mark_safe('<foo>bar</foo>')), context={}))
        == '<foo>bar</foo>'
    )

    assert as_html(request=req('get'), part=None, context={}) == ''


def test_as_html_integer():
    assert as_html(part=123, context={}) == '123'


def test_context_processor_is_called_on_render_root():
    style_name = 'test_context_processor_is_called_on_render_root'
    style = Style(
        base,
        base_template='test_context_processor_is_called_on_render_root.html',
    )
    register_style(style_name, style)

    part = Page(
        context__root_part_context_variable='root_part_context_variable',
        iommi_style=style_name,
    )

    t = render_root(
        part=part.bind(request=req('get')),
        context=dict(my_context_variable='my_context_variable'),
    )
    assert t == 'context_processor_is_called\nroot_part_context_variable\nmy_context_variable\n'


def test_get_title_of_header():
    assert get_title(Header(children__foo='foo', children__bar='qwe').bind(request=req('get'))) == 'foo'
