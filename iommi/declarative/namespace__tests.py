import pytest
from iommi.struct import Struct

from iommi.declarative.namespace import (
    EMPTY,
    flatten,
    getattr_path,
    Namespace,
    setattr_path,
    setdefaults_path,
)


def test_getattr_path_and_setattr_path():
    class Baz:
        def __init__(self):
            self.quux = 3

    class Bar:
        def __init__(self):
            self.baz = Baz()

    class Foo:
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


def test_getattr_empty_path():
    obj = object()
    assert getattr_path(obj, '') is obj


def test_getattr_missing_attribute():
    obj = object()

    with pytest.raises(AttributeError) as e:
        getattr_path(obj, 'foo')
    assert str(e.value) == "'object' object has no attribute path 'foo', since 'object' object has no attribute 'foo'"

    with pytest.raises(AttributeError) as e:
        getattr_path(Struct(foo=object()), 'foo__bar')
    assert (
        str(e.value) == "'Struct' object has no attribute path 'foo__bar', since 'object' object has no attribute 'bar'"
    )


def test_getattr_default():
    assert getattr_path(object(), 'foo', 17) == 17
    assert getattr_path(Struct(foo=object()), 'foo__bar', 42) == 42

    assert getattr_path(object(), 'foo', default=17) == 17
    assert getattr_path(Struct(foo=object()), 'foo__bar', default=42) == 42


def test_setdefaults_path_1():
    assert setdefaults_path(dict(), x=17) == dict(x=17)


def test_setdefaults_path_2():
    assert setdefaults_path(dict(x=dict()), x__y=17) == dict(x=dict(y=17))


def test_setdefaults_path_3():
    assert setdefaults_path(dict(), x__y=17) == dict(x=dict(y=17))


def test_setdefaults_path():
    actual = setdefaults_path(
        dict(
            x=1,
            y=dict(z=2),
        ),
        dict(
            a=3,
            x=4,
            y__b=5,
            y__z=6,
        ),
    )
    expected = dict(
        x=1,
        a=3,
        y=dict(
            z=2,
            b=5,
        ),
    )
    assert actual == expected


def test_setdefaults_namespace_merge():
    actual = setdefaults_path(
        dict(x=1, y=Struct(z=Struct(foo=True))),
        dict(
            y__a__b=17,
            y__z__c=True,
        ),
    )
    expected = dict(
        x=1,
        y=Struct(
            a=Struct(b=17),
            z=Struct(
                foo=True,
                c=True,
            ),
        ),
    )
    assert actual == expected


def test_setdefaults_callable_forward():
    actual = setdefaults_path(
        Namespace(
            foo=lambda x: x,
            foo__x=17,
        )
    )
    assert actual.foo() == 17


def test_setdefaults_callable_backward():
    actual = setdefaults_path(
        Namespace(foo__x=17),
        foo=lambda x: x,
    )
    assert actual.foo() == 17


def test_setdefaults_callable_backward_not_namespace():
    actual = setdefaults_path(
        Namespace(foo__x=17),
        foo=EMPTY,
    )
    expected = Namespace(foo__x=17)
    assert actual == expected


def test_namespace_repr():
    actual = repr(Namespace(a=4, b=3, c=Namespace(d=2, e=Namespace(f='1'))))
    expected = "Namespace(a=4, b=3, c__d=2, c__e__f='1')"  # Quotes on '1' since `repr` is called on values
    assert actual == expected


def test_namespace_str():
    actual = str(Namespace(a=4, b=3, c=Namespace(d=2, e=Namespace(f='1'))))
    expected = "Namespace(a=4, b=3, c__d=2, c__e__f=1)"  # No quotes on '1' since `str` is used on values
    assert actual == expected


def test_namespace_repr_empty_members():
    actual = repr(Namespace(a=Namespace(b=Namespace())))
    expected = "Namespace(a__b=Namespace())"
    assert actual == expected


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


def test_namespace_as_callable_with_call_target_present():
    subject = Namespace(x=17, call_target=lambda **kwargs: kwargs)
    assert subject() == dict(x=17)


def test_namespace_as_callable_with_call_target_missing():
    subject = Namespace(x=17)
    with pytest.raises(TypeError) as e:
        subject()

    expected_error_msg = (
        "Namespace was used as a function, but no call_target was specified. The namespace is: Namespace(x=17)"
    )
    assert expected_error_msg in str(e.value)


