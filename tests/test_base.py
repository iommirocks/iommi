import json

import pytest
from django.db import models
from django.template import (
    Template,
    RequestContext,
)
from django.test import override_settings
from iommi._web_compat import (
    mark_safe,
    format_html,
)

from iommi.page import (
    html,
    Page,
)
from iommi.table import Table
from iommi.base import (
    find_target,
    InvalidEndpointPathException,
    evaluate_attrs,
    should_include,
    perform_post_dispatch,
    Part,
    no_copy_on_bind,
    as_html,
    evaluate_strict_container,
    build_long_path,
)
from tri_declarative import Namespace
from tri_struct import Struct

from tests.helpers import (
    request_with_middleware,
    req,
    StubTraversable,
)


# assert first in children, f'Found invalid path {k}. {first} not a member of {children.keys()}'


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


class MyPage(Page):
    t1 = Table(
        auto__model=T1,
        columns__foo=dict(
            query__include=True,
            query__form__include=True,
        ),
        columns__bar=dict(
            query__include=True,
            query__form__include=True,
        ),
    )

    t2 = Table(
        auto__model=T2,
        columns__foo=dict(
            query__include=True,
            query__form__include=True,
        ),
        columns__bar=dict(
            query__include=True,
            query__form__include=True,
        ),
    )


@pytest.mark.django_db
def test_dispatch_error_message_to_client():
    response = request_with_middleware(response=MyPage(), data={'/qwe': ''})
    data = json.loads(response.content)
    assert data == dict(error='Invalid endpoint path')


def test_find_target():
    # To build paths: declared_members: Struct, and optionally name
    # To find target: _long_path_by_path: Dict on root, children()

    bar = StubTraversable(name='bar')
    foo = StubTraversable(
        name='foo',
        children=Struct(
            bar=bar,
        ),
    )
    root = StubTraversable(
        name='root',
        children=Struct(
            foo=foo
        ),
    )
    root.bind(request=None)

    target = find_target(path='/foo/bar', root=root)
    assert target is bar
    assert build_long_path(target) == 'foo/bar'


def test_find_target_with_invalid_path():
    bar = StubTraversable(name='bar')
    foo = StubTraversable(
        name='foo',
        children=Struct(
            bar=bar,
        ),
    )
    root = StubTraversable(
        name='root',
        children=Struct(
            foo=foo
        ),
    )
    root.bind(request=None)

    with pytest.raises(InvalidEndpointPathException) as e:
        find_target(path='/foo/bar/baz', root=root)

    assert str(e.value) == "Given path /foo/bar/baz not found.\n" \
                           "  Short alternatives: '', 'foo', 'bar'\n" \
                           "  Long alternatives: '', 'foo', 'foo/bar'"


def test_evaluate_attrs():
    actual = evaluate_attrs(
        Struct(
            attrs=Namespace(
                class__table=True,
                class__foo=lambda foo: True,
                data=1,
                data2=lambda foo: foo,
            ),
        ),
        foo=3
    )

    expected = {
        'class': {
            'table': True,
            'foo': True,
        },
        'data': 1,
        'data2': 3,
    }

    assert actual == expected


@override_settings(IOMMI_DEBUG_SHOW_PATHS=True)
def test_evaluate_attrs_show_debug_paths():
    actual = evaluate_attrs(
        Struct(
            attrs=Namespace(
                class__table=True,
            ),
            name='foo',
            dunder_path=lambda: '<path here>',
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
    assert html.br().__html__() == '<br >'


def test_fragment():
    foo = html.h1('asd')
    assert foo.__html__() == '<h1 >asd</h1>'


def test_should_include_error_message():
    with pytest.raises(AssertionError) as e:
        should_include(Struct(include=lambda foo: foo))

    assert str(e.value).startswith('`include` was a callable. You probably forgot to evaluate it. The callable was: lambda found at')


def test_perform_post_dispatch_error_message():
    target = StubTraversable(name='root', children=Struct(foo=StubTraversable(name='foo')))
    target.bind(request=None)

    with pytest.raises(InvalidEndpointPathException) as e:
        perform_post_dispatch(root=target, path='/foo', value='')

    assert str(e.value) == "Target <tests.helpers.StubTraversable foo (bound) path:'foo'> has no registered post_handler"


def test_dunder_path_is_fully_qualified_and_skipping_root():
    foo = StubTraversable(
        name='my_part3',
        children=Struct(
            my_part2=StubTraversable(
                name='my_part2',
                children=Struct(
                    my_part=StubTraversable(
                        name='my_part',
                    )
                )
            )
        )
    )
    foo.bind(request=None)

    assert foo.path() == ''

    assert foo.children().my_part2.path() == 'my_part2'
    assert foo.children().my_part2.dunder_path() == 'my_part2'

    assert foo.children().my_part2.children().my_part.path() == 'my_part'
    assert foo.children().my_part2.children().my_part.dunder_path() == 'my_part2__my_part'


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
