import json

import pytest
from django.db import models

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
)
from tri_declarative import Namespace
from tri_struct import Struct

from tests.helpers import (
    request_with_middleware,
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
            query__show=True,
            query__form__show=True,
        ),
        columns__bar=dict(
            query__show=True,
            query__form__show=True,
        ),
        default_child=True,
    )

    t2 = Table.from_model(
        model=T2,
        columns__foo=dict(
            query__show=True,
            query__form__show=True,
        ),
        columns__bar=dict(
            query__show=True,
            query__form__show=True,
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


def test_render_simple_tag():
    assert html.a('bar', attrs__href='foo').__html__() == '<a href="foo">bar</a>'


def test_render_empty_tag():
    assert html.br().__html__() == '<br >'


def test_fragment():
    foo = html.h1('asd')
    assert foo.__html__() == '<h1 >asd</h1>'