def test_namespace_flatten_loop_detection():
    n1 = Namespace()
    n1.foo = n1
    n1.bar = 'baz'
    n2 = Namespace()
    n2.buzz = n1
    assert flatten(n2) == {'buzz__bar': 'baz'}


def test_flatten_broken():
    assert flatten(Namespace(party1_labels=Namespace(show=True), party2_labels=Namespace(show=True),)) == dict(
        party1_labels__show=True,
        party2_labels__show=True,
    )


def test_flatten_identity_on_namespace_should_not_trigger_loop_detection():
    foo = Namespace(show=True)
    assert flatten(Namespace(party1_labels=foo, party2_labels=foo,)) == dict(
        party1_labels__show=True,
        party2_labels__show=True,
    )


# def test_namespace_repr_loop_detection():
#     n1 = Namespace()
#     n1.foo = n1
#     n1.bar = 'baz'
#     n2 = Namespace()
#     n2.buzz = n1
#     assert repr(n2) == "Namespace(buzz__bar='baz', buzz__foo=Namespace(...))"


def test_namespace_empty_initializer():
    assert Namespace() == dict()


def test_namespace_setitem_single_value():
    ns = Namespace()
    ns.setitem_path('x', 17)
    assert ns == dict(x=17)


def test_namespace_setitem_singe_value_overwrite():
    ns = Namespace(x=17)
    ns.setitem_path('x', 42)
    assert ns == dict(x=42)


def test_namespace_setitem_split_path():
    ns = Namespace()
    ns.setitem_path('x__y', 17)
    assert ns == dict(x=dict(y=17))


def test_namespace_setitem_split_path_overwrite():
    ns = Namespace(x__y=17)
    ns.setitem_path('x__y', 42)
    assert ns == dict(x=dict(y=42))


def test_namespace_setitem_namespace_merge():
    ns = Namespace(x__y=17)
    ns.setitem_path('x__z', 42)
    assert ns == dict(x=dict(y=17, z=42))


def test_namespace_setitem_function():
    def f():
        pass

    ns = Namespace(f=f)
    assert ns == dict(f=f)
    ns.setitem_path('f__x', 17)
    assert ns == dict(f=dict(call_target=f, x=17))


def test_namespace_setitem_function_backward():
    def f():
        pass

    ns = Namespace(f__x=17)
    assert ns == dict(f=dict(x=17))
    ns.setitem_path('f', f)
    assert ns == dict(f=dict(call_target=f, x=17))


def test_namespace_setitem_function_dict():
    def f():
        pass

    ns = Namespace(f=f)
    assert ns == dict(f=f)
    ns.setitem_path('f', dict(x=17))
    assert ns == dict(f=dict(call_target=f, x=17))


def test_namespace_setitem_function_non_dict():
    def f():
        pass

    ns = Namespace(f=f)
    assert ns == dict(f=f)
    ns.setitem_path('f', 17)
    assert ns == dict(f=17)


def test_namespace_no_promote_overwrite():
    ns = Namespace(x=17)
    ns.setitem_path('x__z', 42)
    assert ns == Namespace(x__z=42)


def test_namespace_no_promote_overwrite_backwards():
    ns = Namespace(x__z=42)
    ns.setitem_path('x', 17)
    assert ns == Namespace(x=17)


@pytest.mark.parametrize('backward', [False, True], ids={False: '==>', True: '<=='}.get)
@pytest.mark.parametrize(
    'a, b, expected',
    [
        (Namespace(), Namespace(), Namespace()),
        (Namespace(a=1), Namespace(b=2), Namespace(a=1, b=2)),
        (Namespace(a__b=1), Namespace(a__c=2), Namespace(a__b=1, a__c=2)),
        (Namespace(x=sum), Namespace(x__y=1), Namespace(x__call_target=sum, x__y=1)),
        (Namespace(x=dict(y=1)), Namespace(x__z=2), Namespace(x__y=1, x__z=2)),
        (Namespace(x=Namespace(y__z=1)), Namespace(a=Namespace(b__c=2)), Namespace(x__y__z=1, a__b__c=2)),
        (Namespace(bar__a=1), Namespace(bar__quux__title=2), Namespace(bar__a=1, bar__quux__title=2)),
        (Namespace(bar__a=1), Namespace(bar__quux__title="hi"), Namespace(bar__a=1, bar__quux__title="hi")),
        (Namespace(bar__='foo'), Namespace(bar__fisk="hi"), Namespace(bar__='foo', bar__fisk='hi')),
    ],
    ids=str,
)
def test_merge(a, b, expected, backward):
    if backward:
        a, b = b, a
    assert Namespace(flatten(a), flatten(b)) == expected


