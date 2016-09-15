from collections import OrderedDict

import pytest
from tri.struct import Struct
from tri.declarative import extract_subkeys, getattr_path, setattr_path, sort_after, LAST, collect_namespaces, assert_kwargs_empty, setdefaults_path, dispatch, EMPTY, Namespace, flatten


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
    assert 3 == getattr_path(foo, 'bar__baz__quux')

    setattr_path(foo, 'bar__baz__quux', 7)

    assert 7 == getattr_path(foo, 'bar__baz__quux')

    setattr_path(foo, 'bar__baz', None)
    assert None is getattr_path(foo, 'bar__baz__quux')

    setattr_path(foo, 'bar', None)
    assert None is foo.bar


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
    assert expected == actual


def test_setdefaults_namespace_merge():
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
    assert expected == actual


def test_namespace_repr():
    actual = repr(Namespace(a=1, b=2, c=Namespace(d=3, e=Namespace(f='4'))))
    expected = "Namespace(a=1, b=2, c__d=3, c__e__f='4')"  # Quotes since repr is called on values
    assert expected == actual


def test_namespace_str():
    actual = str(Namespace(a="1"))
    expected = "Namespace(a=1)"  # No quotes on string since str is used on values
    assert expected == actual


def test_namespace_repr_empty_members():
    actual = repr(Namespace(a=Namespace(b=Namespace())))
    expected = "Namespace(a__b=Namespace())"
    assert expected == actual


def test_namespace_get_set():
    n = Namespace(a=1, b__c=2)
    assert n.a == 1
    assert n.b.c == 2


def test_namespace_flatten():
    actual = flatten(Namespace(a=1, b=2, c=Namespace(d=3, e=Namespace(f=4))))
    expected = dict(a=1, b=2, c__d=3, c__e__f=4)
    assert actual == expected


def test_namespace_funcal():
    def f(**kwargs):
        assert {'a': 1, 'b__c': 2, 'b__d': 3} == kwargs

    f(**flatten(Namespace(a=1, b=Namespace(c=2, d=3))))


def test_namespace_flatten_loop_detection():
    n1 = Namespace()
    n1.foo = n1
    n1.bar = 'baz'
    n2 = Namespace()
    n2.buzz = n1
    assert {'buzz__bar': 'baz'} == flatten(n2)


def test_flatten_broken():
    assert dict(party1_labels__show=True, party2_labels__show=True) == flatten(Namespace(party1_labels=Namespace(show=True), party2_labels=Namespace(show=True)))


def test_flatten_identity_on_namespace_should_not_trigger_loop_detection():
    foo = Namespace(show=True)
    assert dict(party1_labels__show=True, party2_labels__show=True) == flatten(Namespace(party1_labels=foo, party2_labels=foo))


# def test_namespace_repr_loop_detection():
#     n1 = Namespace()
#     n1.foo = n1
#     n1.bar = 'baz'
#     n2 = Namespace()
#     n2.buzz = n1
#     assert "Namespace(buzz__bar='baz', buzz__foo=Namespace(...))" == repr(n2)


def test_setdefaults_path_empty_marker():
    actual = setdefaults_path(Struct(), foo=EMPTY, bar__boink=EMPTY)
    expected = dict(foo={}, bar=dict(boink={}))
    assert expected == actual


def test_setdefaults_path_empty_marker_no_side_effect():
    actual = setdefaults_path(Namespace(a__b=1, a__c=2),
                              a=Namespace(d=3),
                              a__e=4)
    expected = Namespace(a__b=1, a__c=2, a__d=3, a__e=4)
    assert expected == actual


def test_setdefaults_kwargs():
    actual = setdefaults_path({}, x__y=17)
    expected = dict(x=dict(y=17))
    assert expected == actual


def test_setdefaults_path_multiple_defaults():
    actual = setdefaults_path(Struct(),
                              Struct(a=17, b=42),
                              Struct(a=19, c=4711))
    expected = dict(a=17, b=42, c=4711)
    assert expected == actual


def test_setdefaults_path_ordering():
    expected = Struct(x=Struct(y=17, z=42))

    actual_foo = setdefaults_path(Struct(),
                                  OrderedDict([
                                      ('x', {'z': 42}),
                                      ('x__y', 17),
                                  ]))
    assert actual_foo == expected

    actual_bar = setdefaults_path(Struct(),
                                  OrderedDict([
                                      ('x__y', 17),
                                      ('x', {'z': 42}),
                                  ]))
    assert actual_bar == expected


def test_setdefatults_path_retain_empty():
    actual = setdefaults_path(Namespace(a=Namespace()), a__b=Namespace())
    expected = Namespace(a__b=Namespace())
    assert expected == actual

    actual = setdefaults_path(Namespace(), attrs__class=Namespace())
    expected = Namespace(attrs__class=Namespace())
    assert expected == actual


def test_namespace_retain_empty():
    assert Namespace(a=Namespace(b=Namespace())).a.b == Namespace()


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
    assert [y.expected_position for y in expected_order], 'check expected_order' == list(range(len(objects)))
    assert [x.expected_position for x in expected_order] == [x.expected_position for x in sort_after(objects)]


@pytest.mark.skipif(True, reason="Not yet implemented")
def test_sort_after_chaining():
    objects = [
        Struct(name='foo', after='bar'),
        Struct(name='bar', after=0),
    ]
    assert ['bar', 'foo'] == [x.name for x in sort_after(objects)]


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

    assert "assert_kwargs_empty() got unexpected keyword arguments 'bar', 'baz', 'foo'" in str(e.value)


def test_dispatch():
    @dispatch(bar__a='5', bar__quux__title='hi!')
    def foo(a, b, c, bar, baz):
        x = do_bar(**bar)
        y = do_baz(**baz)
        # do something with the inputs a, b, c...
        return a + b + c + x + y

    @dispatch(b='X', quux={}, )
    def do_bar(a, b, quux):
        return a + b + do_quux(**quux)

    def do_baz(a, b, c):
        # something...
        return a + b + c

    @dispatch
    def do_quux(title):
        # something...
        return title

    assert foo('1', '2', '3', bar__quux__title='7', baz__a='A', baz__b='B', baz__c='C') == '1235X7ABC'
