iommi
=====

.. raw:: html

    <p class="mobile-logo"><a href="#"><img class="logo" src="_static/logo.svg" alt="Logo"></a></p>

.. image:: https://travis-ci.org/TriOptima/iommi.svg?branch=master
    :target: https://travis-ci.org/TriOptima/iommi

.. image:: https://codecov.io/gh/TriOptima/iommi/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/TriOptima/iommi


iommi is a django-based framework for even higher abstraction and faster development than django itself.

Major features:

- A system to project django model definitions into more high level definitions
- :doc:`Forms <forms>`: view models, data validation, and parsing
- :doc:`Queries <queries>`: filtering lists/query sets
- :doc:`Tables <tables>`: view models for lists/query sets, html tables, and CSV reports
- :doc:`Pages <pages>`: compose pages from parts like forms, tables and html fragments

All the components are written with the same philosophy of:

* Everything has a name
* Traversing a namespace is done with `__` when `.` can't be used in normal python syntax
* Callables for advanced usage, values for the simple cases
* Late binding
* Declarative/programmatic hybrid API
* Prepackaged commonly used patterns (that can still be customized!)
* Single point customization with *no* boilerplate
* Escape hatches included

See :doc:`philosophy` for explanations of all these.


Example:


.. code:: python

    def music_page(request):
        class MusicPage(Page):
            musicians = Table.from_model(
                model=Musician)
            albums = Table.from_model(
                model=Album)

        return MusicPage()

This creates a page with two separate tables, one for the model :code:`Musician` and one for the model :code:`Album`.


Usage
------

See :doc:`usage`.


Running tests
-------------

You need tox installed then just :code:`make test`.


License
-------

BSD
