from tri_declarative import (
    _generate_rst_docs,
    class_shortcut,
    dispatch,
    Refinable,
    refinable,
    RefinableObject,
    Shortcut,
)


def test_generate_docs():
    def some_callable():
        pass

    class Foo(RefinableObject):
        """docstring for Foo"""

        name = Refinable()
        description = Refinable()
        some_other_thing = Refinable()

        @dispatch(
            name='foo-name',
            description=lambda foo, bar: 'qwe',
            some_other_thing=some_callable,
        )
        def __init__(self):
            """
            :param name: description of the name field
            """
            super(Foo, self).__init__()

        @staticmethod
        @refinable
        def refinable_func(field, instance, value):
            pass

        @classmethod
        @class_shortcut
        def shortcut1(cls):
            return cls()

        @classmethod
        @class_shortcut(
            description='fish'
        )
        def shortcut2(cls, call_target):
            """shortcut2 docstring"""
            return call_target()

        @classmethod
        @class_shortcut(
            description=lambda foo: 'qwe'
            # TODO: This is currently not shown in the documentation output, but it should be!
        )
        def shortcut3(cls, call_target):
            """
            shortcut3 docstring

            :param call_target: something something call_target
            """
            return call_target()

    Foo.shortcut4 = Shortcut(
        call_target=Foo,
        name='baz',
        description='qwe',
    )

    (actual_filename, actual_doc), = list(_generate_rst_docs(classes=[Foo]))

    assert actual_filename == '/Foo.rst'

    expected_doc = """
Foo
===

docstring for Foo

Refinable members
-----------------

* `description`
* `name`
    description of the name field

* `refinable_func`
* `some_other_thing`

Defaults
^^^^^^^^

* `description`
    * `lambda foo, bar: 'qwe'`
* `name`
    * `foo-name`
* `some_other_thing`
    * `test_docs.some_callable`

Shortcuts
---------

`shortcut1`
^^^^^^^^^^^

`shortcut2`
^^^^^^^^^^^

shortcut2 docstring

`shortcut3`
^^^^^^^^^^^

shortcut3 docstring

            :param call_target: something something call_target

`shortcut4`
^^^^^^^^^^^
    """

    assert actual_doc.strip() == expected_doc.strip()


def test_generate_docs_empty_docstring():
    class Foo(RefinableObject):
        name = Refinable()

    (actual_filename, actual_doc), = list(_generate_rst_docs(classes=[Foo]))

    assert actual_filename == '/Foo.rst'

    expected_doc = """
Foo
===


Refinable members
-----------------

* `name`

"""

    assert actual_doc.strip() == expected_doc.strip()


def test_generate_docs_description_and_params_in_constructor():
    class Foo(RefinableObject):
        """
        First description
        """

        name = Refinable()

        @dispatch
        def __init__(self, **kwargs):
            """
            __init__ description

            :param foo: foo description
            """
            super(Foo, self).__init__(**kwargs)

    (actual_filename, actual_doc), = list(_generate_rst_docs(classes=[Foo]))

    assert actual_filename == '/Foo.rst'

    expected_doc = """
Foo
===

First description

__init__ description

Refinable members
-----------------

* `name`

"""

    assert actual_doc.strip() == expected_doc.strip()


def test_generate_docs_kill_obscure_mutant():
    class Foo(RefinableObject):
        name = Refinable()

        @dispatch(
            # this is to handle that mutmut mutates strip(',') to strip('XX,XX')
            name=lambda X: X,
        )
        def __init__(self, **kwargs):
            super(Foo, self).__init__(**kwargs)

    (actual_filename, actual_doc), = list(_generate_rst_docs(classes=[Foo]))

    assert actual_filename == '/Foo.rst'

    expected_doc = """
Foo
===


Refinable members
-----------------

* `name`

Defaults
^^^^^^^^

* `name`
    * `lambda X: X`

"""

    assert actual_doc.strip() == expected_doc.strip()
