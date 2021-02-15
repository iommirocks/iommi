from platform import python_implementation

import pytest
from django.test import override_settings

from iommi import (
    Fragment,
    html,
    Page,
)
from iommi._web_compat import (
    Template,
)
from iommi.member import _force_bind_all
from iommi.part import as_html
from iommi.traversable import declared_members
from tests.helpers import (
    prettify,
    req,
    user_req,
)


def test_page_constructor():
    class MyPage(Page):
        h1 = html.h1()

    my_page = MyPage(parts__foo=html.div(_name='foo'), parts__bar=html.div())

    assert ['h1', 'foo', 'bar'] == list(declared_members(my_page).parts.keys())
    my_page = my_page.bind(request=None)
    assert ['h1', 'foo', 'bar'] == list(my_page.parts.keys())


@pytest.mark.skipif(python_implementation() == 'PyPy', reason='Intermittently fails on pypy for unknown reasons.')
@override_settings(
    MIDDLEWARE_CLASSES=[],
)
def test_page_render():
    # Working around some weird issue with pypy3+django3.0
    from django.conf import settings

    settings.DEBUG = False
    # end workaround

    class MyPage(Page):
        header = html.h1('Foo')
        body = html.div('bar bar')

    my_page = MyPage()
    my_page = my_page.bind(request=user_req('get'))

    response = my_page.render_to_response()

    expected_html = '''
        <!DOCTYPE html>
        <html>
            <head>
                <title></title>
            </head>
            <body>
                 <h1> Foo </h1>
                 <div> bar bar </div>
            </body>
        </html>
    '''

    prettified_expected = prettify(expected_html)
    prettified_actual = prettify(response.content)
    assert prettified_expected == prettified_actual


def test_promote_str_to_fragment_for_page():
    class MyPage(Page):
        foo = 'asd'

    page = MyPage()
    assert isinstance(declared_members(page).parts.foo, Fragment)


def test_as_html_integer():
    assert as_html(part=123, context={}) == '123'


def test_page_context():
    class MyPage(Page):
        part1 = Template('Template: {{foo}}\n')
        part2 = html.div(template=Template('Template2: {{foo}}'))

        class Meta:
            context__foo = 'foo'

    assert MyPage().bind(request=req('get')).__html__() == 'Template: foo\nTemplate2: foo'


def test_invalid_context_specified():
    class Nested(Page):
        class Meta:
            context__foo = 1

    class Root(Page):
        nested = Nested()

    with pytest.raises(AssertionError) as e:
        root = Root().bind(request=None)
        _force_bind_all(root.parts)

    assert str(e.value) == 'The context property is only valid on the root page'


def test_as_view():
    view = Page(parts__foo='##foo##').as_view()
    assert '##foo##' in view(req('get')).content.decode()


def test_title_basic():
    assert '<h1>Foo</h1>' == Page(title='foo').bind(request=req('get')).__html__()


def test_title_empty():
    assert '' in Page().bind(request=req('get')).__html__()


def test_title_attr():
    assert '<h1 class="foo">Foo</h1>' == Page(title='foo', h_tag__attrs__class__foo=True).bind(request=req('get')).__html__()
