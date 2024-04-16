from typing import Dict

import pytest

from iommi import (
    Fragment,
    Header,
)
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import Namespace
from iommi.declarative.with_meta import with_meta
from iommi.refinable import (
    Prio,
    Refinable,
    RefinableMembers,
    RefinableNamespace,
    RefinableObject,
    prefixes,
    refinable,
)


def test_i_stil_med2():
    f = RefinableNamespace(foo__call_target__cls=Header)
    f = f._refine(
        Prio.refine,
        foo=Fragment(),
    )
    assert str(f.as_stack()) == str(
        [
            ('base', {'foo__call_target__cls': Header}),
            ('refine', {'foo': Fragment()}),
        ]
    )
    f.foo.refine_done()


def test_empty():
    class MyRefinableObject(RefinableObject):
        def __init__(self, a, x=None, **kwargs):
            self.a = a
            self.x = x
            super().__init__(**kwargs)

    my_refinable = MyRefinableObject(17, x=42)
    assert my_refinable.a == 17
    assert my_refinable.x == 42
    assert my_refinable.iommi_namespace == Namespace()


def test_refinable():
    class MyRefinableObject(RefinableObject):
        def __init__(self, a, x=None, **kwargs):
            self.a = a
            self.x = x
            super().__init__(**kwargs)

        b = Refinable()

    my_refinable = MyRefinableObject(17, x=42, b=4711)
    assert my_refinable.a == 17
    assert my_refinable.x == 42
    assert my_refinable.iommi_namespace == Namespace(b=4711)


def test_with_meta():
    @with_meta
    class MyRefinableObject(RefinableObject):
        a = Refinable()
        b = Refinable()

        class Meta:
            a = 1

    my_refinable = MyRefinableObject(b=2)
    assert my_refinable.iommi_namespace == Namespace(a=1, b=2)


def test_with_dispatch():
    class MyRefinableObject(RefinableObject):
        a = Refinable()
        b = Refinable()

        @dispatch(a=1)
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    my_refinable = MyRefinableObject(b=2)
    assert my_refinable.iommi_namespace == Namespace(a=1, b=2)


def test_refine():
    class MyRefinableObject(RefinableObject):
        a = Refinable()

    my_refinable = MyRefinableObject(a=17)
    assert my_refinable.iommi_namespace == Namespace(a=17)

    my_refined_namespacey = my_refinable.refine(a=42)
    assert my_refined_namespacey.iommi_namespace == Namespace(a=42)
    assert isinstance(my_refined_namespacey, MyRefinableObject)


@pytest.mark.parametrize(
    'path, result',
    [
        ('', []),
        ('foo', ['foo']),
        ('foo__bar', ['foo', 'foo__bar']),
        ('foo__bar__boink', ['foo', 'foo__bar', 'foo__bar__boink']),
    ],
)
def test_prefixes(path, result):
    assert list(prefixes(path)) == result


class Fruit(RefinableObject):
    taste: str = Refinable()
    color: str = Refinable()


class Basket(RefinableObject):
    fruits: Dict[str, Fruit] = RefinableMembers()


def test_refine_recursive():
    basket = Basket(fruits__banana=Fruit(color='yellow'))
    basket = basket.refine(fruits__banana__taste='good').refine_done()
    banana = basket.fruits.banana.refine_done()

    assert banana.color == 'yellow'
    assert banana.taste == 'good'
    assert str(basket.iommi_namespace.as_stack()) == (
        "[('base', {'fruits__banana': <Fruit color=yellow>}), ('refine', {'fruits__banana__taste': 'good'})]"
    )


def test_refine_recursive_defaults():
    basket = Basket(fruits__banana=Fruit(color='yellow'))
    basket = basket.refine_defaults(
        fruits__banana__color='blue',
        fruits__banana__taste='good',
    ).refine_done()
    banana = basket.fruits.banana.refine_done()

    assert banana.color == 'yellow'
    assert banana.taste is None  # Shadowed by the wholesale overwrite by Fruit
    assert str(basket.iommi_namespace.as_stack()) == (
        "["
        "('refine_defaults', {'fruits__banana__color': 'blue', 'fruits__banana__taste': 'good'}), "
        "('base', {'fruits__banana': <Fruit color=yellow>})"
        "]"
    )


def test_refine_recursive_defaults2():
    basket = Basket(fruits__banana=Fruit(color='yellow'))
    basket = basket.refine_defaults(
        fruits__banana=Fruit(
            color='blue',
            taste='good',
        ),
    ).refine_done()
    banana = basket.fruits.banana.refine_done()

    assert banana.taste is None
    assert banana.color == 'yellow'
    assert str(basket.iommi_namespace.as_stack()) == (
        "["
        "('refine_defaults', {'fruits__banana': <Fruit color=blue taste=good>}), "
        "('base', {'fruits__banana': <Fruit color=yellow>})"
        "]"
    )


