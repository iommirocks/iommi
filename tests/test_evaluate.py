import sys
from tri.declarative import filter_show_recursive, evaluate_recursive, remove_show_recursive, evaluate, should_not_evaluate, \
    should_evaluate, force_evaluate, get_signature, matches
from tri.struct import Struct
import pytest


def test_evaluate_recursive():
    foo = {
        'foo': {'foo': lambda x: x * 2},
        'bar': [{'foo': lambda x: x * 2}],
        'baz': {lambda x: x * 2},
    }

    assert {'bar': [{'foo': 4}], 'foo': {'foo': 4}, 'baz': {4}} == evaluate_recursive(foo, x=2)


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


def test_no_evaluate():

    def f(x):
        return x * 2

    assert 34 == evaluate(f, x=17)
    assert 34 == should_not_evaluate(f)(17)
    assert 38 == evaluate(should_not_evaluate(f), x=42)(19)
    assert 38 == force_evaluate(should_not_evaluate(f), x=19)
    assert 19 == should_not_evaluate(19)  # should_not_evaluate() on a non-callable is a no-op
    assert 19 == should_evaluate(19)  # should_evaluate() on a non-callable is a no-op
    assert 46 == evaluate(should_evaluate(should_not_evaluate(f)), x=23)


def test_no_evaluate_recursive():

    def f(x):
        return x * 2

    subject = Struct(foo=f, bar=should_not_evaluate(f))
    assert 34 == evaluate_recursive(subject, x=17).foo
    assert 38 == evaluate_recursive(subject, x=17).bar(19)


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


def test_get_signature_fails_on_native():
    # isinstance will return False for a native function. A string will also return False.
    f = 'this is not a function'
    assert None is get_signature(f)


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
    assert 'a,b|c,d|' == get_signature(lambda a, b, c=None, d=None: None)
    assert 'c,d|a,b|' == get_signature(lambda d, c, b=None, a=None: None)
    assert 'a,b|c,d|*' == get_signature(lambda a, b, c=None, d=None, **_: None)
    assert '||*' == get_signature(lambda **_: None)


def test_match_optionals():
    assert matches("a,b", "a,b|c|")
    assert matches("a,b,c", "a,b|c|")
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


@pytest.mark.skipif(sys.version_info > (3, 0), reason='Python 3 DOES support classes as callables')
def test_get_signature_class():
    class Foo(object):
        pass

    assert None is get_signature(Foo)
