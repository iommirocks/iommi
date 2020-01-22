from bs4 import BeautifulSoup
from django.test import override_settings
from iommi import (
    Page,
    html,
)
from tri_struct import Struct

from tests.helpers import req


def test_page_constructor():
    class MyPage(Page):
        h1 = html.h1()

    my_page = MyPage(
        parts__foo=html.div(name='foo'),
        parts__bar=html.div()
    )

    assert ['h1', 'foo', 'bar'] == list(my_page.declared_parts.keys())
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
