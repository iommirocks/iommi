iommi

.. image:: https://travis-ci.org/TriOptima/iommi.svg?branch=master
    :target: https://travis-ci.org/TriOptima/iommi.svg

.. image:: http://codecov.io/github/TriOptima/iommi.svg/coverage.svg?branch=master
    :target: http://codecov.io/github/TriOptima/iommi.svg?branch=master


Iommi is a django-based framework for even higher abstraction and faster development than django itself.

Major features:

- a system to project django model definitions into more high level definitions
- :doc:`forms <forms>`: view models, data validation, and parsing
- :doc:`queries <queries>`: filtering lists/query sets
- :doc:`tables <tables>`: view models for lists/query sets, html tables, and CSV reports
- :doc:`pages <pages>`: compose pages from parts like forms, tables and html fragments

All the components are written with the same philosophy of:

- late binding
- many layered customization
- single point customization without needing to introduce entire chains of classes
- prepackaged commonly used patterns (that can still be customized!)
- declarative/programmatic hybrid API
- everything has a name so can be referenced for customization
- escape hatches included


Example:


.. code:: python

    def my_page(request):
        class MyPage(Page):
            foos = Table.from_model(model=Foo)
            bars = Table.from_model(model=Bar)

        return MyPage()

This creates a page with two tables, one for the model `Foo` and one for the model `Bar`.


Usage
------

See :doc:`usage`.



Running tests
-------------

You need tox installed then just `make test`.


License
-------

BSD


Documentation
-------------

http://iommi.readthedocs.org.
