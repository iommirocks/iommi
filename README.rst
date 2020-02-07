iommi
=====

.. image:: https://travis-ci.org/TriOptima/iommi.svg?branch=master
    :target: https://travis-ci.org/TriOptima/iommi

.. image:: https://codecov.io/gh/TriOptima/iommi/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/TriOptima/iommi


iommi is a django-based framework for even higher abstraction and faster development than django itself.

Major features:

- A system to project django model definitions into more high level definitions
- `Forms <https://docs.iommi.rocks/en/latest/forms.html>`_: view models, data validation, and parsing
- `Queries <https://docs.iommi.rocks/en/latest/queries.html>`_: filtering lists/query sets
- `Tables <https://docs.iommi.rocks/en/latest/tables.html>`_: view models for lists/query sets, html tables, and CSV reports
- `Pages <https://docs.iommi.rocks/en/latest/pages.html>`_: compose pages from parts like forms, tables and html fragments

All the components are written with the same philosophy of:

* Everything has a name
* Traversing a namespace is done with `__` when `.` can't be used in normal python syntax
* Callables for advanced usage, values for the simple cases
* Late binding
* Declarative/programmatic hybrid API
* Prepackaged commonly used patterns (that can still be customized!)
* Single point customization with *no* boilerplate
* Escape hatches included

See `philosophy <https://docs.iommi.rocks/en/latest/philosophy.html>`_ for explanations of all these.

Example:


.. code:: python

    def music_page(request):
        class MusicPage(Page):
            musicians = Table(
                auto__model=Musician,
            )
            albums = Table(
                auto__model=Album,
            )

        return MusicPage()

This creates a page with two separate tables, one for the model :code:`Musician` and one for the model :code:`Album`.

For more examples, see the `examples project <https://github.com/TriOptima/iommi/tree/master/examples/examples>`_.


Usage
------

See `usage <https://docs.iommi.rocks/en/latest/usage.html>`_.


Running tests
-------------

You need tox installed then just :code:`make test`.


License
-------

BSD


Documentation
-------------

https://docs.iommi.rocks
