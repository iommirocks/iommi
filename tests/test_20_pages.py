from django.test import override_settings
from tri_struct import Struct

from iommi import (
    html,
    Page,
)
from iommi._web_compat import (
    format_html,
)
from iommi.attrs import Attrs
from iommi.page import Fragment
from iommi.part import as_html
from iommi.traversable import declared_members
from tests.helpers import (
    prettify,
    req,
)


def test_page_constructor():
    class MyPage(Page):
        h1 = html.h1()

    my_page = MyPage(
        parts__foo=html.div(_name='foo'),
        parts__bar=html.div()
    )

    assert ['h1', 'foo', 'bar'] == list(declared_members(my_page).parts.keys())
    my_page = my_page.bind(request=None)
    assert ['h1', 'foo', 'bar'] == list(my_page.parts.keys())


@override_settings(
    MIDDLEWARE_CLASSES=[],
)
def test_page_render():
    class MyPage(Page):
        header = html.h1('Foo')
        body = html.div('bar bar')

    my_page = MyPage()
    request = req('get')
    request.user = Struct()
    my_page = my_page.bind(request=request)

    response = my_page.render_to_response()

    expected_html = '''
        <html>
            <head></head>
            <body>
                 <h1> Foo </h1>
                 <div> bar bar </div>
            </body>
        </html>
    '''

    prettified_expected = prettify(expected_html)
    prettified_actual = prettify(response.content)
    assert prettified_expected == prettified_actual


def test_fragment__render__simple_cases():
    assert format_html('{}', html.h1('foo').bind(parent=None)) == '<h1>foo</h1>'
    assert format_html('{}', Fragment('foo<foo>').bind(parent=None)) == 'foo&lt;foo&gt;'


def test_fragment_repr():
    assert repr(Fragment(tag='foo', attrs=Attrs(None, **{'foo-bar': 'baz'}))) == "<Fragment tag:foo attrs:{'class': Namespace(), 'style': Namespace(), 'foo-bar': 'baz'}>"


def test_promote_str_to_fragment_for_page():
    class MyPage(Page):
        foo = 'asd'

    page = MyPage()
    assert isinstance(declared_members(page).parts.foo, Fragment)


def test_as_html_integer():
    assert as_html(part=123, context={}) == '123'
