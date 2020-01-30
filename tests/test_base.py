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
    group_paths_by_children,
    GroupPathsByChildrenError,
    find_target,
    InvalidEndpointPathException,
    evaluate_attrs,
    should_include,
    perform_post_dispatch,
    PagePart,
    no_copy_on_bind,
    as_html,
    evaluate_strict_container,
)
from tri_declarative import Namespace
from tri_struct import Struct

from tests.helpers import (
    request_with_middleware,
    req,
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
    t1 = Table.from_model(
        model=T1,
        columns__foo=dict(
            query__include=True,
            query__form__include=True,
        ),
        columns__bar=dict(
            query__include=True,
            query__form__include=True,
        ),
        default_child=True,
    )

    t2 = Table.from_model(
        model=T2,
        columns__foo=dict(
            query__include=True,
            query__form__include=True,
        ),
        columns__bar=dict(
            query__include=True,
            query__form__include=True,
        ),
    )
    assert not t2.default_child


def test_group_paths_by_children_happy_path():
    my_page = MyPage()
    my_page.bind(request=None)

    data = {
        't1/query/form/foo': '1',
        't2/query/form/foo': '2',
        'bar': '3',
        't2/bar': '4',
    }

    assert group_paths_by_children(children=my_page.children(), data=data) == {
        't1': {
            'query/form/foo': '1',
            'bar': '3',
        },
        't2': {
            'query/form/foo': '2',
            'bar': '4',
        },
    }

    assert group_paths_by_children(
        children=my_page.children().t1.children(),
        data={
            'query/form/foo': '1',
            'bar': '3',
        },
    ) == {
        'query': {
            'form/foo': '1',
            'bar': '3',
        }
    }

    assert group_paths_by_children(
        children=my_page.children().t1.children().query.children(),
        data={
            'form/foo': '1',
            'bar': '3',
        },
    ) == {
        'form': {
            'foo': '1',
            'bar': '3',
        }
    }


def test_group_paths_by_children_error_message():
    class NoDefaultChildPage(Page):
        foo = html.h1('asd', default_child=False)

        class Meta:
            default_child = False

    my_page = NoDefaultChildPage()
    my_page.bind(request=None)

    data = {
        'unknown': '5',
    }

    with pytest.raises(GroupPathsByChildrenError):
        group_paths_by_children(children=my_page.children(), data=data)


@pytest.mark.django_db
def test_dispatch_error_message_to_client():
    response = request_with_middleware(response=MyPage(), data={'/qwe': ''})
    data = json.loads(response.content)
    assert data == dict(error='Invalid endpoint path')


def test_find_target():
    bar = 'bar'
    foo = Struct(
        children=lambda: Struct(
            bar=bar,
        ),
    )
    root = Struct(
        children=lambda: Struct(
            foo=foo
        ),
    )

    target, parents = find_target(path='/foo/bar', root=root)
    assert target is bar
    assert parents == [root, foo]


def test_find_target_with_default_child_present():
    baz = 'baz'
    bar = Struct(
        children=lambda: Struct(
            baz=baz,
        ),
        default_child=True,
    )
    foo = Struct(
        children=lambda: Struct(
            bar=bar,
        ),
        default_child=True,
    )
    root = Struct(
        children=lambda: Struct(
            foo=foo
        ),
    )

    # First check the canonical path
    target, parents = find_target(path='/foo/bar/baz', root=root)
    assert target is baz
    assert parents == [root, foo, bar]

    # Then we check the short path using the default_child property
    target, parents = find_target(path='/baz', root=root)
    assert target is baz
    assert parents == [root, foo, bar]


def test_find_target_with_invalid_path():
    bar = 'bar'

    class Foo:
        def children(self):
            return Struct(bar=bar)

        def __repr__(self):
            return 'Foo'

    class Root:
        def children(self):
            return Struct(foo=Foo())

        def __repr__(self):
            return 'Root'

    with pytest.raises(InvalidEndpointPathException) as e:
        find_target(path='/foo/bar/baz', root=Root())

    assert str(e.value) == """Invalid path /foo/bar/baz.
bar (of type <class 'str'> has no attribute children so can't be traversed.
Parents so far: [Root, Foo, 'bar'].
Path left: baz"""


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
    @no_copy_on_bind
    class MyPart(PagePart):
        def children(self):
            return Struct(
                foo=Struct(
                    post_handler=None,
                    default_child=False,
                )
            )

        def __html__(self):
            return 'MyPart'

    target = MyPart()
    target.bind(request=None)

    with pytest.raises(InvalidEndpointPathException) as e:
        perform_post_dispatch(root=target, path='/foo', value='')

    assert str(e.value) == f'''Target Struct(default_child=False, post_handler=None) has no registered post_handler.
    Path: "/foo"
    Parents:
        MyPart'''


def test_dunder_path_is_different_from_path_and_fully_qualified_skipping_root():
    @no_copy_on_bind
    class MyPart(PagePart):
        def __init__(self):
            super(MyPart, self).__init__()
            self.name = 'my_part'

        def __html__(self):
            return 'MyPart'

    @no_copy_on_bind
    class MyPart2(PagePart):
        def __init__(self):
            super(MyPart2, self).__init__()
            self.name = 'my_part2'
            self.my_part = MyPart()

        def on_bind(self):
            self.my_part.bind(parent=self)

        def children(self):
            return Struct(
                my_part=self.my_part
            )

        def __html__(self):
            return 'MyPart'

    @no_copy_on_bind
    class MyPart3(PagePart):
        def __init__(self):
            super(MyPart3, self).__init__()
            self.name = 'my_part3'
            self.my_part2 = MyPart2()

        def on_bind(self):
            self.my_part2.bind(parent=self)

        def children(self):
            return Struct(
                my_part2=self.my_part2
            )

        def __html__(self):
            return 'MyPart'

    foo = MyPart3()
    foo.bind(request=None)

    assert foo.children().my_part2.path() == ''
    assert foo.children().my_part2.dunder_path() == 'my_part2'

    assert foo.children().my_part2.children().my_part.path() == ''
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
