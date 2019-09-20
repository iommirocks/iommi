import pytest
from tri_declarative import with_meta


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

    TestSubclass()


def test_inheritance_base():
    @with_meta
    class Test:
        def __init__(self, foo):
            assert 'bar' == foo

    class TestSubclass(Test):
        class Meta:
            foo = 'bar'

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

    Test('apa', gapa='gapa')


def test_args_get_by_pos():
    @with_meta
    class Test:
        class Meta:
            foo = 'foo'

        def __init__(self, foo):
            assert foo == 'foo'

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

        def __init__(self, foo):
            pass

    with pytest.raises(TypeError) as e:
        Test('foo', 'bar')

    assert 'Too many positional arguments' == str(e.value)


def test_add_init_kwargs():
    @with_meta(add_init_kwargs=True)
    class Test:
        class Meta:
            foo = 'bar'
            _bar = 'baz'

        def __init__(self, foo):
            assert 'bar' == foo

    Test()


def test_not_add_init_kwargs():
    @with_meta(add_init_kwargs=False)
    class Test:
        class Meta:
            foo = 'bar'

        def __init__(self):
            assert self.get_meta().foo == 'bar'

    Test()