def test_backward_compatible_empty_key():
    assert Namespace(foo=Namespace({'': 'hej'})) == Namespace(foo__='hej')


def test_setdefaults_path_empty_marker():
    assert setdefaults_path(Struct(), foo=EMPTY, bar__boink=EMPTY) == dict(foo={}, bar=dict(boink={}))


def test_setdefaults_path_empty_marker_copy():
    actual = setdefaults_path(Struct(), x=EMPTY)
    expected = dict(x={})
    assert actual == expected
    assert actual.x is not EMPTY


def test_setdefaults_path_empty_marker_no_side_effect():
    assert setdefaults_path(Namespace(a__b=1, a__c=2), a=Namespace(d=3), a__e=4) == Namespace(
        a__b=1,
        a__c=2,
        a__d=3,
        a__e=4,
    )


def test_setdefaults_kwargs():
    assert setdefaults_path({}, x__y=17) == dict(x=dict(y=17))


def test_setdefaults_path_multiple_defaults():
    assert setdefaults_path(
        Struct(),
        Struct(a=17, b=42),
        Struct(a=19, c=4711),
    ) == dict(a=17, b=42, c=4711)


def test_setdefaults_path_ordering():
    expected = Struct(x=Struct(y=17, z=42))

    actual_foo = setdefaults_path(
        Struct(),
        dict(
            x={'z': 42},
            x__y=17,
        ),
    )

    assert actual_foo == expected

    actual_bar = setdefaults_path(
        Struct(),
        dict(
            x__y=17,
            x={'z': 42},
        ),
    )
    assert actual_bar == expected


def test_setdefatults_path_retain_empty():
    assert setdefaults_path(Namespace(a=Namespace()), a__b=Namespace()) == Namespace(
        a__b=Namespace(),
    )

    assert setdefaults_path(Namespace(), attrs__class=Namespace()) == Namespace(
        attrs__class=Namespace(),
    )


def test_namespace_retain_empty():
    assert Namespace(a=Namespace(b=Namespace())).a.b == Namespace()


def test_namespace_call():
    def bar(arg):
        return arg

    f = Namespace(call_target=bar, arg='arg')
    assert f() == 'arg'


def test_namespace_class_call():
    class Foo:
        @staticmethod
        def bar(arg):
            return arg

    f = Namespace(call_target__cls=Foo, call_target__attribute='bar', arg='arg')
    assert f() == 'arg'


def test_namespace_class_call_override_default():
    class Foo:
        @staticmethod
        def bar(arg):
            return arg

    f = Namespace(
        call_target__call_target=lambda arg: "not arg",
        call_target__cls=Foo,
        call_target__attribute='bar',
        arg='arg',
    )
    assert f() == 'not arg'


def test_namespace_call_attribute_missing():
    class Foo:
        def __init__(self, arg):
            self.arg = arg

    f = Namespace(
        call_target__cls=Foo,
        arg='arg',
    )
    assert f().arg == 'arg'


# noinspection PyPep8Naming
def test_namespace_call_attribute_None():
    class Foo:
        def __init__(self, arg):
            self.arg = arg

    f = Namespace(
        call_target__cls=Foo,
        call_target__attribute=None,
        arg='arg',
    )
    assert f().arg == 'arg'


def test_no_call_target_overwrite():
    def f():
        pass

    def b():
        pass

    x = setdefaults_path(
        dict(foo={}),
        foo=f,
    )
    assert x == dict(foo=dict(call_target=f))

    y = setdefaults_path(
        x,
        foo=b,
    )
    assert dict(foo=dict(call_target=f)) == y


def test_empty_marker_is_immutable():
    assert isinstance(EMPTY, Namespace)
    with pytest.raises(TypeError):
        EMPTY['foo'] = 'bar'


def test_none_semantics():
    assert Namespace(Namespace(foo=None), foo__bar='baz') == Namespace(foo__bar='baz')


def test_none_overwrite_semantics():
    assert Namespace(Namespace(foo__bar='baz'), foo=None) == Namespace(foo=None)
