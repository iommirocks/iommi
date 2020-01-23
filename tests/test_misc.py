import copy

import pytest
from tri_declarative import (
    assert_kwargs_empty,
    class_shortcut,
    dispatch,
    EMPTY,
    flatten,
    full_function_name,
    get_members,
    get_shortcuts_by_name,
    get_signature,
    getattr_path,
    is_shortcut,
    LAST,
    Namespace,
    Refinable,
    refinable,
    RefinableObject,
    setattr_path,
    setdefaults_path,
    Shortcut,
    shortcut,
    sort_after,
    with_meta,
)
from tri_struct import Struct


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


def test_setdefaults_path_1():
    assert setdefaults_path(dict(), x=17) == dict(x=17)


def test_setdefaults_path_2():
    assert setdefaults_path(dict(x=dict()), x__y=17) == dict(x=dict(y=17))


def test_setdefaults_path_3():
    assert setdefaults_path(dict(), x__y=17) == dict(x=dict(y=17))


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


def test_setdefaults_namespace_merge():
    actual = setdefaults_path(dict(
        x=1,
        y=Struct(z=Struct(foo=True))
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


def test_setdefaults_callable_forward():
    actual = setdefaults_path(Namespace(
        foo=lambda x: x,
        foo__x=17,
    ))
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
    expected = "Namespace(a=4, b=3, c__d=2, c__e__f='1')"  # Quotes since repr is called on values
    assert actual == expected


def test_namespace_str():
    actual = str(Namespace(a=4, b=3, c=Namespace(d=2, e=Namespace(f='1'))))
    expected = "Namespace(a=4, b=3, c__d=2, c__e__f=1)"  # No quotes on '1' since str is used on values
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


def test_namespace_call_target():
    subject = Namespace(x=17, call_target=lambda **kwargs: kwargs)
    assert subject() == dict(x=17)


def test_namespace_missing_call_target():
    subject = Namespace(x=17)
    with pytest.raises(TypeError) as e:
        subject()
    assert "TypeError: Namespace was used as a function, but no call_target was specified. " \
           "The namespace is: Namespace(x=17)" in str(e)


def test_namespace_flatten_loop_detection():
    n1 = Namespace()
    n1.foo = n1
    n1.bar = 'baz'
    n2 = Namespace()
    n2.buzz = n1
    assert flatten(n2) == {'buzz__bar': 'baz'}


def test_flatten_broken():
    assert flatten(Namespace(
        party1_labels=Namespace(show=True),
        party2_labels=Namespace(show=True),
    )) == dict(
        party1_labels__show=True,
        party2_labels__show=True,
    )


def test_flatten_identity_on_namespace_should_not_trigger_loop_detection():
    foo = Namespace(show=True)
    assert flatten(Namespace(
        party1_labels=foo,
        party2_labels=foo,
    )) == dict(
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
    x = Namespace()
    x.setitem_path('x', 17)
    assert x == dict(x=17)


def test_namespace_setitem_singe_value_overwrite():
    x = Namespace(x=17)
    x.setitem_path('x', 42)
    assert x == dict(x=42)


def test_namespace_setitem_split_path():
    x = Namespace()
    x.setitem_path('x__y', 17)
    assert x == dict(x=dict(y=17))


def test_namespace_setitem_split_path_overwrite():
    x = Namespace(x__y=17)
    x.setitem_path('x__y', 42)
    assert x == dict(x=dict(y=42))


def test_namespace_setitem_namespace_merge():
    x = Namespace(x__y=17)
    x.setitem_path('x__z', 42)
    assert x == dict(x=dict(y=17, z=42))


def f():
    pass


def test_namespace_setitem_function():
    x = Namespace(f=f)
    x.setitem_path('f__x', 17)
    assert x == dict(f=dict(call_target=f, x=17))


def test_namespace_setitem_function_backward():
    x = Namespace(f__x=17)
    x.setitem_path('f', f)
    assert x == dict(f=dict(call_target=f, x=17))


def test_namespace_setitem_function_dict():
    x = Namespace(f=f)
    x.setitem_path('f', dict(x=17))
    assert x == dict(f=dict(call_target=f, x=17))


def test_namespace_setitem_function_non_dict():
    x = Namespace(f=f)
    x.setitem_path('f', 17)
    assert x == dict(f=17)


def test_namespace_no_promote_overwrite():
    x = Namespace(x=17)
    x.setitem_path('x__z', 42)
    assert x == Namespace(x__z=42)


def test_namespace_no_promote_overwrite_backwards():
    x = Namespace(x__z=42)
    x.setitem_path('x', 17)
    assert x == Namespace(x=17)


def test_dispatch():
    @dispatch(foo=EMPTY)
    def f(**kwargs):
        return kwargs

    assert f() == dict(foo={})


@pytest.mark.parametrize('backward', [False, True], ids={False: '==>', True: '<=='}.get)
@pytest.mark.parametrize('a, b, expected', [
    (Namespace(), Namespace(), Namespace()),
    (Namespace(a=1), Namespace(b=2), Namespace(a=1, b=2)),
    (Namespace(a__b=1), Namespace(a__c=2), Namespace(a__b=1, a__c=2)),
    (Namespace(x=f), Namespace(x__y=1), Namespace(x__call_target=f, x__y=1)),
    (Namespace(x=dict(y=1)), Namespace(x__z=2), Namespace(x__y=1, x__z=2)),
    (Namespace(x=Namespace(y__z=1)), Namespace(a=Namespace(b__c=2)), Namespace(x__y__z=1, a__b__c=2)),
    (Namespace(bar__a=1), Namespace(bar__quux__title=2), Namespace(bar__a=1, bar__quux__title=2)),
    (Namespace(bar__a=1), Namespace(bar__quux__title="hi"), Namespace(bar__a=1, bar__quux__title="hi")),
    (Namespace(bar__='foo'), Namespace(bar__fisk="hi"), Namespace(bar__='foo', bar__fisk='hi')),
], ids=str)
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
    assert setdefaults_path(
        Namespace(a__b=1, a__c=2),
        a=Namespace(d=3),
        a__e=4,
    ) == Namespace(
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
    assert setdefaults_path(Namespace(
        a=Namespace()),
        a__b=Namespace()
    ) == Namespace(
        a__b=Namespace(),
    )

    assert setdefaults_path(
        Namespace(),
        attrs__class=Namespace(),
    ) == Namespace(
        attrs__class=Namespace(),
    )


def test_namespace_retain_empty():
    assert Namespace(a=Namespace(b=Namespace())).a.b == Namespace()


def test_namespace_shortcut_overwrite():
    assert Namespace(
        Namespace(
            x=Shortcut(y__z=1, y__zz=2),
        ),
        Namespace(
            x=Namespace(a__b=3),
        ),
    ) == Namespace(
        x__a__b=3,
    )


def test_namespace_shortcut_overwrite_backward():
    assert Namespace(
        Namespace(x=Namespace(y__z=1, y__zz=2)),
        Namespace(x=Shortcut(a__b=3)),
    ) == Namespace(
        x__a__b=3,
        x__y__z=1,
        x__y__zz=2,
    )


def test_order_after_0():
    sorts_right([
        Struct(name='foo', expected_position=1),
        Struct(name='bar', expected_position=2),
        Struct(name='quux', after=0, expected_position=0),
        Struct(name='baz', expected_position=3),
    ])


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

    assert str(e.value).replace("u'", "'") == "'Tried to order after does-not-exist but that key does not exist'"


def test_sort_after_points_to_nothing_plural():
    with pytest.raises(KeyError) as e:
        sort_after([
            Struct(name='quux'),
            Struct(name='foo', after='does-not-exist2'),
            Struct(name='quux6', after='does-not-exist'),
        ])

    assert str(e.value).replace("u'", "'") == "'Tried to order after does-not-exist, does-not-exist2 " \
                                              "but those keys do not exist'"


def test_assert_kwargs_empty():
    assert_kwargs_empty({})

    with pytest.raises(TypeError) as e:
        assert_kwargs_empty(dict(foo=1, bar=2, baz=3))

    assert str(e.value) == "test_assert_kwargs_empty() got unexpected keyword arguments 'bar', 'baz', 'foo'"


def test_dispatch_legacy():
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


def test_dispatch_wraps():
    @dispatch
    def foo():
        """test"""
        pass

    assert foo.__doc__ == 'test'


def test_dispatch_store_arguments():
    @dispatch(
        foo=1,
        bar=2,
    )
    def foo():
        pass

    assert foo.dispatch == Namespace(foo=1, bar=2)


def test_full_function_name():
    assert full_function_name(setattr_path) == 'tri_declarative.setattr_path'


def test_dispatch_with_target():
    @dispatch
    def quux(title):
        # something...
        return title

    @dispatch(b='X', quux=Namespace(call_target=quux), )
    def bar(a, b, quux):
        return a + b + quux()

    def baz(a, b, c):
        # something...
        return a + b + c

    @dispatch(
        bar=Namespace(call_target=bar),
        bar__a='5',
        bar__quux__title='hi!',
        baz=Namespace(call_target=baz)
    )
    def foo(a, b, c, bar, baz):
        x = bar()
        y = baz()
        # do something with the inputs a, b, c...
        return a + b + c + x + y

    assert foo('1', '2', '3', bar__quux__title='7', baz__a='A', baz__b='B', baz__c='C') == '1235X7ABC'


def test_is_shortcut():
    t = Namespace(x=1)
    assert not is_shortcut(t)

    s = Shortcut(x=1)
    assert isinstance(s, Namespace)
    assert is_shortcut(s)


def test_is_shortcut_function():
    def f():
        pass

    assert not is_shortcut(f)

    @shortcut
    def g():
        pass

    assert is_shortcut(g)

    class Foo:
        @staticmethod
        @shortcut
        def h():
            pass

        @classmethod
        @class_shortcut
        def i(cls):
            pass

    assert is_shortcut(Foo.h)
    assert is_shortcut(Foo.i)


def test_get_shortcuts_by_name():
    class Foo:
        a = Shortcut(x=1)

    class Bar(Foo):
        @staticmethod
        @shortcut
        def b(self):
            pass

        @classmethod
        @class_shortcut
        def c(cls):
            pass

    assert get_shortcuts_by_name(Bar) == dict(a=Bar.a, b=Bar.b, c=Bar.c)


def test_class_shortcut():
    @with_meta
    class Foo:
        @dispatch(
            bar=17
        )
        def __init__(self, bar, **kwargs):
            self.bar = bar

        @classmethod
        @class_shortcut
        def shortcut(cls, **args):
            return cls(**args)

        @classmethod
        @class_shortcut(
            foo=7
        )
        def shortcut2(cls, call_target, foo):
            del call_target
            return foo

    class MyFoo(Foo):
        class Meta:
            bar = 42

    assert Foo.shortcut().bar == 17
    assert MyFoo.shortcut().bar == 42
    assert MyFoo.shortcut2() == 7


def test_class_shortcut_class_call_target():
    @with_meta
    class Foo:
        @classmethod
        @class_shortcut(
            foo=7
        )
        def shortcut(cls, call_target, foo):
            del call_target
            return foo

    class MyFoo(Foo):
        @classmethod
        @class_shortcut(
            foo=5
        )
        def shortcut(cls, call_target, foo):
            del call_target
            return foo

        @classmethod
        @class_shortcut(
            call_target__attribute='shortcut'
        )
        def shortcut2(cls, call_target, **kwargs):
            return call_target(**kwargs)

        @classmethod
        @class_shortcut(
            call_target=Foo.shortcut
        )
        def shortcut3(cls, call_target, **kwargs):
            return call_target(**kwargs)

    assert Foo.shortcut() == 7
    assert MyFoo.shortcut() == 5
    assert MyFoo.shortcut2() == 5
    assert MyFoo.shortcut3() == 7


def test_class_shortcut_shortcut():
    class Foo:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        @classmethod
        @class_shortcut(
            x=17
        )
        def shortcut1(self, call_target=None, **kwargs):
            return call_target(**kwargs)

    Foo.shortcut2 = Shortcut(
        y=42,
        call_target__cls=Foo,
        call_target__attribute='shortcut1',
    )

    assert Foo.shortcut1().kwargs == {'x': 17}
    assert Foo.shortcut2().kwargs == {'x': 17, 'y': 42}


def test_refinable_object_complete_example():
    def f(p=11):
        return p

    class Foo(RefinableObject):
        a = Refinable()
        b = Refinable()

        @dispatch(
            b='default_b',
        )
        def __init__(self, **kwargs):
            self.non_refinable = 17
            super(Foo, self).__init__(**kwargs)

        @staticmethod
        @dispatch(
            f=Namespace(call_target=f)
        )
        @refinable
        def c(f):
            """
            c docstring
            """
            return f()

        @staticmethod
        @shortcut
        @dispatch(
            call_target=f
        )
        def shortcut_to_f(call_target):
            return call_target()

    @shortcut
    @dispatch(
        call_target=Foo
    )
    def shortcut_to_foo(call_target):
        return call_target()

    Foo.shortcut_to_foo = staticmethod(shortcut_to_foo)

    Foo.q = Shortcut(call_target=Foo, b='refined_by_shortcut_b')

    with pytest.raises(TypeError):
        Foo(non_refinable=1)

    assert Foo().a is None
    assert Foo(a=1).a == 1

    # refinable function with dispatch
    assert Foo().c() == 11
    assert Foo().c(f__p=13) == 13
    assert Foo(c=lambda p: 77).c(12321312312) == 77


def test_refinable_object2():
    class MyClass(RefinableObject):
        @dispatch(
            foo__bar=17
        )
        def __init__(self, **kwargs):
            super(MyClass, self).__init__(**kwargs)

        foo = Refinable()

    assert MyClass().foo.bar == 17
    assert MyClass(foo__bar=42).foo.bar == 42

    with pytest.raises(TypeError):
        MyClass(barf=17)


def test_refinable_object_binding():
    class MyClass(RefinableObject):
        foo = Refinable()
        container = Refinable()

        def bind(self, container):
            new_object = copy.copy(self)
            new_object.container = container
            return new_object

    container = object()
    template = MyClass(foo=17)
    bound_object = template.bind(container)
    bound_object.foo = 42

    assert template.foo == 17
    assert bound_object.foo == 42
    assert bound_object.container is container


def test_nested_namespace_overriding_and_calling():
    @dispatch
    def f(extra):
        return extra.foo

    foo = Shortcut(
        call_target=f,
        extra__foo='asd',
    )
    assert foo(extra__foo='qwe') == 'qwe'


def test_retain_shortcut_type():
    assert isinstance(Shortcut(foo=Shortcut()).foo, Shortcut)
    assert isinstance(Shortcut(foo=Shortcut(bar=Shortcut())).foo.bar, Shortcut)

    assert Shortcut(foo__bar__q=1, foo=Shortcut(bar=Shortcut())).foo.bar.q == 1


def test_shortcut_call_target_attribute():
    class Foo:
        @classmethod
        def foo(cls):
            return cls

    assert Shortcut(call_target__attribute='foo', call_target__cls=Foo)() is Foo
    assert isinstance(Shortcut(call_target__cls=Foo)(), Foo)


def test_refinable_object3():
    class MyClass(RefinableObject):
        x = Refinable()
        y = Refinable()

        @dispatch(
            x=None,
            y=17,
        )
        def __init__(self, **kwargs):
            super(MyClass, self).__init__(**kwargs)

    m = MyClass(x=1, y=2)
    assert m.x == 1
    assert m.y == 2

    m = MyClass(x=1)
    assert m.x == 1
    assert m.y == 17

    with pytest.raises(TypeError) as e:
        MyClass(z=42)

    assert str(e.value) == "'MyClass' object has no refinable attribute(s): z"

    with pytest.raises(TypeError) as e:
        MyClass(z=42, w=99)

    assert str(e.value) == "'MyClass' object has no refinable attribute(s): w, z"


def test_refinable_no_constructor():
    @dispatch(
        x=None,
        y=17,
    )
    class MyClass(RefinableObject):
        x = Refinable()
        y = Refinable()

    m = MyClass(x=1)
    assert m.x == 1
    assert m.y == 17


def test_refinable_no_dispatch():
    class MyClass(RefinableObject):
        x = Refinable()
        y = Refinable()

    m = MyClass(x=1)
    assert m.x == 1
    assert m.y is None

    m = MyClass(x__y=17)
    assert hasattr(m, 'x')
    assert m.x.y == 17


def test_refinable_object_with_dispatch():
    class MyClass(RefinableObject):
        x = Refinable()
        y = Refinable()

        @dispatch(
            x=17,
            y=EMPTY,
        )
        def __init__(self, **kwargs):
            super(MyClass, self).__init__(**kwargs)

    m = MyClass()
    assert m.x == 17
    assert m.y == {}


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


def test_get_members_error_message():
    with pytest.raises(TypeError) as e:
        get_members(None, None, None)

    assert str(e.value) == "get_members either needs a member_class parameter or an is_member check function (or both)"


def test_get_signature_on_namespace_does_not_modify_its_contents():
    foo = Namespace()
    get_signature(foo)
    assert str(foo) == 'Namespace()'


def test_shortcut_chaining():
    def endpoint(**kwargs):
        return kwargs

    foo = Shortcut(
        call_target=endpoint,
        tag='foo',
    )
    bar = Shortcut(
        call_target=foo,
        bar=1,

        # these two will get popped off by Namespace.__call__, let's make sure they are!
        call_target__cls='randomcrap',
        call_target__attribute='randomcrap',
    )

    assert bar() == dict(tag='foo', bar=1)


def test_class_shortcut__shortcut_stack():
    class MyFoo:
        @classmethod
        @class_shortcut
        def shortcut(cls, call_target):
            return call_target()

        @classmethod
        @class_shortcut(
            call_target__attribute='shortcut'
        )
        def shortcut2(cls, call_target, **kwargs):
            return call_target(**kwargs)

    middle = Shortcut(call_target=MyFoo.shortcut2)

    class MyOtherFoo(MyFoo):
        @classmethod
        @class_shortcut(
            call_target=middle
        )
        def shortcut3(cls, call_target, **kwargs):
            return call_target(**kwargs)

    assert MyOtherFoo().shortcut2().__tri_declarative_shortcut_stack == ['shortcut2', 'shortcut']
    assert MyOtherFoo().shortcut3().__tri_declarative_shortcut_stack == ['shortcut3', 'shortcut2', 'shortcut']
