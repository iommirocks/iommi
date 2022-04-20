from platform import python_implementation
from typing import Dict

import pytest

from iommi import Fragment
from iommi.docs import (
    _generate_tests_from_class_docs,
    get_default_classes,
)
from iommi.refinable import (
    Refinable,
    refinable,
    RefinableObject,
)
from iommi.shortcut import (
    Shortcut,
    with_defaults,
)


def test_generate_docs(snapshot):
    def some_callable():
        pass  # pragma: no cover

    class Foo(RefinableObject):
        """
        docstring for Foo
        """

        name = Refinable()
        description = Refinable()
        some_other_thing = Refinable()
        empty_string_default = Refinable()

        @with_defaults(
            name='foo-name',
            description=lambda foo, bar: 'qwe',
            some_other_thing=some_callable,
            empty_string_default='',
        )
        def __init__(self):
            """
            :param name: description of the name field
            """
            super(Foo, self).__init__()  # pragma: no cover

        @staticmethod
        @refinable
        def refinable_func(field, instance, value):
            pass  # pragma: no cover

        @classmethod
        @with_defaults
        def shortcut1(cls):
            return cls()  # pragma: no cover

        @classmethod
        @with_defaults(description='fish')
        def shortcut2(cls):
            """shortcut2 docstring"""
            return cls()  # pragma: no cover

        @classmethod
        # fmt: off
        @with_defaults(
            description=lambda foo: 'qwe',
        )
        # fmt: on
        def shortcut3(cls):
            """
            shortcut3 docstring

            :param call_target: something something call_target
            """
            return cls()  # pragma: no cover

    Foo.shortcut4 = Shortcut(
        call_target=Foo,
        name='baz',
        description='qwe',
    )

    ((actual_filename, actual_doc),) = list(_generate_tests_from_class_docs(classes=[Foo]))

    assert actual_filename == 'test_doc__api_Foo.py'

    snapshot.assert_match(actual_doc, 'test_generate_docs.rst')


def test_generate_docs_empty_docstring(snapshot):
    class Foo(RefinableObject):
        name = Refinable()

    ((actual_filename, actual_doc),) = list(_generate_tests_from_class_docs(classes=[Foo]))

    assert actual_filename == 'test_doc__api_Foo.py'

    snapshot.assert_match(actual_doc, 'test_generate_docs_empty_docstring.rst')


def test_generate_docs_description_and_params_in_constructor(snapshot):
    class Foo(RefinableObject):
        """
        First description
        """

        name = Refinable()

        @with_defaults
        def __init__(self, **kwargs):
            """
            __init__ description

            :param foo: foo description
            """
            super(Foo, self).__init__(**kwargs)  # pragma: no cover

    (actual_filename, actual_doc), (_, _) = list(_generate_tests_from_class_docs(classes=[Foo, RefinableObject]))

    assert actual_filename == 'test_doc__api_Foo.py'

    snapshot.assert_match(actual_doc, 'test_generate_docs_description_and_params_in_constructor.rst')


def test_generate_docs_kill_obscure_mutant(snapshot):
    class Foo(RefinableObject):
        name = Refinable()

        @with_defaults(
            # this is to handle that mutmut mutates strip(',') to strip('XX,XX')
            name=lambda X: X,
        )
        def __init__(self, **kwargs):
            super(Foo, self).__init__(**kwargs)  # pragma: no cover

    ((actual_filename, actual_doc),) = list(_generate_tests_from_class_docs(classes=[Foo]))

    assert actual_filename == 'test_doc__api_Foo.py'

    snapshot.assert_match(actual_doc, 'test_generate_docs_kill_obscure_mutant.rst')


def test_default_classes():
    default_classes = {x.__name__ for x in get_default_classes() if isinstance(x, type)}

    import iommi

    classes_in_all = {x for x in iommi.__all__ if isinstance(getattr(iommi, x), type)}

    assert (classes_in_all - default_classes) == set()


@pytest.mark.skipif(
    python_implementation() == 'PyPy',
    reason='Fails on pypy, but we only run this for building documentation and we do that on cpython',
)
def test_type_annotations(snapshot):
    class Foo(RefinableObject):
        a: int = Refinable()
        b: Dict = Refinable()
        c: Fragment = Refinable()

    (actual_filename, actual_doc), (_, _) = list(_generate_tests_from_class_docs(classes=[Foo, Fragment]))

    assert actual_filename == 'test_doc__api_Foo.py'

    snapshot.assert_match(actual_doc, 'test_type_annotations.rst')


def test_read_defaults():
    from iommi import Column
    ((actual_filename, actual_doc),) = list(_generate_tests_from_class_docs(classes=[Column]))

    assert """`time`
^^^^^^

Defaults
++++++++

* `filter__call_target__attribute`
    * `time`""" in actual_doc
