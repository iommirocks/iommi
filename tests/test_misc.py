import pytest
from tri.struct import Struct
from tri.declarative import extract_subkeys, getattr_path, setattr_path, sort_after, LAST, collect_namespaces, assert_kwargs_empty, setdefaults_path


def test_extract_subkeys():
    foo = {
        'foo__foo': 1,
        'foo__bar': 2,
        'baz': 3,
    }
    assert extract_subkeys(foo, 'foo', defaults={'quux': 4}) == {
        'foo': 1,
        'bar': 2,
        'quux': 4,
    }

    assert extract_subkeys(foo, 'foo') == {
        'foo': 1,
        'bar': 2,
    }


def test_collect_namespaces():
    values = dict(
        foo__foo=1,
        foo__bar=2,
        bar__foo=3,
        bar__bar=4,
        foo_baz=5,
        baz=6
    )

    assert dict(foo=dict(foo=1, bar=2), bar=dict(foo=3, bar=4), foo_baz=5, baz=6) == collect_namespaces(values)


def test_collect_namespaces_merge_existing():
    values = dict(
        foo=dict(bar=1),
        foo__baz=2
    )

    assert dict(foo=dict(bar=1, baz=2)) == collect_namespaces(values)


def test_collect_namespaces_non_dict_existing_value():
    values = dict(
        foo='bar',
        foo__baz=False
    )
    assert dict(foo=dict(bar=True, baz=False)) == collect_namespaces(values)


def test_getattr_path_and_setattr_path():
    class Baz(object):
        def __init__(self):
            self.quux = 3

    class Bar(object):
        def __init__(self):
            self.baz = Baz()

    class Foo(object):
        def __init__(self):
            self.bar = Bar()

    foo = Foo()
    assert getattr_path(foo, 'bar__baz__quux') == 3

    setattr_path(foo, 'bar__baz__quux', 7)

    assert getattr_path(foo, 'bar__baz__quux') == 7

    setattr_path(foo, 'bar__baz', None)
    assert getattr_path(foo, 'bar__baz__quux') is None

    setattr_path(foo, 'bar', None)
    assert foo.bar is None


def test_setdefaults_path():
    actual = setdefaults_path(dict(
            x=1,
            y=dict(z=2)
    ), dict(
            a=3,
            x=4,
            y__b=5,
            y__z=6
    ))
    expected = dict(
            x=1,
            a=3,
            y=dict(z=2, b=5)
    )
    assert actual == expected


def test_setdefaults_path():
    actual = setdefaults_path(dict(
        x=1,
        y=Struct(z="foo")
    ), dict(
        y__a__b=17,
        y__z__c=True
    ))
    expected = dict(
        x=1,
        y=Struct(a=Struct(b=17),
                 z=Struct(foo=True,
                          c=True))
    )
    assert actual == expected


def test_order_after():
    objects = [
        # header1
        Struct(name='quux', expected_position=2),
        Struct(name='foo', expected_position=3),
        # header2
        Struct(name='bar', expected_position=6),
        Struct(name='asd', expected_position=7),
        Struct(name='header1', after=0, expected_position=0),
        Struct(name='header1b', after=0, expected_position=1),
        Struct(name='header2', after='foo', expected_position=4),
        Struct(name='header2.b', after='foo', expected_position=5),
        Struct(name='header3', after='quux2', expected_position=9),
        Struct(name='quux2', expected_position=8),
        # header3
        Struct(name='quux3', expected_position=10),
        Struct(name='quux4', expected_position=11),
        Struct(name='quux5', after=LAST, expected_position=12),
        Struct(name='quux6', after=LAST, expected_position=13),
    ]

    expected_order = sorted(objects, key=lambda x: x.expected_position)
    assert list(range(len(objects))) == [y.expected_position for y in expected_order], 'check expected_order'
    assert [x.expected_position for x in expected_order] == [x.expected_position for x in sort_after(objects)]


def test_sort_after_points_to_nothing():
    objects = [
        Struct(name='quux'),
        Struct(name='foo'),
        Struct(name='quux6', after='does-not-exist'),
    ]

    with pytest.raises(KeyError) as e:
        sort_after(objects)

    assert 'Tried to order after does-not-exist but that key does not exist' in str(e)


def test_assert_kwargs_empty():
    assert_kwargs_empty({})

    with pytest.raises(TypeError) as e:
        assert_kwargs_empty(dict(foo=1, bar=2, baz=3))

    assert str(e.value) == "test_assert_kwargs_empty() got unexpected keyword arguments 'bar', 'baz', 'foo'"
