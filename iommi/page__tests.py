import itertools
from platform import python_implementation
from unittest import mock

import pytest
from django.template.loader import get_template
from django.test import override_settings

from iommi import (
    Fragment,
    html,
    Page,
)
from iommi._web_compat import (
    Template,
)
from iommi.evaluate import evaluate_strict
from iommi.member import _force_bind_all
from iommi.part import (
    as_html,
    render_root,
)
from tests.helpers import (
    prettify,
    req,
    user_req,
    verify_html,
)


def test_simple_page():
    class MyPage(Page):
        footer = html.div(
            html.hr(),
        )

    my_page = MyPage()
    my_page.bind(request=req('GET')).render_to_response()
    my_page.bind(request=req('GET')).render_to_response()


def test_page_constructor():
    class MyPage(Page):
        h1 = html.h1()

    my_page = MyPage(parts__foo=html.div(_name='foo'), parts__bar=html.div()).refine_done()

    assert list(my_page.iommi_namespace.parts.keys()) == ['h1', 'foo', 'bar']
    my_page = my_page.bind(request=None)
    assert list(my_page.parts.keys()) == ['h1', 'foo', 'bar']


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

    my_page = MyPage(parts__footer=html.div('footer'))
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
                 <div> footer </div>
            </body>
        </html>
    '''

    prettified_expected = prettify(expected_html)
    prettified_actual = prettify(response.content)
    assert prettified_expected == prettified_actual


def test_promote_str_to_fragment_for_page():
    class MyPage(Page):
        foo = 'asd'

    page = MyPage().refine_done()
    assert isinstance(page.iommi_namespace.parts.foo, Fragment)


def test_as_html_integer():
    assert as_html(part=123, context={}) == '123'


def test_page_context():
    class MyPage(Page):
        part1 = Template('Template: {{foo}}\n')
        part2 = html.div(template=Template('Template2: {{foo}}\n'))
        part3 = get_template('test_page_context.html')

        class Meta:
            context__foo = 'foo'

    assert MyPage().bind(request=req('get')).__html__().strip() == 'Template: foo\nTemplate2: foo\nTemplate3: foo'


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
    assert (
        '<h1 class="foo">Foo</h1>'
        == Page(title='foo', h_tag__attrs__class__foo=True).bind(request=req('get')).__html__()
    )


def test_page_h_tag():
    assert '<h1>$$$</h1>' in Page(title='$$$').bind().__html__()
    assert '<b>$$$</b>' in Page(title='$$$', h_tag__tag='b').bind().__html__()
    assert '<b>$$$</b>' in Page(h_tag=html.b('$$$')).bind().__html__()
    assert 'None' not in Page(h_tag=None).bind().__html__()
    assert 'None' not in Page(h_tag__include=False).bind().__html__()


def test_sort_after_h_tag():
    verify_html(
        actual_html=render_root(
            part=Page(
                title='My title',
                parts__foo=html.p('foo', after='bar'),
                parts__bar=html.p('bar', after=0),
                parts__baz=html.p('baz'),
            ).bind()
        ),
        # language=HTML
        expected_html='''
            <!DOCTYPE html>
            <html>
                <head>
                    <title> My title </title>
                </head>
                <body>
                    <p> bar </p>
                    <p> foo </p>
                    <h1> My title </h1>
                    <p> baz </p>
                </body>
            </html>
        ''',
    )


def test_custom_h_tag():
    verify_html(
        actual_html=render_root(
            part=Page(
                h_tag=html.b('custom h_tag'),
                parts__foo=html.p('foo', after=0),
            ).bind()
        ),
        # language=HTML
        expected_html='''
            <!DOCTYPE html>
            <html>
                <head>
                    <title> </title>
                </head>
                <body>
                    <p> foo </p>
                    <b> custom h_tag </b>
                </body>
            </html>
        ''',
    )


@mock.patch('iommi.evaluate.evaluate_strict')
def test_only_evaluate_callbacks(mock_evaluate_strict):
    counter = itertools.count()

    def side_effect(func_or_value, __signature=None, __match_empty=True, **kwargs):
        assert callable(func_or_value)
        next(counter)
        return evaluate_strict(func_or_value, __signature, __match_empty, **kwargs)

    mock_evaluate_strict.side_effect = side_effect
    part = Page(
        context=dict(
            static_part='This is a static thing',
            callback_part=lambda **_: 'This is a callback',
        ),
    ).bind()

    part.__html__()

    assert part.context == {
        'callback_part': 'This is a callback',
        'static_part': 'This is a static thing',
    }
    assert next(counter) == 1
