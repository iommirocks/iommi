import pytest

from iommi.evaluate import (
    evaluate,
    evaluate_member,
    evaluate_strict,
    evaluate_strict_container,
    get_callable_description,
    get_signature,
    matches,
    Namespace,
)


def test_no_evaluate_kwargs_mismatch():
    # noinspection PyUnusedLocal
    def f(x):
        assert False  # pragma: no cover

    assert evaluate(f) is f
    assert evaluate(f, y=1) is f


def test_get_signature():
    # noinspection PyUnusedLocal
    def f(a, b):
        assert False  # pragma: no cover

    # noinspection PyUnusedLocal
    def f2(b, a):
        assert False  # pragma: no cover

    assert get_signature(lambda a, b: None) == get_signature(f2) == get_signature(f) == 'a,b||'
    # noinspection PyUnresolvedReferences
    assert f.__tri_declarative_signature == 'a,b||'


def test_get_signature_fails_on_native():
    # isinstance will return False for a native function. A string will also return False.
    f = 'this is not a function'
    assert get_signature(f) is None


def test_get_signature_on_class():
    class Foo:
        # noinspection PyUnusedLocal
        def __init__(self, a, b):
            assert False  # pragma: no cover

    assert 'a,b,self||' == get_signature(Foo)
    # noinspection PyUnresolvedReferences
    assert 'a,b,self||' == Foo.__tri_declarative_signature


def test_get_signature_varargs():
    assert get_signature(lambda a, b, **c: None) == "a,b||*"


def test_evaluate_subset_parameters():
    def f(x, **_):
        return x

    assert evaluate(f, x=17, y=42) == 17


def test_evaluate_no_explicit_parameters():
    def f(**_):
        return 17

    assert evaluate(f, y=42) == 17


def test_match_caching():
    assert matches("a,b", "a,b||")
    assert matches("a,b", "a||*")
    assert not matches("a,b", "c||*")
    assert matches("a,b", "a||*")
    assert not matches("a,b", "c||*")


def test_get_signature_description():
    assert get_signature(lambda a, b: None) == 'a,b||'
    assert get_signature(lambda a, b, c, d=None, e=None: None) == 'a,b,c|d,e|'
    assert get_signature(lambda d, c, b=None, a=None: None) == 'c,d|a,b|'
    assert get_signature(lambda a, b, c=None, d=None, **_: None) == 'a,b|c,d|*'
    assert get_signature(lambda d, c, b=None, a=None, **_: None) == 'c,d|a,b|*'
    assert get_signature(lambda **_: None) == '||*'


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
    # noinspection PyUnusedLocal
    def f(x, y=17):
        return x

    assert evaluate(f, x=17) == 17


def test_evaluate_on_methods():
    class Foo:
        # noinspection PyMethodMayBeStatic
        def bar(self, x):
            return x

        @staticmethod
        def baz(x):
            return x

    assert evaluate(Foo().bar, x=17) == 17
    assert evaluate(Foo().baz, x=17) == 17

    f = Foo().bar
    assert evaluate(f, y=17) is f


def test_early_return_from_get_signature():
    # noinspection PyUnusedLocal
    def foo(a, b, c):
        assert False  # pragma: no cover

    object.__setattr__(foo, '__tri_declarative_signature', 'foobar')
    assert get_signature(foo) == 'foobar'


def test_evaluate_strict():
    with pytest.raises(AssertionError) as e:
        evaluate_strict(lambda foo: 1, bar=2, baz=4)

    assert (
        str(e.value)
        == "Evaluating lambda found at: `evaluate_strict(lambda foo: 1, bar=2, baz=4)` didn't resolve it into a value but strict mode was active, the signature doesn't match the given parameters. We had these arguments: bar, baz"
    )


def test_non_strict_evaluate():
    def foo(bar):
        return bar

    assert evaluate(foo, bar=True) is True  # first the evaluated case
    assert evaluate(foo, quuz=True) is foo  # now we missed the signature, so we get the function unevaluated back


def test_get_callable_description():
    # noinspection PyUnusedLocal
    def foo(a, b, c, *, bar, **kwargs):
        assert False  # pragma: no cover

    description = get_callable_description(foo)
    assert description.startswith('`<function test_get_callable_description.<locals>.foo at')
    assert description.endswith('`')


def test_get_callable_description_nested_lambda():
    foo = Namespace(bar=lambda x: x)

    description = get_callable_description(foo)
    assert description.startswith(
        '`Namespace(bar=<function test_get_callable_description_nested_lambda.<locals>.<lambda> at'
    )
    assert description.endswith('`')


def test_get_signature_on_namespace_does_not_modify_its_contents():
    foo = Namespace()
    get_signature(foo)
    assert str(foo) == 'Namespace()'


def test_match_empty():
    f = lambda **_: 17
    assert evaluate(f, x=1, __match_empty=False) is f
    assert evaluate(f, x=1, __match_empty=True) == 17


def test_evaluate_strict_container():
    assert evaluate_strict_container(Namespace(foo=1)) == Namespace(foo=1)
    assert evaluate_strict_container(Namespace(foo=lambda foo: foo), foo=3) == Namespace(foo=3)


def test_evaluate_member():
    class Foo:
        def __init__(self):
            self.foo = lambda x: x

    foo = Foo()
    with pytest.raises(AssertionError):
        evaluate_member(foo, 'foo')

    evaluate_member(foo, 'foo', x=3)
    assert foo.foo == 3
