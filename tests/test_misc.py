from tri.declarative import extract_subkeys, getattr_path, setattr_path


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
    assert getattr_path(foo, 'bar__baz__quux') == 3

    setattr_path(foo, 'bar__baz__quux', 7)

    assert getattr_path(foo, 'bar__baz__quux') == 7

    setattr_path(foo, 'bar__baz', None)
    assert getattr_path(foo, 'bar__baz__quux') is None

    setattr_path(foo, 'bar', None)
    assert foo.bar is None
