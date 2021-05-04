import pytest
from tri_declarative import LAST
from tri_struct import Struct

from iommi.base import (
    keys,
    values,
)
from iommi.sort_after import sort_after


def test_order_after_0():
    sorts_right(
        dict(
            foo=Struct(expected_position=1),
            bar=Struct(expected_position=2),
            quux=Struct(after=0, expected_position=0),
            baz=Struct(expected_position=3),
        )
    )


def test_order_after_LAST():
    sorts_right(
        dict(
            foo=Struct(expected_position=0),
            bar=Struct(expected_position=1),
            quux=Struct(after=LAST, expected_position=3),
            baz=Struct(expected_position=2),
        )
    )


def test_order_after_large():
    sorts_right(
        dict(
            foo=Struct(expected_position=2, after=42),
            bar=Struct(expected_position=0, ),
            quux=Struct(expected_position=3, after=42),
            baz=Struct(expected_position=1, after=17),
        )
    )


def test_order_after_name():
    sorts_right(
        dict(
            foo=Struct(expected_position=0),
            bar=Struct(expected_position=2),
            quux=Struct(after='foo', expected_position=1),
            baz=Struct(expected_position=3),
        )
    )


def test_order_after_name_stable():
    sorts_right(
        dict(
            foo=Struct(expected_position=0),
            bar=Struct(expected_position=3),
            quux=Struct(after='foo', expected_position=1),
            qoox=Struct(after='foo', expected_position=2),
            baz=Struct(expected_position=4),
        )
    )


def test_order_after_name_interleave():
    sorts_right(
        dict(
            foo=Struct(expected_position=0),
            bar=Struct(expected_position=3),
            qoox=Struct(after=1, expected_position=2),
            quux=Struct(after='foo', expected_position=1),
        )
    )


def test_order_after_name_last():
    sorts_right(
        dict(
            foo=Struct(expected_position=0),
            quux=Struct(after='qoox', expected_position=3),
            qoox=Struct(after=LAST, expected_position=2),
            bar=Struct(expected_position=1),
        )
    )


def test_order_after_complete():
    sorts_right(
        {
            # header1
            'quux': Struct(expected_position=2),
            'foo': Struct(expected_position=3),
            # header2
            'bar': Struct(expected_position=6),
            'asd': Struct(expected_position=7),
            'header1': Struct(after=0, expected_position=0),
            'header1b': Struct(after=0, expected_position=1),
            'header2': Struct(after='foo', expected_position=4),
            # header3
            'header2.b': Struct(after='foo', expected_position=5),
            'header3': Struct(after='quux2', expected_position=9),
            'quux2': Struct(expected_position=8),
            'quux3': Struct(expected_position=10),
            'quux4': Struct(expected_position=11),
            'quux5': Struct(after=LAST, expected_position=12),
            'quux6': Struct(after=LAST, expected_position=13),
        }
    )


def test_sort_after_chaining():
    sorts_right(
        dict(
            foo=Struct(after='bar', expected_position=1),
            bar=Struct(after=0, expected_position=0),
        )
    )


def test_sort_after_name_chaining():
    sorts_right(
        dict(
            baz=Struct(after='foo', expected_position=2),
            foo=Struct(after='bar', expected_position=1),
            bar=Struct(after=0, expected_position=0),
        )
    )


def test_sort_after_indexes():
    sorts_right(
        dict(
            baz=Struct(after=1, expected_position=2),
            foo=Struct(after=0, expected_position=1),
            bar=Struct(after=-1, expected_position=0),
        )
    )


def sorts_right(objects):
    assert {y.expected_position for y in values(objects)} == set(range(len(objects))), "Borken test"
    sort_after(objects)
    assert [x.expected_position for x in values(objects)] == list(range(len(objects))), keys(objects)


def test_sort_after_points_to_nothing():
    with pytest.raises(KeyError) as e:
        sort_after(
            dict(
                quux=Struct(),
                foo=Struct(),
                quux6=Struct(after='does-not-exist'),
            )
        )

    assert (
        e.value.args[0]
        == """\
Tried to order after does-not-exist but that key does not exist.
Available names:
    foo
    quux
    quux6"""
    )


def test_sort_after_points_to_nothing_plural():
    with pytest.raises(KeyError) as e:
        sort_after(
            dict(
                quux=Struct(),
                foo=Struct(after='does-not-exist2'),
                quux6=Struct(after='does-not-exist'),
            )
        )

    assert (
        e.value.args[0]
        == """\
Tried to order after does-not-exist, does-not-exist2 but those keys do not exist.
Available names:
    foo
    quux
    quux6"""
    )
