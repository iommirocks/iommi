import pytest

from iommi import (
    Part,
    register_style,
    Style,
)
from iommi.declarative.dispatch import dispatch
from iommi.refinable import (
    Prio,
    Refinable,
    RefinableObject,
)
from iommi.shortcut import (
    get_shortcuts_by_name,
    is_shortcut,
    Namespace,
    Shortcut,
    shortcut,
    superinvoking_classmethod,
    with_defaults,
)


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
        @with_defaults
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
        @with_defaults()
        def c(cls):
            pass

    assert get_shortcuts_by_name(Bar) == dict(a=Bar.a, b=Bar.b, c=Bar.c)


def test_shortcut_to_superclass_two_calls_no_decorator():
    class Foo(RefinableObject):
        x = Refinable()
        y = Refinable()
        z = Refinable()

        @classmethod
        @with_defaults
        def buzz(cls, **kwargs):
            result = cls(**kwargs)
            return result.refine(Prio.shortcut, z=4711)

        @classmethod
        @with_defaults
        def baz(cls, **kwargs):
            result = cls.buzz(**kwargs)
            return result.refine(Prio.shortcut, x=17)

    class Bar(Foo):
        @classmethod
        @superinvoking_classmethod
        @with_defaults
        def baz(cls, super_classmethod, **kwargs):
            result = super_classmethod(**kwargs)
            return result.refine(Prio.shortcut, y=42)

    result = Bar.baz()
    assert result.iommi_namespace == dict(x=17, y=42, z=4711)
    assert isinstance(result, Bar)


def test_shortcut_to_superclass_two_calls2():
    class Foo(RefinableObject):
        v = Refinable()
        w = Refinable()
        x = Refinable()
        y = Refinable()
        z = Refinable()

        @with_defaults(
            w=123,
        )
        def __init__(self, **kwargs):
            super(Foo, self).__init__(**kwargs)

        @classmethod
        @with_defaults(
            z=4711
        )
        def buzz(cls, **kwargs):
            return cls(**kwargs)

        @classmethod
        @with_defaults(
            x=17
        )
        def baz(cls, **kwargs):
            return cls.buzz(**kwargs)

    class Bar(Foo):
        @classmethod
        @superinvoking_classmethod
        @with_defaults(
            y=42
        )
        def baz(cls, super_classmethod=None, **kwargs):
            return super_classmethod(**kwargs)

    result = Bar.baz(v=456)
    result.refine_done()

    assert result.iommi_namespace == dict(v=456, w=123, x=17, y=42, z=4711)
    assert isinstance(result, Bar)
    assert result.iommi_namespace.as_stack() == [
        ('constructor', {'w': 123}),
        ('shortcut', {'z': 4711}),
        ('shortcut', {'x': 17}),
        ('shortcut', {'y': 42}),
        ('base', {'v': 456}),
    ]


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


def test_better_shortcut():
    class MyPart(Part):
        @classmethod
        @with_defaults(
            extra__thing='shortcut_thing'
        )
        def my_shortcut(cls, **kwargs):
            return cls(**kwargs)

    assert MyPart.my_shortcut().bind().extra.thing == 'shortcut_thing'

    with register_style('my_style', Style(MyPart__shortcuts__my_shortcut__extra__thing='style_thing')):
        assert MyPart.my_shortcut(iommi_style='my_style').bind().extra.thing == 'style_thing'


def test_superinvoking_classmethod_args():
    class Foo:
        @classmethod
        def f(cls, calls):
            assert cls.__name__ == 'Bar'
            calls.append('Foo:f was here')
            return calls

    class Bar(Foo):
        @classmethod
        @superinvoking_classmethod
        def f(cls, calls, super_classmethod):
            assert cls.__name__ == 'Bar'
            calls.append(f'Bar:f was here')
            return super_classmethod(calls)

    assert Bar.f([]) == [
        'Bar:f was here',
        'Foo:f was here',
    ]


