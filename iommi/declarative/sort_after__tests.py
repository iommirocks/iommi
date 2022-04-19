import pytest
from tri_struct import Struct

from tri_declarative import (
    LAST,
    sort_after,
)


def test_order_after_0():
    sorts_right([
        Struct(name='foo', expected_position=1),
        Struct(name='bar', expected_position=2),
        Struct(name='quux', after=0, expected_position=0),
        Struct(name='baz', expected_position=3),
    ])


# noinspection PyPep8Naming
def test_order_after_LAST():
    sorts_right([
        Struct(name='foo', expected_position=0),
        Struct(name='bar', expected_position=1),
        Struct(name='quux', after=LAST, expected_position=3),
        Struct(name='baz', expected_position=2),
    ])


def test_order_after_name():
    sorts_right([
        Struct(name='foo', expected_position=0),
        Struct(name='bar', expected_position=2),
        Struct(name='quux', after='foo', expected_position=1),
        Struct(name='baz', expected_position=3),
    ])


def test_order_after_name_stable():
    sorts_right([
        Struct(name='foo', expected_position=0),
        Struct(name='bar', expected_position=3),
        Struct(name='quux', after='foo', expected_position=1),
        Struct(name='qoox', after='foo', expected_position=2),
        Struct(name='baz', expected_position=4),
    ])


def test_order_after_name_interleave():
    sorts_right([
        Struct(name='foo', expected_position=0),
        Struct(name='bar', expected_position=3),
        Struct(name='qoox', after=1, expected_position=2),
        Struct(name='quux', after='foo', expected_position=1),
    ])


def test_order_after_name_last():
    sorts_right([
        Struct(name='foo', expected_position=0),
        Struct(name='quux', after='qoox', expected_position=3),
        Struct(name='qoox', after=LAST, expected_position=2),
        Struct(name='bar', expected_position=1),
    ])


def test_order_after_complete():
    sorts_right([
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
    ])


def test_sort_after_chaining():
    sorts_right([
        Struct(name='foo', after='bar', expected_position=1),
        Struct(name='bar', after=0, expected_position=0),
    ])


def test_sort_after_name_chaining():
    sorts_right([
        Struct(name='baz', after='foo', expected_position=2),
        Struct(name='foo', after='bar', expected_position=1),
        Struct(name='bar', after=0, expected_position=0),
    ])


def test_sort_after_indexes():
    sorts_right([
        Struct(name='baz', after=1, expected_position=2),
        Struct(name='foo', after=0, expected_position=1),
        Struct(name='bar', after=-1, expected_position=0),
    ])


def sorts_right(objects):
    expected_order = sorted(objects, key=lambda x: x.expected_position)
    assert [y.expected_position for y in expected_order] == list(range(len(objects))), "Borken test"
    sorted_objects = sort_after(objects)
    assert list(range(len(objects))) == [x.expected_position for x in sorted_objects], [x.name for x in objects]


def test_sort_after_points_to_nothing():
    with pytest.raises(KeyError) as e:
        sort_after([
            Struct(name='quux'),
            Struct(name='foo'),
            Struct(name='quux6', after='does-not-exist'),
        ])

    assert e.value.args[0] == "Tried to order after does-not-exist but that key does not exist.\nAvailable names:\n    foo\n   quux\n   quux6"


def test_sort_after_points_to_nothing_plural():
    with pytest.raises(KeyError) as e:
        sort_after([
            Struct(name='quux'),
            Struct(name='foo', after='does-not-exist2'),
            Struct(name='quux6', after='does-not-exist'),
        ])

    assert e.value.args[0] == "Tried to order after does-not-exist, does-not-exist2 but those keys do not exist.\nAvailable names:\n    foo\n   quux\n   quux6"
