.. raw:: html

    <a href="https://travis-ci.org/TriOptima/tri.table"><img alt="https://travis-ci.org/TriOptima/tri.table.svg?branch=master" src="https://camo.githubusercontent.com/e783360fe0af425d1d7bae96b55c0bb4b96d394e/68747470733a2f2f7472617669732d63692e6f72672f5472694f7074696d612f7472692e7461626c65732e7376673f6272616e63683d6d6173746572" data-canonical-src="https://travis-ci.org/TriOptima/tri.table.svg?branch=master" style="max-width:100%;"></a>


.. raw:: html

    <a href="http://codecov.io/github/TriOptima/tri.table?branch=master"><img alt="http://codecov.io/github/TriOptima/tri.table/coverage.svg?branch=master" src="https://camo.githubusercontent.com/41ddc1ad582885a328f67b5d38910b80c16e41be/687474703a2f2f636f6465636f762e696f2f6769746875622f5472694f7074696d612f7472692e7461626c65732f636f7665726167652e7376673f6272616e63683d6d6173746572" data-canonical-src="http://codecov.io/github/TriOptima/tri.table/coverage.svg?branch=master" style="max-width:100%;"></a>


tri.table
==========

tri.table is a library to make full featured HTML tables easily:

* generates header, rows and cells
* grouping of headers
* filtering
* sorting
* bulk edit
* pagination
* automatic rowspan
* link creation
* customization on multiple levels, all the way down to templates for cells

All these examples and a bigger example using many more features can be found in the examples django project.

Read the full documentation for more.

Simple example
--------------

.. literalinclude:: ../examples/examples/views.py
   :pyobject: readme_example_1

And this is what you get:

.. image:: table_example_1.png

Fancy django features
---------------------

Say I have some models:

.. literalinclude:: ../examples/examples/models.py
   :pyobject: Foo
.. literalinclude:: ../examples/examples/models.py
   :pyobject: Bar

Now I can display a list of Bars in a table like this:

.. literalinclude:: ../examples/examples/views.py
   :pyobject: readme_example_2

This gives me a view with filtering, sorting, bulk edit and pagination.

All these examples and a bigger example using many more features can be found in the examples django project.

Read the full documentation for more.


Running tests
-------------

You need tox installed then just `make test`.


License
-------

BSD


Documentation
-------------

http://tritable.readthedocs.org.
