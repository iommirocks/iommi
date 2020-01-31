iommi
=====

.. image:: https://travis-ci.org/TriOptima/iommi.svg?branch=master
    :target: https://travis-ci.org/TriOptima/iommi.svg

.. image:: http://codecov.io/github/TriOptima/iommi.svg/coverage.svg?branch=master
    :target: http://codecov.io/github/TriOptima/iommi.svg?branch=master


iommi is a django-based framework for even higher abstraction and faster development than django itself.

Major features:

- A system to project django model definitions into more high level definitions
- `Forms <https://docs.iommi.rocks/en/latest/forms.html>`_: view models, data validation, and parsing
- `Queries <https://docs.iommi.rocks/en/latest/queries.html>`_: filtering lists/query sets
- `Tables <https://docs.iommi.rocks/en/latest/tables.html>`_: view models for lists/query sets, html tables, and CSV reports
- `Pages <https://docs.iommi.rocks/en/latest/pages.html>`_: compose pages from parts like forms, tables and html fragments

All the components are written with the same philosophy of:

- Late binding
- Many layered customization
- Single point customization without needing to introduce entire chains of classes
- Prepackaged commonly used patterns (that can still be customized!)
- Declarative/programmatic hybrid API
- Everything has a name so can be referenced for customization
- Escape hatches included


Example:


.. code:: python

    def my_page(request):
        class MyPage(Page):
            foos = Table.from_model(model=Foo)
            bars = Table.from_model(model=Bar)

        return MyPage()

This creates a page with two tables, one for the model :code:`Foo` and one for the model :code:`Bar`.


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
