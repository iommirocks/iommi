import pytest

from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import Namespace
from iommi.declarative.with_meta import with_meta


def test_empty():
    @with_meta
    class Test:

        def __init__(self, foo):
            assert foo == 'bar'

    Test('bar')


def test_constructor():
    @with_meta
    class Test:
        class Meta:
            foo = 'bar'

        def __init__(self, foo):
            assert foo == 'bar'

    # noinspection PyArgumentList
    Test()


def test_override():
    @with_meta
    class Test:
        class Meta:
            foo = 'bar'

        def __init__(self, foo):
            assert foo == 'baz'

    Test(foo='baz')


def test_inheritance():
    @with_meta
    class Test:
        class Meta:
            foo = 'bar'

    @with_meta
    class TestSubclass(Test):
        def __init__(self, foo):
            assert foo == 'bar'

    # noinspection PyArgumentList
    TestSubclass()


def test_inheritance_base():
    @with_meta
    class Test:
        def __init__(self, foo):
            assert 'bar' == foo

    class TestSubclass(Test):
        class Meta:
            foo = 'bar'

    # noinspection PyArgumentList
    TestSubclass()


def test_inheritance_with_override():
    @with_meta
    class Test:
        class Meta:
            foo = 'bar'

    @with_meta
    class TestSubclass(Test):
        class Meta:
            foo = 'baz'

        def __init__(self, foo):
            assert foo == 'baz'

    # noinspection PyArgumentList
    TestSubclass()


def test_pos_arg_override():
    @with_meta
    class Test:
        class Meta:
            foo = 'foo'
            bar = 'bar'

        def __init__(self, apa, foo, gapa, **kwargs):
            assert apa == 'apa'
            assert foo == 'foo'
            assert gapa == 'gapa'
            assert 'bar' in kwargs

    # noinspection PyArgumentList
    Test('apa', gapa='gapa')


def test_args_get_by_pos():
    @with_meta
    class Test:
        class Meta:
            foo = 'foo'

        def __init__(self, foo):
            assert foo == 'foo'

    # noinspection PyArgumentList
    Test()


def test_args_get_by_name():
    @with_meta
    class Test:
        class Meta:
            foo = 'foo'

        def __init__(self, foo=None):
            assert foo == 'foo'

    Test()


def test_args_override_by_pos():
    @with_meta
    class Test:
        class Meta:
            foo = 'foo'

        def __init__(self, foo):
            assert foo == 'bar'

    Test('bar')


def test_args_override_by_name():
    @with_meta
    class Test:
        class Meta:
            foo = 'foo'

        def __init__(self, foo):
            self.foo = foo

    t = Test(foo='bar')
    assert t.foo == 'bar'


def test_too_many_args_check():
    @with_meta
    class Test:
        class Meta:
            foo = 'foo'

        # noinspection PyUnusedLocal
        def __init__(self, foo):
            pass

    with pytest.raises(TypeError) as e:
        # noinspection PyArgumentList
        Test('foo', 'bar')

    assert 'Too many positional arguments' == str(e.value)


# noinspection PyArgumentEqualDefault
def test_add_init_kwargs():
    @with_meta(add_init_kwargs=True)
    class Test:
        class Meta:
            foo = 'bar'
            _bar = 'baz'

        def __init__(self, foo):
            assert 'bar' == foo

    # noinspection PyArgumentList
    Test()


def test_not_add_init_kwargs():
    @with_meta(add_init_kwargs=False)
    class Test:
        class Meta:
            foo = 'bar'

        def __init__(self):
            assert self.get_meta().foo == 'bar'

    Test()


def test_namespaciness():
    @with_meta(add_init_kwargs=False)
    class Foo:
        class Meta:
            foo = {'bar': 17}

    class Bar(Foo):
        class Meta:
            foo = {'baz': 42}

    assert Bar().get_meta() == Namespace(
        foo__bar=17,
        foo__baz=42,
    )


def test_namespaciness_override():
    @with_meta()
    class Foo:
        class Meta:
            foo = {'bar': 17}

        @dispatch
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    assert Foo(foo__baz=42).kwargs == Namespace(
        foo__bar=17,
        foo__baz=42,
    )


def test_semantics_after_none_from_meta():
    @with_meta
    class MyForm:
        class Meta:
            actions = None

        @dispatch
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    form = MyForm(actions__magic__display_name="A magic button")
    assert form.kwargs == Namespace(actions__magic__display_name="A magic button")


def test_none_semantics_over_meta():
    @with_meta
    class MyForm:
        class Meta:
            actions__magic__display_name = "A magic button"

        @dispatch
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    form = MyForm(actions=None)
    assert form.kwargs == Namespace(actions=None)


def test_dispatch_semantics_after_none_from_meta():
    @with_meta
    class MyForm:
        class Meta:
            actions = None

        @dispatch(
            actions__magic__display_name="A magic button"
        )
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    form = MyForm()
    assert form.kwargs == Namespace(actions=None)


def test_dispatch_none_semantics_after_meta():
    @with_meta
    class MyForm:
        class Meta:
            actions__magic__display_name = "A magic button"

        @dispatch(
            actions=None
        )
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    form = MyForm()
    assert form.kwargs == Namespace(actions__magic__display_name="A magic button")


def test_dispatch_none_semantics_after_superclass_meta():
    @with_meta
    class MyForm:
        class Meta:
            actions__magic__display_name = "A magic button"

        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    class SubForm(MyForm):
        @dispatch(
            actions=None
        )
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    form = SubForm()
    assert form.kwargs == Namespace(actions=None)


def test_dispatch_semantics_after_none_superclass_meta():
    @with_meta
    class MyForm:
        class Meta:
            actions = None

        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    class SubForm(MyForm):
        @dispatch(
            actions__magic__display_name="A magic button"
        )
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    form = SubForm()
    assert form.kwargs == Namespace(actions__magic__display_name="A magic button")


def test_meta_staticmethod():
    @with_meta
    class Foo:
        class Meta:
            @staticmethod
            def foo(bar):
                return bar

        def __init__(self, **_):
            pass

    assert Foo().get_meta().foo(17) == 17
