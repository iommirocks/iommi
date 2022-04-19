from tri_declarative import (
    class_shortcut,
    dispatch,
    get_shortcuts_by_name,
    is_shortcut,
    Namespace,
    Shortcut,
    shortcut,
    with_meta,
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
        def __init__(self, bar, **_):
            self.bar = bar

        @classmethod
        @class_shortcut
        def shortcut(cls, **args):
            return cls(**args)

        # noinspection PyUnusedLocal
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
        # noinspection PyUnusedLocal
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
        def shortcut1(cls, call_target=None, **kwargs):
            return call_target(**kwargs)

    Foo.shortcut2 = Shortcut(
        y=42,
        call_target__cls=Foo,
        call_target__attribute='shortcut1',
    )

    assert Foo.shortcut1().kwargs == {'x': 17}
    assert Foo.shortcut2().kwargs == {'x': 17, 'y': 42}


def test_shortcut_to_superclass():
    class Foo:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        @classmethod
        @class_shortcut(
            x=17
        )
        def baz(cls, call_target, **kwargs):
            return call_target(**kwargs)

    class Bar(Foo):
        @classmethod
        @class_shortcut(
            call_target__attribute='baz',
            y=42
        )
        def baz(cls, call_target, **kwargs):
            return call_target(**kwargs)

    result = Bar.baz()
    assert result.kwargs == dict(x=17, y=42)
    assert isinstance(result, Bar)


def test_shortcut_to_superclass_two_calls():
    class Foo:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        @classmethod
        @class_shortcut(
            z=4711
        )
        def buzz(cls, call_target, **kwargs):
            return call_target(**kwargs)

        @classmethod
        @class_shortcut(
            call_target__attribute='buzz',
            x=17
        )
        def baz(cls, call_target, **kwargs):
            return call_target(**kwargs)

    class Bar(Foo):
        @classmethod
        @class_shortcut(
            call_target__attribute='baz',
            y=42
        )
        def baz(cls, call_target, **kwargs):
            return call_target(**kwargs)

    result = Bar.baz()
    assert result.kwargs == dict(x=17, y=42, z=4711)
    assert isinstance(result, Bar)


def test_shortcut_inherit():
    class Foo:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        @classmethod
        @class_shortcut(
            z=4711
        )
        def bar(cls, call_target, **kwargs):
            return call_target(**kwargs)

    class Bar(Foo):
        @classmethod
        @class_shortcut(
            call_target__attribute='bar',
            x=17
        )
        def bar(cls, call_target, **kwargs):
            return call_target(**kwargs)

    class Baz(Bar):
        pass

    result = Baz.bar()
    assert result.kwargs == dict(x=17, z=4711)
    assert isinstance(result, Bar)


def test_shortcut_inherit_and_override():
    class Foo:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        @classmethod
        @class_shortcut(
            z=4711
        )
        def bar(cls, call_target, **kwargs):
            return call_target(**kwargs)

    class Bar(Foo):
        @classmethod
        @class_shortcut(
            call_target__attribute='bar',
            x=17
        )
        def bar(cls, call_target, **kwargs):
            return call_target(**kwargs)

    class Baz(Bar):
        @classmethod
        @class_shortcut(
            call_target__attribute='bar',
            y=42
        )
        def bar(cls, call_target, **kwargs):
            return call_target(**kwargs)

    result = Baz.bar()
    assert result.kwargs == dict(x=17, y=42, z=4711)
    assert isinstance(result, Bar)


def test_shortcut_choice():
    class IommiField:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        @classmethod
        @class_shortcut(
            iommi_choice=True
        )
        def choice(cls, call_target, **kwargs):
            return call_target(**kwargs)

        @classmethod
        @class_shortcut(
            call_target__attribute='choice',
            iommi_choice_queryset=True
        )
        def choice_queryset(cls, call_target, **kwargs):
            return call_target(**kwargs)

    class ResolveField(IommiField):
        @classmethod
        @class_shortcut(
            call_target__attribute='choice',
            resolve_choice=True
        )
        def choice(cls, call_target, **kwargs):
            return call_target(**kwargs)

        @classmethod
        @class_shortcut(
            call_target__attribute='choice_queryset',
            resolve_choice_queryset=True
        )
        def choice_queryset(cls, call_target, **kwargs):
            return call_target(**kwargs)

    result = ResolveField.choice()
    assert result.kwargs == dict(
        resolve_choice=True,
        iommi_choice=True,
    )
    assert isinstance(result, ResolveField)

    result = ResolveField.choice_queryset()
    assert result.kwargs == dict(
        resolve_choice_queryset=True,
        iommi_choice_queryset=True,
        resolve_choice=True,
        iommi_choice=True,
    )
    assert isinstance(result, ResolveField)

    class ElmField(ResolveField):
        @classmethod
        @class_shortcut(
            call_target__attribute='choice',
            elm_choice=True
        )
        def choice(cls, call_target, **kwargs):
            return call_target(**kwargs)

        @classmethod
        @class_shortcut(
            call_target__attribute='choice_queryset',
            elm_choice_queryset=True
        )
        def choice_queryset(cls, call_target, **kwargs):
            return call_target(**kwargs)

    result = ElmField.choice()
    assert result.kwargs == dict(
        elm_choice=True,
        resolve_choice=True,
        iommi_choice=True,
    )
    assert isinstance(result, ElmField)

    result = ElmField.choice_queryset()
    assert result.kwargs == dict(
        elm_choice_queryset=True,
        resolve_choice_queryset=True,
        iommi_choice_queryset=True,
        elm_choice=True,
        resolve_choice=True,
        iommi_choice=True,
    )
    assert isinstance(result, ElmField)


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
