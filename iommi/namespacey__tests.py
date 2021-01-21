import pytest
from tri_declarative import (
    dispatch,
    Namespace,
    with_meta,
)

from iommi.namespacey import (
    Namespacey,
    Refinable,
    RefinedNamespace,
)


def test_empty():
    class MyNamespacey(Namespacey):
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            super().__init__(**kwargs)

    my_namespacey = MyNamespacey(17, x=42)
    assert my_namespacey.namespace == Namespace()
    assert my_namespacey.args == (17,)
    assert my_namespacey.kwargs == dict(x=42)
    assert my_namespacey.namespace == Namespace()


def test_refinable():
    class MyNamespacey(Namespacey):
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            super().__init__(**kwargs)

        a = Refinable()

    my_namespacey = MyNamespacey(17, x=42, a=4711)
    assert my_namespacey.namespace == Namespace(a=4711)
    assert my_namespacey.args == (17,)
    assert my_namespacey.kwargs == dict(x=42, a=4711)


def test_with_meta():

    @with_meta
    class MyNamespacey(Namespacey):
        a = Refinable()
        b = Refinable()

        class Meta:
            a = 1

    my_namespacey = MyNamespacey(b=2)
    assert my_namespacey.namespace == Namespace(a=1, b=2)


def test_with_dispatch():

    class MyNamespacey(Namespacey):
        a = Refinable()
        b = Refinable()

        @dispatch(
            a=1
        )
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    my_namespacey = MyNamespacey(b=2)
    assert my_namespacey.namespace == Namespace(a=1, b=2)


def test_refine():
    class MyNamespacey(Namespacey):
        a = Refinable()

    my_namespacey = MyNamespacey(a=17)
    assert my_namespacey.namespace == Namespace(a=17)

    my_refined_namespacey = my_namespacey.refine(a=42)
    assert my_refined_namespacey.namespace == Namespace(a=42)
    assert isinstance(my_refined_namespacey, MyNamespacey)


def test_refine_defaults():
    class MyNamespacey(Namespacey):
        a = Refinable()

    my_refined_namespacey = MyNamespacey().refine_defaults(a=42)
    assert my_refined_namespacey.namespace == Namespace(a=42)

    my_namespace = MyNamespacey(a=17)
    assert my_namespace.namespace == Namespace(a=17)

    my_refined_namespacey = my_namespace.refine_defaults(a=42)
    assert my_refined_namespacey.namespace == Namespace(a=17)


def test_finalize():
    class MyNamespacey(Namespacey):
        a = Refinable()

    my_namespacey = MyNamespacey(a=42)
    my_namespacey.finalize()

    assert my_namespacey.a == 42


def test_no_double_finalize():
    with pytest.raises(AssertionError) as e:
        Namespacey().finalize().finalize()
    assert 'already finalized' in str(e.value)


def test_refined_namespace():
    base = Namespace(a=1, b=2)
    refined = RefinedNamespace('refinement', base, b=3)
    assert refined == Namespace(a=1, b=3)


def test_refined_defaults():
    base = Namespace(a=1, b=2)
    refined = RefinedNamespace('refinement', base, defaults=True, b=3, c=4)
    assert refined == Namespace(a=1, b=2, c=4)


def test_refined_as_stack():
    namespace = Namespace(a=1)
    namespace = RefinedNamespace('refinement', namespace, b=2)
    namespace = RefinedNamespace('defaults refinement', namespace, defaults=True, c=3)
    namespace = RefinedNamespace('further refinement', namespace, d=4)
    namespace = RefinedNamespace('further defaults refinement', namespace, defaults=True, e=5)
    assert namespace == dict(a=1, b=2, c=3, d=4, e=5)
    assert namespace.as_stack() == [
        ('further defaults refinement', {'e': 5}),
        ('defaults refinement', {'c': 3}),
        ('base', {'a': 1}),
        ('refinement', {'b': 2}),
        ('further refinement', {'d': 4}),
    ]
