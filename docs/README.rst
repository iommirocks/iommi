.. image:: https://travis-ci.org/TriOptima/tri.tables.svg?branch=master
    :target: https://travis-ci.org/TriOptima/tri.tables

tri.tables
==========

tri.tables is a library to make full featured HTML tables easily.

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

This gives me a view with filtering, sorting, bulk edit and pagination and this only scratches the surface. Some other features include:

* automatic rowspan
* filtering
* grouping of headers
* link creation
* templates for cells

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

http://tritables.readthedocs.org.
