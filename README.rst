.. raw:: html

    <p class="mobile-logo" align="center"><a href="#"><img class="logo" src="https://raw.githubusercontent.com/TriOptima/iommi/master/logo_with_outline.svg" alt="iommi" style="max-width: 200px" width=300></a></p>

    <h3 class="pun">Your first pick for a django power cord</h3>

.. image:: https://github.com/TriOptima/iommi/workflows/tests/badge.svg
    :target: https://github.com/TriOptima/iommi/actions?query=workflow%3Atests+branch%3Amaster

.. image:: https://codecov.io/gh/TriOptima/iommi/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/TriOptima/iommi

.. image:: https://repl.it/badge/github/boxed/iommi-repl.it
    :target: https://repl.it/github/boxed/iommi-repl.it

.. image:: https://img.shields.io/discord/773470009795018763
    :target: https://discord.gg/ZyYRYhf7Pd


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

You need to have tox installed then:

.. code::

    make venv
    source env/bin/activate
    make test
    make test-docs


License
-------

BSD


Documentation
-------------

https://docs.iommi.rocks
