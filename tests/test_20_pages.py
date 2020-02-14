from bs4 import BeautifulSoup
from django.test import override_settings
from iommi import (
    Page,
    html,
)
from iommi._web_compat import (
    format_html,
)
from iommi.page import Fragment
from iommi.render import Attrs
from tri_struct import Struct

from tests.helpers import req


def test_page_constructor():
    class MyPage(Page):
        h1 = html.h1()

    my_page = MyPage(
        parts__foo=html.div(_name='foo'),
        parts__bar=html.div()
    )

    assert ['h1', 'foo', 'bar'] == list(my_page.declared_members.parts.keys())
    my_page.bind(request=None)
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
    my_page.bind(request=request)

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

    actual = BeautifulSoup(response.content, 'html.parser').prettify()
    expected = BeautifulSoup(expected_html, 'html.parser').prettify()
    assert actual == expected


def test_fragment__render__simple_cases():
    assert format_html('{}', html.h1('foo')) == '<h1>foo</h1>'
    assert format_html('{}', Fragment('foo<foo>')) == 'foo&lt;foo&gt;'


def test_fragment_repr():
    assert repr(Fragment(tag='foo', attrs=Attrs(None, **{'foo-bar': 'baz'}))) == "<Fragment tag:foo attrs:{'foo-bar': 'baz'}>"


def test_promote_str_to_fragment_for_page():
    class MyPage(Page):
        foo = 'asd'

    page = MyPage()
    assert isinstance(page.declared_members.parts.foo, Fragment)
