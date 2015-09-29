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
