import json

import pytest
from django.db import models
from django.test import override_settings
from tri_declarative import Namespace
from tri_struct import Struct

from iommi import Part
from iommi._web_compat import (
    format_html,
    HttpResponse,
    mark_safe,
)
from iommi._web_compat import (
    RequestContext,
    Template,
)
from iommi.attrs import evaluate_attrs
from iommi.endpoint import (
    find_target,
    InvalidEndpointPathException,
    perform_post_dispatch,
)
from iommi.page import (
    Fragment,
    html,
    Page,
)
from iommi.part import (
    as_html,
    request_data,
)
from iommi.table import Table
from iommi.traversable import (
    build_long_path,
    evaluate_strict_container,
)
from tests.helpers import (
    req,
    request_with_middleware,
    StubTraversable,
)


class T1(models.Model):
    foo = models.CharField(max_length=255)
    bar = models.CharField(max_length=255)

    class Meta:
        ordering = ('id',)


class T2(models.Model):
    foo = models.CharField(max_length=255)
    bar = models.CharField(max_length=255)

    class Meta:
        ordering = ('id',)


@pytest.mark.django_db
def test_dispatch_error_message_to_client():
    class MyPage(Page):
        t1 = Table(
            auto__model=T1,
            columns__foo=dict(
                filter__include=True,
                filter__field__include=True,
            ),
            columns__bar=dict(
                filter__include=True,
                filter__field__include=True,
            ),
        )

        t2 = Table(
            auto__model=T2,
            columns__foo=dict(
                filter__include=True,
                filter__field__include=True,
            ),
            columns__bar=dict(
                filter__include=True,
                filter__field__include=True,
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
    assert html.a('bar', attrs__href='foo').__html__() == '<a href="foo">bar</a>'


def test_render_empty_tag():
    assert html.br().__html__() == '<br>'


def test_fragment():
    foo = html.h1('asd')
    assert foo.__html__() == '<h1>asd</h1>'


def test_perform_post_dispatch_error_message():
    target = StubTraversable(_name='root', members=Struct(foo=StubTraversable(_name='foo')))
    target = target.bind(request=None)

    with pytest.raises(InvalidEndpointPathException) as e:
        perform_post_dispatch(root=target, path='/foo', value='')

    assert str(e.value) == "Target <tests.helpers.StubTraversable foo (bound) path:'foo'> has no registered post_handler"


def test_dunder_path_is_fully_qualified_and_skipping_root():
    foo = StubTraversable(
        _name='my_part3',
        members=Struct(
            my_part2=StubTraversable(
                _name='my_part2',
                members=Struct(
                    my_part=StubTraversable(
                        _name='my_part',
                    )
                )
            )
        )
    )
    foo = foo.bind(request=None)

    assert foo.iommi_path == ''

    assert foo._bound_members.my_part2.iommi_path == 'my_part2'
    assert foo._bound_members.my_part2.iommi_dunder_path == 'my_part2'

    assert foo._bound_members.my_part2._bound_members.my_part.iommi_path == 'my_part'
    assert foo._bound_members.my_part2._bound_members.my_part.iommi_dunder_path == 'my_part2__my_part'


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


def test_middleware_fallthrough_on_non_part():
    sentinel = object()
    assert request_with_middleware(response=sentinel, data={}) is sentinel


@override_settings(DEBUG=True)
def test_dispatch_auto_json():
    class MyPart(Part):
        def endpoint_handler(self, value, **_):
            return dict(a=1, b='asd', c=value)

    p = MyPart().bind(request=req('get', **{'/': '7'}))
    r = p.render_to_response()
    assert r['Content-type'] == 'application/json'
    assert json.loads(r.content) == dict(a=1, b='asd', c='7')


def test_dispatch_return_http_response():
    class MyPart(Part):
        def endpoint_handler(self, value, **_):
            return HttpResponse(f'foo {value}')

    p = MyPart()
    r = p.bind(request=req('get', **{'/': '7'})).render_to_response()
    assert r.content == b'foo 7'


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

    assert p.render_to_response().content == b'7'


def test_html_builder():
    assert html.h1('foo').bind(request=None).__html__() == '<h1>foo</h1>'


def test_fragment_basic():
    assert Fragment('foo').bind(request=None).__html__() == 'foo'


def test_fragment_with_tag():
    assert Fragment('foo', tag='h1').bind(request=None).__html__() == '<h1>foo</h1>'


def test_fragment_with_two_children():
    assert Fragment('foo', tag='h1', children__foo='asd').bind(request=None).__html__() == '<h1>fooasd</h1>'
