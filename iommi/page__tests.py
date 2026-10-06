import itertools
import json
from platform import python_implementation
from unittest import mock

import pytest
from django.template.loader import get_template
from django.test import override_settings

from iommi import (
    Fragment,
    Page,
    Table,
    html,
)
from iommi._web_compat import (
    Template,
)
from iommi.base import NOT_BOUND_MESSAGE
from iommi.evaluate import evaluate_strict
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

    assert list(my_page.iommi_namespace.get('parts').keys()) == ['h1', 'foo', 'bar']
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
        <html lang="en">
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
    assert isinstance(page.iommi_namespace.get('parts').foo, Fragment)


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


def test_page_context_is_evaluated_when_an_endpoint_renders_a_nested_part():
    calls = []

    def foo(page, **_):
        calls.append(page)
        return 'foo'

    class MyPage(Page):
        table = Table(
            rows=[],
            container__children__extra=Fragment(template=Template('Context: {{ foo }}')),
        )

        class Meta:
            context__foo = foo

    response = MyPage().as_view()(req('get', **{'/table/tbody': ''}))

    assert 'Context: foo' in json.loads(response.content)['html']
    assert len(calls) == 1


def test_page_context_is_evaluated_once_per_request():
    calls = []

    def foo(**_):
        calls.append(1)
        return 'foo'

    class MyPage(Page):
        part1 = Template('Template: {{ foo }}\n')
        part2 = html.div(template=Template('Template2: {{ foo }}\n'))

        class Meta:
            context__foo = foo

    page = MyPage().bind(request=req('get'))
    assert page.__html__().strip() == 'Template: foo\nTemplate2: foo'
    assert page.get_context() == {'foo': 'foo'}
    assert len(calls) == 1


def test_nested_page_context_composes_with_the_parents():
    class Nested(Page):
        part = Template('Nested: {{ foo }} {{ bar }}\n')

        class Meta:
            @staticmethod
            def context__bar(page, **_):
                return f'nested {page._name}'

    class Root(Page):
        part = Template('Root: {{ foo }} {{ bar }}\n')
        nested = Nested()

        class Meta:
            context__foo = 'root foo'
            context__bar = 'root bar'

    html = Root().bind(request=req('get')).__html__()

    assert 'Root: root foo root bar' in html
    assert 'Nested: root foo nested nested' in html


def test_page_context_can_be_a_callable_returning_a_dict():
    calls = []

    def context(page, **_):
        calls.append(page)
        return {'foo': 'foo', 'bar': 'bar'}

    class MyPage(Page):
        part = Template('{{ foo }} {{ bar }}\n')

    page = MyPage(context=context).bind(request=req('get'))
    assert calls == []

    assert page.__html__().strip() == 'foo bar'
    assert page.get_context() == {'foo': 'foo', 'bar': 'bar'}
    assert len(calls) == 1


def test_page_context_callable_is_evaluated_when_an_endpoint_renders_a_nested_part():
    class MyPage(Page):
        table = Table(
            rows=[],
            container__children__extra=Fragment(template=Template('Context: {{ foo }}')),
        )

    response = MyPage(context=lambda **_: {'foo': 'foo'}).as_view()(req('get', **{'/table/tbody': ''}))

    assert 'Context: foo' in json.loads(response.content)['html']


def test_nested_page_context_callable_composes_with_the_parents():
    class Nested(Page):
        part = Template('Nested: {{ foo }} {{ bar }}\n')

    class Root(Page):
        nested = Nested(context=lambda **_: {'bar': 'nested bar'})

    html = Root(context=lambda **_: {'foo': 'root foo', 'bar': 'root bar'}).bind(request=req('get')).__html__()

    assert 'Nested: root foo nested bar' in html


def test_page_context_callable_must_return_a_dict():
    page = Page(context=lambda **_: 'not a dict').bind(request=req('get'))

    with pytest.raises(AssertionError) as e:
        page.get_context()

    assert str(e.value) == 'context needs to be a dict, or a callable that returns a dict'


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
            <html lang="en">
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
            <html lang="en">
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
        return evaluate_strict(
            func_or_value,
            __signature=__signature,
            __match_empty=__match_empty,
            **kwargs,
        )

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


def test_get_context_requires_bind():
    with pytest.raises(AssertionError) as e:
        Page(context__foo='foo').refine_done().get_context()

    assert str(e.value) == NOT_BOUND_MESSAGE
