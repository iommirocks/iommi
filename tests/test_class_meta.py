import pytest
from tri.declarative import with_meta


def test_empty():

    @with_meta
    class Test(object):

        def __init__(self, foo):
            assert 'bar' == foo

    Test('bar')


def test_constructor():

    @with_meta
    class Test(object):
        class Meta:
            foo = 'bar'

        def __init__(self, foo):
            assert 'bar' == foo

    Test()


def test_override():

    @with_meta
    class Test(object):
        class Meta:
            foo = 'bar'

        def __init__(self, foo):
            assert 'baz' == foo

    Test(foo='baz')


def test_inheritance():

    @with_meta
    class Test(object):
        class Meta:
            foo = 'bar'

    @with_meta
    class TestSubclass(Test):
        def __init__(self, foo):
            assert 'bar' == foo

    TestSubclass()


def test_inheritance_base():

    @with_meta
    class Test(object):
        def __init__(self, foo):
            assert 'bar' == foo

    class TestSubclass(Test):
        class Meta:
            foo = 'bar'

    TestSubclass()


def test_inheritance_with_override():

    @with_meta
    class Test(object):
        class Meta:
            foo = 'bar'

    @with_meta
    class TestSubclass(Test):
        class Meta:
            foo = 'baz'

        def __init__(self, foo):
            assert 'baz' == foo

    TestSubclass()


def test_pos_arg_override():

    @with_meta
    class Test(object):
        class Meta:
            foo = 'foo'
            bar = 'bar'

        def __init__(self, apa, foo, gapa, **kwargs):
            assert 'apa' == apa
            assert 'foo' == foo
            assert 'gapa' == gapa
            assert 'bar' in kwargs

    Test('apa', gapa='gapa')


def test_args_get_by_pos():

    @with_meta
    class Test(object):
        class Meta:
            foo = 'foo'

        def __init__(self, foo):
            assert 'foo' == foo

    Test()


def test_args_get_by_name():

    @with_meta
    class Test(object):
        class Meta:
            foo = 'foo'

        def __init__(self, foo=None):
            assert 'foo' == foo

    Test()


def test_args_override_by_pos():

    @with_meta
    class Test(object):
        class Meta:
            foo = 'foo'

        def __init__(self, foo):
            assert 'bar' == foo

    Test('bar')


def test_args_override_by_name():

    @with_meta
    class Test(object):
        class Meta:
            foo = 'foo'

        def __init__(self, foo):
            assert 'bar' == foo

    Test(foo='bar')


def test_too_many_args_check():

    @with_meta
    class Test(object):
        class Meta:
            foo = 'foo'

        def __init__(self, foo):
            pass

    with pytest.raises(TypeError):
        Test('foo', 'bar')


def test_add_init_kwargs():
    @with_meta(add_init_kwargs=True)
    class Test(object):
        class Meta:
            foo = 'bar'

        def __init__(self, foo):
            assert 'bar' == foo

    Test()