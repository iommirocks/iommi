iommi
=====

.. image:: https://travis-ci.org/TriOptima/iommi.svg?branch=master
    :target: https://travis-ci.org/TriOptima/iommi

.. image:: https://codecov.io/gh/TriOptima/iommi/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/TriOptima/iommi

.. image:: https://repl.it/badge/github/boxed/iommi-repl.it
    :target: https://repl.it/github/boxed/iommi-repl.it

iommi is a Django-based framework that magically create pages, forms and tables with advanced out-of-the-box functionality based on your applications models - without sacrificing flexibility and control.

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

    class IndexPage(Page):
        title = html.h1('Supernaut')
        welcome_text = 'This is a discography of the best acts in music!'

        artists = Table(auto__model=Artist, page_size=5)
        albums = Table(
            auto__model=Album,
            page_size=5,
        )
        tracks = Table(auto__model=Album, page_size=5)


    urlpatterns = [
        path('', IndexPage().as_view()),
    ]


This creates a page with three separate tables, a header and some text:

.. image:: docs/README-screenshot.png

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
