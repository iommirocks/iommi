from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    Namespace,
)


def test_dispatch():
    @dispatch(foo=EMPTY)
    def f(**kwargs):
        return kwargs

    assert f() == dict(foo={})


def test_dispatch_legacy():
    @dispatch(bar__a='5', bar__quux__title='hi!')
    def foo(a, b, c, bar, baz):
        x = do_bar(**bar)
        y = do_baz(**baz)
        # do something with the inputs a, b, c...
        return a + b + c + x + y

    @dispatch(b='X', quux={}, )
    def do_bar(a, b, quux):
        return a + b + do_quux(**quux)

    def do_baz(a, b, c):
        # something...
        return a + b + c

    @dispatch
    def do_quux(title):
        # something...
        return title

    assert foo('1', '2', '3', bar__quux__title='7', baz__a='A', baz__b='B', baz__c='C') == '1235X7ABC'


def test_dispatch_wraps():
    @dispatch
    def foo():
        """test"""
        pass

    assert foo.__doc__ == 'test'


def test_dispatch_store_arguments():
    @dispatch(
        foo=1,
        bar=2,
    )
    def foo():
        pass

    assert foo.dispatch == Namespace(foo=1, bar=2)


def test_dispatch_with_target():
    @dispatch
    def quux_(title):
        # something...
        return title

    @dispatch(b='X', quux=Namespace(call_target=quux_), )
    def bar_(a, b, quux):
        return a + b + quux()

    def baz_(a, b, c):
        # something...
        return a + b + c

    @dispatch(
        bar=Namespace(call_target=bar_),
        bar__a='5',
        bar__quux__title='hi!',
        baz=Namespace(call_target=baz_)
    )
    def foo(a, b, c, bar, baz):
        x = bar()
        y = baz()
        # do something with the inputs a, b, c...
        return a + b + c + x + y

    assert foo('1', '2', '3', bar__quux__title='7', baz__a='A', baz__b='B', baz__c='C') == '1235X7ABC'


def test_semantics_after_none_from_meta():
    class MyForm:
        @dispatch(
            actions=None
        )
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    form = MyForm(actions__magic__display_name="A magic button")
    assert form.kwargs == Namespace(actions__magic__display_name="A magic button")


def test_none_semantics_over_meta():
    class MyForm:
        @dispatch(
            actions__magic__display_name="A magic button"
        )
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    form = MyForm(actions=None)
    assert form.kwargs == Namespace(actions=None)
