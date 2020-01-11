iommi
=====

.. image:: https://travis-ci.org/TriOptima/iommi.svg?branch=master
    :target: https://travis-ci.org/TriOptima/iommi.svg

.. image:: http://codecov.io/github/TriOptima/iommi.svg/coverage.svg?branch=master
    :target: http://codecov.io/github/TriOptima/iommi.svg?branch=master


iommi is a django-based framework for even higher abstraction and faster development than django itself.

Major features:

- A system to project django model definitions into more high level definitions
- :doc:`Forms <forms>`: view models, data validation, and parsing
- :doc:`Queries <queries>`: filtering lists/query sets
- :doc:`Tables <tables>`: view models for lists/query sets, html tables, and CSV reports
- :doc:`Pages <pages>`: compose pages from parts like forms, tables and html fragments

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

See :doc:`usage`.


Running tests
-------------

You need tox installed then just :code:`make test`.


License
-------

BSD


Documentation
-------------

http://iommi.readthedocs.org.