def test_refine_recursive_2():
    basket = Basket(fruits__banana=Fruit(color='yellow'))
    basket = basket.refine(
        fruits__banana=Fruit(
            color='blue',
            taste='good',
        ),
    ).refine_done()
    banana = basket.fruits.banana.refine_done()

    assert banana.color == 'blue'
    assert banana.taste == 'good'
    assert str(basket.iommi_namespace.as_stack()) == (
        "["
        "('base', {'fruits__banana': <Fruit color=yellow>}), "
        "('refine', {'fruits__banana': <Fruit color=blue taste=good>})"
        "]"
    )


def test_refine_defaults():
    class MyRefinableObject(RefinableObject):
        a = Refinable()

    my_refined_refinable = MyRefinableObject().refine_defaults(a=42)
    assert my_refined_refinable.iommi_namespace == Namespace(a=42)

    my_refinable = MyRefinableObject(a=17)
    assert my_refinable.iommi_namespace == Namespace(a=17)

    my_refined_refinable = my_refinable.refine_defaults(a=42)
    assert my_refined_refinable.iommi_namespace == Namespace(a=17)


def test_refine_fail_on_call_target():
    class MyRefinableObject(RefinableObject):
        a = Refinable()

    MyRefinableObject().refine(a=17).refine_done()

    with pytest.raises(TypeError) as e:
        MyRefinableObject().refine(b=17).refine_done()
    assert str(e.value) == (
        'MyRefinableObject object has no refinable attribute(s): "b".\nAvailable attributes:\n    a\n'
    )

    with pytest.raises(TypeError) as e:
        MyRefinableObject().refine(call_target=lambda **_: None).refine_done()
    assert str(e.value) == (
        'MyRefinableObject object has no refinable attribute(s): "call_target".\nAvailable attributes:\n    a\n'
    )


def test_done_refine():
    class MyRefinableObject(RefinableObject):
        a = Refinable()

    my_namespacey = MyRefinableObject(a=42)
    my_namespacey = my_namespacey.refine_done()

    assert my_namespacey.a == 42


def test_no_double_done_refine():
    with pytest.raises(AssertionError) as e:
        RefinableObject().refine_done().refine_done()
    assert 'refine_done() already invoked on' in str(e.value)


def test_refined_namespace():
    base = RefinableNamespace(a=1, b=2)
    refined = base._refine(Prio.refine, b=3)
    assert refined == Namespace(a=1, b=3)


def test_refined_defaults():
    base = RefinableNamespace(a=1, b=2)
    refined = base._refine(Prio.refine_defaults, b=3, c=4)
    assert refined == Namespace(a=1, b=2, c=4)


def test_refined_as_stack():
    namespace = RefinableNamespace(a=1)
    namespace = namespace._refine(Prio.refine, b=2)
    namespace = namespace._refine(Prio.refine_defaults, c=3)
    namespace = namespace._refine(Prio.refine, d=4)
    namespace = namespace._refine(Prio.refine_defaults, e=5)
    assert namespace == dict(a=1, b=2, c=3, d=4, e=5)
    assert namespace.as_stack() == [
        ('refine_defaults', {'c': 3}),
        ('refine_defaults', {'e': 5}),  # Later defaults now shadow earlier defaults
        ('base', {'a': 1}),
        ('refine', {'b': 2}),
        ('refine', {'d': 4}),
    ]


def test_refine_done_not_mutating():
    o = RefinableObject()
    result = o.refine_done()
    assert o.is_refine_done is False
    assert result.is_refine_done is True


def test_subclass_override():
    class MyRefinable(RefinableObject):
        @staticmethod
        @refinable
        def foo():
            return 'MyRefinable'

    assert MyRefinable(foo=lambda: 'from argument').refine_done().foo() == 'from argument'
    assert MyRefinable().refine_done().foo() == 'MyRefinable'

    class MySubclass(MyRefinable):
        @staticmethod
        @refinable
        def foo():
            return 'MySubclass'

    assert MySubclass(foo=lambda: 'from argument').refine_done().foo() == 'from argument'
    assert MySubclass().refine_done().foo() == 'MySubclass'

    class MySubclass(MyRefinable):
        # Somewhat unexpected the base class refinable shadows the subclass override if the override is not decorated
        # @refinable
        @staticmethod
        def foo():
            return 'MySubclass'

    # Still refinable
    assert MySubclass(foo=lambda: 'from argument').refine_done().foo() == 'from argument'
    # But the default is from the base class having the @refinable decorator
    assert MySubclass().refine_done().foo() == 'MyRefinable'
    # assert MySubclass().refine_done().foo() == 'MySubclass'


def test_check_attribute_existence():
    with pytest.raises(
        TypeError,
        match=(
            'Fruit object has no refinable attribute\\(s\\): "smell".\n'
            'Available attributes:\n'
            '    color\n'
            '    taste\n'
        ),
    ):
        Fruit(smell=17)
