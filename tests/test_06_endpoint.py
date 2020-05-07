import json

import pytest
from django.http import HttpResponse
from django.test import override_settings
from tri_declarative import with_meta
from tri_struct import Struct

from iommi import (
    Page,
    Table,
    Part,
    html,
)
from iommi.endpoint import (
    find_target,
    InvalidEndpointPathException,
    perform_post_dispatch,
    path_join,
)
from iommi.part import request_data
from iommi.traversable import (
    build_long_path,
    get_path_by_long_path,
)
from tests.helpers import (
    request_with_middleware,
    StubTraversable,
    req,
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

    response = request_with_middleware(response=MyPage(), data={'/qwe': ''})
    data = json.loads(response.content)
    assert data == dict(error='Invalid endpoint path')


def test_find_target():
    # To build paths: _declared_members: Struct, and optionally name
    # To find target: _long_path_by_path: Dict on root

    bar = StubTraversable(_name='bar')
    foo = StubTraversable(
        _name='foo',
        members=Struct(
            bar=bar,
        ),
    )
    root = StubTraversable(
        _name='root',
        members=Struct(
            foo=foo
        ),
    )
    root = root.bind(request=None)

    target = find_target(path='/foo/bar', root=root)
    assert target._declared is bar
    assert build_long_path(target) == 'foo/bar'


def test_find_target_with_invalid_path():
    bar = StubTraversable(_name='bar')
    foo = StubTraversable(
        _name='foo',
        members=Struct(
            bar=bar,
        ),
    )
    root = StubTraversable(
        _name='root',
        members=Struct(
            foo=foo
        ),
    )
    root = root.bind(request=None)

    with pytest.raises(InvalidEndpointPathException) as e:
        find_target(path='/foo/bar/baz', root=root)

    assert str(e.value) == "Given path /foo/bar/baz not found.\n" \
                           "    Short alternatives:\n" \
                           "        ''\n" \
                           "        foo\n" \
                           "        bar\n" \
                           "    Long alternatives:\n" \
                           "        ''\n" \
                           "        foo\n" \
                           "        foo/bar"


def test_middleware_fallthrough_on_non_part():
    sentinel = object()
    assert request_with_middleware(response=sentinel, data={}) is sentinel


@override_settings(DEBUG=True)
def test_dispatch_auto_json():
    @with_meta
    class MyPart(Part):
        class Meta:
            @staticmethod
            def endpoints__foo__func(value, **_):
                return dict(a=1, b='asd', c=value)

    p = MyPart(
        endpoints__foo__func=lambda value, **_: dict(a=1, b='asd', c=value)
    ).bind(request=req('get', **{'/foo': '7'}))
    r = p.render_to_response()
    assert r['Content-type'] == 'application/json'
    assert json.loads(r.content) == dict(a=1, b='asd', c='7')


def test_dispatch_return_http_response():
    p = Part(
        endpoints__foo__func=lambda value, **_: HttpResponse(f'foo {value}')
    )
    r = p.bind(request=req('get', **{'/foo': '7'})).render_to_response()
    assert r.content == b'foo 7'


def test_dispatch_return_part():
    p = Part(
        endpoints__foo__func=lambda root, value, **_: html.div('foo', attrs__class__bar=True).bind(parent=root)
    )
    r = p.bind(request=req('get', **{'/foo': '7'})).render_to_response()
    assert b'<div class="bar">foo</div>' in r.content


def test_invalid_enpoint_path(settings):
    p = Page().bind(request=req('get', **{'/foo': ''}))
    assert p.render_to_response().content == b'{"error": "Invalid endpoint path"}'

    settings.DEBUG = True
    with pytest.raises(InvalidEndpointPathException) as e:
        p.render_to_response()

    assert str(e.value) == """
Given path /foo not found.
    Short alternatives:
        ''
        debug_tree
    Long alternatives:
        ''
        endpoints/debug_tree
""".strip()


def test_unsupported_request_method():
    with pytest.raises(AssertionError):
        request_data(Struct(method='OPTIONS'))


def test_custom_endpoint_on_page():
    p = Page(endpoints__test__func=lambda value, **_: 7).bind(request=req('get', **{'/test': ''}))

    assert p.endpoints.test.include is True
    assert p.endpoints.test.endpoint_path == '/test'
    assert p.render_to_response().content == b'7'


def test_perform_post_dispatch_error_message():
    target = StubTraversable(_name='root', members=Struct(foo=StubTraversable(_name='foo')))
    target = target.bind(request=None)

    with pytest.raises(InvalidEndpointPathException) as e:
        perform_post_dispatch(root=target, path='/foo', value='')

    assert str(e.value) == "Target <tests.helpers.StubTraversable foo (bound) path:'foo'> has no registered post_handler"


def test_path_join():
    assert path_join(None, 'foo') == 'foo'
    assert path_join('', 'foo') == 'foo'
    assert path_join('foo', 'bar') == 'foo/bar'
    assert path_join('foo', 'bar', separator='#') == 'foo#bar'