def test_superinvoking_classmethod_kwargs():
    class Foo:
        @classmethod
        def f(cls, calls):
            assert cls.__name__ == 'Bar'
            calls.append(f'Foo:f was here')
            return calls

    class Bar(Foo):
        @classmethod
        @superinvoking_classmethod
        def f(cls, calls, super_classmethod):
            assert cls.__name__ == 'Bar'
            calls.append(f'Bar:f was here')
            return super_classmethod(calls=calls)

    assert Bar.f(calls=[]) == [
        'Bar:f was here',
        'Foo:f was here',
    ]


def test_shortcut_to_superclass():
    class Foo(RefinableObject):
        def __init__(self, **kwargs):
            super(Foo, self).__init__(**kwargs)

        @classmethod
        @with_defaults(
            x=17
        )
        def baz(cls, **kwargs):
            return cls(**kwargs)

    class Bar(Foo):
        @classmethod
        @superinvoking_classmethod
        @with_defaults(
            y=42
        )
        def baz(cls, super_classmethod, **kwargs):
            return super_classmethod(**kwargs)

    result = Bar.baz()
    assert result.iommi_namespace == dict(x=17, y=42)
    assert isinstance(result, Bar)


def test_superinvoking_twice():
    class Foo(RefinableObject):
        @classmethod
        @with_defaults(
            x=17,
        )
        def foo(cls, **kwargs):
            return cls(**kwargs)

    class Bar(Foo):
        @classmethod
        @superinvoking_classmethod
        @with_defaults(
            y=42,
        )
        def foo(cls, super_classmethod, **kwargs):
            return super_classmethod(**kwargs)

    assert Bar.foo().iommi_namespace == dict(x=17, y=42)

    class Baz(Bar):
        @classmethod
        @superinvoking_classmethod
        @with_defaults(
            z=9,
        )
        def foo(cls, super_classmethod, **kwargs):
            return super_classmethod(**kwargs)

    assert Baz.foo().iommi_namespace == dict(x=17, y=42, z=9)


def test_super_twice():
    class Foo(RefinableObject):
        @classmethod
        @with_defaults(
            x=17,
        )
        def foo(cls, **kwargs):
            return cls(**kwargs)

    class Bar(Foo):
        @classmethod
        @with_defaults(
            y=42,
        )
        def foo(cls, **kwargs):
            return super().foo(**kwargs)

    assert Bar.foo().iommi_namespace == dict(x=17, y=42)

    class Baz(Bar):
        @classmethod
        @with_defaults(
            z=9,
        )
        def foo(cls, **kwargs):
            return super().foo(**kwargs)

    assert Baz.foo().iommi_namespace == dict(x=17, y=42, z=9)


def test_superinvoking_misconfig_no_super_warning():
    class Foo:
        pass

    with pytest.raises(TypeError, match='Unable to find parent class implementation of Bar:baz'):
        class Bar(Foo):
            @classmethod
            @superinvoking_classmethod
            def baz(cls, super_classmethod):
                super_classmethod()
        Bar.baz()


class A:
    @classmethod
    def f(cls, m):
        m.append('This is A.f')
        return cls.g(m)

    @classmethod
    def g(cls, m):
        m.append('This is A.g')
        return m


class B_with_super_classmethod(A):
    @classmethod
    @superinvoking_classmethod
    def f(cls, m, super_classmethod):
        m.append('This is B.f')
        return super_classmethod(m)

    @classmethod
    @superinvoking_classmethod
    def g(cls, m, super_classmethod):
        m.append('This is B.g')
        return super_classmethod(m)


class B_explicit_super_args(A):
    @classmethod
    def f(cls, m):
        m.append('This is B.f')
        return super(__class__, cls).f(m)

    @classmethod
    def g(cls, m):
        m.append('This is B.g')
        return super(__class__, cls).g(m)


class B_implicit_super_args(A):
    @classmethod
    def f(cls, m):
        m.append('This is B.f')
        return super().f(m)

    @classmethod
    def g(cls, m):
        m.append('This is B.g')
        return super().g(m)


@pytest.mark.parametrize('B', [B_with_super_classmethod, B_explicit_super_args, B_implicit_super_args])
def test_super_shortcut_shadow(B):
    assert B.f([]) == [
        'This is B.f',
        'This is A.f',
        'This is B.g',
        'This is A.g',
    ]
