from tri_declarative import (
    evaluate,
    evaluate_recursive,
    filter_show_recursive,
    get_signature,
    matches,
    remove_show_recursive,
)


def test_evaluate_recursive():
    foo = {
        'foo': {'foo': lambda x: x * 2},
        'bar': [{'foo': lambda x: x * 2}],
        'baz': {lambda x: x * 2},
        'boo': 17
    }

    assert {'bar': [{'foo': 4}], 'foo': {'foo': 4}, 'baz': {4}, 'boo': 17} == evaluate_recursive(foo, x=2)


def test_remove_and_filter_show_recursive():
    class Foo(object):
        show = False

    assert {'qwe': {}, 'foo': [{'bar'}, {}, {}], 'asd': {'bar'}} == remove_show_recursive(filter_show_recursive({
        'foo': [Foo(), {'show': False}, {'bar'}, {}, {'show': True}],
        'bar': {'show': False},
        'baz': Foo(),
        'asd': {Foo(), 'bar'},
        'qwe': {'show': True},
        'quux': {'show': None},
    }))


def test_no_evaluate_kwargs_mismatch():
    def f(x):
        return x * 2

    assert f is evaluate(f)
    assert f is evaluate(f, y=1)


def test_get_signature():
    def f(a, b):
        pass

    def f2(b, a):
        pass

    assert 'a,b||' == get_signature(f) == get_signature(f2) == get_signature(lambda a, b: None)
    assert 'a,b||' == f.__tri_declarative_signature


def test_get_signature_fails_on_native():
    # isinstance will return False for a native function. A string will also return False.
    f = 'this is not a function'
    assert None is get_signature(f)


def test_get_signature_on_class():
    class Foo:
        def __init__(self, a, b):
            pass

    assert 'a,b,self||' == get_signature(Foo)
    assert 'a,b,self||' == Foo.__tri_declarative_signature


def test_get_signature_varargs():
    assert "a,b||*" == get_signature(lambda a, b, **c: None)


def test_evaluate_subset_parameters():
    def f(x, **_):
        return x

    assert 17 == evaluate(f, x=17, y=42)


def test_match_caching():
    assert matches("a,b", "a,b||")
    assert matches("a,b", "a||*")
    assert not matches("a,b", "c||*")
    assert matches("a,b", "a||*")
    assert not matches("a,b", "c||*")


def test_get_signature_description():
    assert 'a,b||' == get_signature(lambda a, b: None)
    assert 'a,b,c|d,e|' == get_signature(lambda a, b, c, d=None, e=None: None)
    assert 'c,d|a,b|' == get_signature(lambda d, c, b=None, a=None: None)
    assert 'a,b|c,d|*' == get_signature(lambda a, b, c=None, d=None, **_: None)
    assert 'c,d|a,b|*' == get_signature(lambda d, c, b=None, a=None, **_: None)
    assert '||*' == get_signature(lambda **_: None)


def test_match_optionals():
    assert matches("a,b", "a,b||")
    assert matches("a,b", "a,b|c|")
    assert matches("a,b,c", "a,b|c|")
    assert matches("a,b,c", "a,b|c,d|")
    assert matches("a,b", "a,b|c|*")
    assert not matches("a,b,d", "a,b|c|")
    assert matches("a,b,d", "a,b|c|*")
    assert matches("", "||")
    assert not matches("a", "||")


def test_match_special_case():
    assert not matches("", "||*")
    assert not matches("a,b,c", "||*")


def test_evaluate_extra_kwargs_with_defaults():
    def f(x, y=17):
        return x

    assert 17 == evaluate(f, x=17)


def test_evaluate_on_methods():
    class Foo(object):
        def bar(self, x):
            return x

        @staticmethod
        def baz(x):
            return x

    assert 17 == evaluate(Foo().bar, x=17)
    assert 17 == evaluate(Foo().baz, x=17)

    f = Foo().bar
    assert f is evaluate(f, y=17)


def test_early_return_from_get_signature():
    def foo(a, b, c):
        pass

    object.__setattr__(foo, '__tri_declarative_signature', 'foobar')
    assert get_signature(foo) == 'foobar'
