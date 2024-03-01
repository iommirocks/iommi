import json

import pytest
from django.http import HttpResponse
from django.test import override_settings

from iommi import (
    Field,
    Form,
    Page,
    Part,
    Table,
    html,
)
from iommi.declarative.with_meta import with_meta
from iommi.endpoint import (
    InvalidEndpointPathException,
    find_target,
    path_join,
    perform_post_dispatch,
)
from iommi.part import request_data
from iommi.struct import Struct
from iommi.traversable import (
    build_long_path,
)
from tests.helpers import (
    Basket,
    Box,
    Fruit,
    req,
    request_with_middleware,
)
from tests.models import (
    T1,
    T2,
)


@pytest.mark.django_db
def test_dispatch_error_message_to_client():
    class MyPage(Page):
        t1 = Table(
            auto__model=T1,
            columns__foo=dict(
                filter__include=True,
            ),
            columns__bar=dict(
                filter__include=True,
            ),
        )

        t2 = Table(
            auto__model=T2,
            columns__foo=dict(
                filter__include=True,
            ),
            columns__bar=dict(
                filter__include=True,
            ),
        )

    response = request_with_middleware(MyPage(), req('get', **{'/qwe': ''}))
    data = json.loads(response.content)
    assert data == dict(error='Invalid endpoint path')


def test_find_target():
    # To build paths: _declared_members: Struct, and optionally name
    # To find target: _long_path_by_path: Dict on root

    banana = Fruit()
    basket = Basket(fruits__banana=banana)
    root = Box(items__basket=basket)
    root = root.bind(request=None)

    target = find_target(path='/items/basket/fruits/banana', root=root)
    assert target._name == 'banana'
    assert build_long_path(target) == 'items/basket/fruits/banana'
    assert target.iommi_path == 'banana'


def test_find_target_with_invalid_path():
    banana = Fruit()
    basket = Basket(fruits__banana=banana)
    root = Box(items__basket=basket)
    root = root.bind(request=None)

    with pytest.raises(InvalidEndpointPathException) as e:
        find_target(path='/items/baz', root=root)

    assert str(e.value) == (
        "Given path /items/baz not found.\n"
        "    Short alternatives:\n"
        "        ''\n"
        "        basket\n"
        "        banana\n"
        "    Long alternatives:\n"
        "        ''\n"
        "        items/basket\n"
        "        items/basket/fruits/banana"
    )


def test_middleware_fallthrough_on_non_part():
    sentinel = object()
    assert request_with_middleware(sentinel, req('get')) is sentinel


@override_settings(DEBUG=True)
def test_dispatch_auto_json():
    @with_meta
    class MyPart(Part):
        class Meta:
            @staticmethod
            def endpoints__foo__func(value, **_):
                return dict(a=1, b='asd', c=value)

    p = MyPart().bind(request=req('get', **{'/foo': '7'}))
    r = p.render_to_response()
    assert r['Content-type'] == 'application/json'
    assert json.loads(r.content) == dict(a=1, b='asd', c='7')


def test_dispatch_return_http_response():
    p = Part(endpoints__foo__func=lambda value, **_: HttpResponse(f'foo {value}'))
    r = p.bind(request=req('get', **{'/foo': '7'})).render_to_response()
    assert r.content == b'foo 7'


def test_dispatch_return_part():
    p = Part(
        endpoints__foo__func=lambda request, **_: html.div('foo', attrs__class__bar=True).bind(request=request),
        endpoints__bar__func=lambda request, **_: html.div('bar', attrs__class__baz=True),
    )
    r = p.bind(request=req('get', **{'/foo': '7'})).render_to_response()
    assert b'<div class="bar">foo</div>' in r.content

    r = p.bind(request=req('get', **{'/bar': '7'})).render_to_response()
    assert b'<div class="baz">bar</div>' in r.content


def test_invalid_endpoint_path(settings):
    p = Page().bind(request=req('get', **{'/foo': ''}))
    assert p.render_to_response().content == b'{"error": "Invalid endpoint path"}'

    settings.DEBUG = True
    with pytest.raises(InvalidEndpointPathException) as e:
        p.render_to_response()

    assert (
        str(e.value)
        == """
Given path /foo not found.
    Short alternatives:
        ''
        debug_tree
        debug_templates_used
    Long alternatives:
        ''
        endpoints/debug_tree
        endpoints/debug_templates_used
""".strip()
    )


def test_unsupported_request_method():
    with pytest.raises(AssertionError):
        request_data(Struct(method='OPTIONS'))


def test_custom_endpoint_on_page():
    p = Page(endpoints__test__func=lambda value, **_: 7).bind(request=req('get', **{'/test': ''}))

    assert p.endpoints.test.include is True
    assert p.endpoints.test.endpoint_path == '/test'
    assert p.render_to_response().content == b'7'


class ExplodingForm(Form):
    def on_bind(self):
        raise Exception('Boom')


def test_post_not_trigger_bind():
    p = Page(
        parts=dict(
            form=Form(
                fields__foo=Field(),
            ),
            exploding_form=ExplodingForm(),
        )
    )

    p = p.bind(
        request=req(
            'post',
            **{
                '-': '',
                'foo': 'bar',
            },
        )
    )

    assert p.parts.form.fields.foo.value == 'bar'
    with pytest.raises(Exception) as e:
        # noinspection PyStatementEffect
        p.parts.exploding_form
    assert str(e.value) == 'Boom'


def test_ajax_not_trigger_bind():
    p = Page(
        parts=dict(
            form=Form(
                endpoints__foo__func=lambda value, **_: HttpResponse('bar'),
            ),
            exploding_form=ExplodingForm(),
        )
    )

    p = p.bind(
        request=req(
            'get',
            **{
                '/foo': '',
            },
        )
    )

    assert p.render_to_response().content == b'bar'

    with pytest.raises(Exception) as e:
        # noinspection PyStatementEffect
        p.parts.exploding_form
    assert str(e.value) == 'Boom'


def test_perform_post_dispatch_error_message():
    target = Basket(fruits__banana=Fruit())
    target = target.bind(request=None)

    with pytest.raises(InvalidEndpointPathException) as e:
        perform_post_dispatch(root=target, path='/banana', value='')

    assert str(e.value) == "Target <tests.helpers.Fruit banana (bound) path:'banana'> has no registered post_handler"


def test_path_join():
    assert path_join(None, 'foo') == 'foo'
    assert path_join('', 'foo') == 'foo'
    assert path_join('foo', 'bar') == 'foo/bar'
    assert path_join('foo', 'bar', separator='#') == 'foo#bar'


def test_perform_post_with_no_dispatch_parameter():
    target = Page().bind(request=req('post'))

    with pytest.raises(AssertionError) as e:
        target.render_to_response()

    assert str(e.value) == 'This request was a POST, but there was no dispatch command present.'
