from io import StringIO
from platform import python_implementation
from typing import Dict

import pytest

from iommi import Fragment
from iommi.docs import (
    _generate_tests_from_class_doc,
    _generate_tests_from_class_docs,
    get_default_classes,
)
from iommi.refinable import (
    Refinable,
    RefinableObject,
    refinable,
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

    ((source_filename, actual_filename, doc_generator),) = list(_generate_tests_from_class_docs(classes=[Foo]))

    actual_doc = doc_generator()

    assert actual_filename == 'test_doc__api_Foo.py'

    snapshot.assert_match(actual_doc, 'test_generate_docs.rst')


def test_generate_docs_empty_docstring(snapshot):
    class Foo(RefinableObject):
        name = Refinable()

    ((source_filename, actual_filename, doc_generator),) = list(_generate_tests_from_class_docs(classes=[Foo]))

    actual_doc = doc_generator()

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

    (source_filename, actual_filename, doc_generator), (_, _, _) = list(
        _generate_tests_from_class_docs(classes=[Foo, RefinableObject])
    )

    actual_doc = doc_generator()

    assert actual_filename == 'test_doc__api_Foo.py'

    snapshot.assert_match(actual_doc, 'test_generate_docs_description_and_params_in_constructor.rst')


def test_generate_docs_kill_obscure_mutant(snapshot):
    class Foo(RefinableObject):
        name = Refinable()

        @with_defaults(
            # this is to handle that mutmut mutates strip(',') to strip('XX,XX')
            name=lambda X: X,  # noqa: N803
        )
        def __init__(self, **kwargs):
            super(Foo, self).__init__(**kwargs)  # pragma: no cover

    ((source_filename, actual_filename, doc_generator),) = list(_generate_tests_from_class_docs(classes=[Foo]))

    actual_doc = doc_generator()

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

    (source_filename, actual_filename, doc_generator), (_, _, _) = list(
        _generate_tests_from_class_docs(classes=[Foo, Fragment])
    )

    actual_doc = doc_generator()

    assert actual_filename == 'test_doc__api_Foo.py'

    snapshot.assert_match(actual_doc, 'test_type_annotations.rst')


def test_read_defaults():
    from iommi import Column

    ((source_filename, actual_filename, doc_generator),) = list(_generate_tests_from_class_docs(classes=[Column]))

    actual_doc = doc_generator()

    assert (
        """`Column.time`
^^^^^^^^^^^^^

Defaults
++++++++

* `filter__call_target__attribute`
    * `time`"""
        in actual_doc
    )


def test_generate_docs_ends_rst_block_badly():
    f = StringIO()

    # language=python
    f.write(
        '''

def test_1():
    # language=rst
    """
`apply`
^^^^^^^

Write the new values specified in the form into the instance specified.

        .. code-block:: python

            foo()

            # @test
            bar()
            # @end

            baz()


`as_view`
^^^^^^^^^
"""
def test_2():
    pass
'''
    )
    f.seek(0)
    target_f = StringIO()

    from make_doc_rsts import rst_from_pytest

    rst_from_pytest(source_f=f, target_f=target_f, target=None)

    v = target_f.getvalue()
    print(v)
    assert 'as_view' in v


# noinspection PyUnresolvedReferences,PyUnreachableCode
def test_generate_tests_from_class_doc():
    class Foo:
        def bar(self):
            # language=rst
            """
            Bla bla

            .. code-block:: python

                assert False
            """

    f = StringIO()
    source_filename, actual_filename, doc_generator = list(
        _generate_tests_from_class_doc(f=f, c=Foo, classes=[], cookbook_name_by_refinable_name={})
    )
    actual_doc = doc_generator()

    print(actual_doc)
    # language=python
    assert (
        actual_doc.strip()
        == '''
# NOTE: this file is automatically generated

from iommi import *
from iommi.admin import Admin
from iommi.struct import Struct
from django.urls import (
    include,
    path,
)
import pytest
from django.db import models
from tests.helpers import req, user_req, staff_req, show_output
from docs.models import *

pytestmark = pytest.mark.django_db

@pytest.fixture(autouse=True)
def auto_use(big_discography):
    pass

request = req('get')


# language=rst
"""
    
Foo
===

Base class: `object`

"""
def test_base():
    # language=rst
    """
    """

    # language=rst
    """
Initialize self.  See help(type(self)) for accurate signature.

Methods
-------

`bar`
^^^^^



Bla bla

    """

    assert False

    # language=rst
    """


    """

    '''.strip()  # noqa: W293
    )
