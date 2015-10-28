from tri.declarative import filter_show_recursive, evaluate_recursive, remove_show_recursive, evaluate, should_not_evaluate, \
    should_evaluate, force_evaluate
from tri.struct import Struct


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
