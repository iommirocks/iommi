import copy

import pytest

from tri_declarative import (
    dispatch,
    EMPTY,
    Namespace,
    Refinable,
    refinable,
    RefinableObject,
    shortcut,
    Shortcut,
)


def test_refinable_object_complete_example():
    def f_(p=11):
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
            f=Namespace(call_target=f_)
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
            call_target=f_
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

    # noinspection PyUnresolvedReferences
    assert MyClass().foo.bar == 17
    # noinspection PyUnresolvedReferences
    assert MyClass(foo__bar=42).foo.bar == 42

    with pytest.raises(TypeError):
        MyClass(barf=17)


def test_refinable_object_binding():
    class MyClass(RefinableObject):
        foo = Refinable()
        container = Refinable()

        # noinspection PyShadowingNames
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

    assert str(e.value) == """'MyClass' object has no refinable attribute(s): z.
Available attributes:
    x
    y"""

    with pytest.raises(TypeError) as e:
        MyClass(z=42, w=99)

    assert str(e.value) == """'MyClass' object has no refinable attribute(s): w, z.
Available attributes:
    x
    y"""


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
    # noinspection PyUnresolvedReferences
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
