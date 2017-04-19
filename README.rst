.. image:: https://travis-ci.org/TriOptima/tri.table.svg?branch=master
    :target: https://travis-ci.org/TriOptima/tri.table


.. image:: https://codecov.io/github/TriOptima/tri.table/coverage.svg?branch=master
    :target: https://codecov.io/github/TriOptima/tri.table?branch=master


tri.table
=========

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

.. contents::

Simple example
--------------

.. code:: python

    def readme_example_1(request):
        # Say I have a class...
        class Foo(object):
            def __init__(self, i):
                self.a = i
                self.b = 'foo %s' % (i % 3)
                self.c = (i, 1, 2, 3, 4)

        # and a list of them
        foos = [Foo(i) for i in xrange(4)]

        # I can declare a table:
        class FooTable(Table):
            a = Column.number()  # This is a shortcut that results in the css class "rj" (for right justified) being added to the header and cell
            b = Column()
            c = Column(cell__format=lambda table, column, row, value, **_: value[-1])  # Display the last value of the tuple
            sum_c = Column(cell__value=lambda table, column, row, **_: sum(row.c), sortable=False)  # Calculate a value not present in Foo

        # now to get an HTML table:
        return render_table_to_response(request, FooTable(data=foos), template='base.html')

And this is what you get:

.. image:: table_example_1.png

Fancy django features
---------------------

Say I have some models:

.. code:: python

    class Foo(models.Model):
        a = models.IntegerField()

        def __unicode__(self):
            return 'Foo: %s' % self.a
.. code:: python

    class Bar(models.Model):
        b = models.ForeignKey(Foo)
        c = models.CharField(max_length=255)

Now I can display a list of Bars in a table like this:

.. code:: python

    def readme_example_2(request):
        fill_dummy_data()

        class BarTable(Table):
            select = Column.select()  # Shortcut for creating checkboxes to select rows
            b__a = Column.number(  # Show "a" from "b". This works for plain old objects too.
                query__show=True,  # put this field into the query language
                query__gui__show=True)  # put this field into the simple filtering GUI
            c = Column(
                bulk=True,  # Enable bulk editing for this field
                query_show=True,
                query__gui__show=True)

        return render_table_to_response(request, BarTable(data=Bar.objects.all()), template='base.html', paginate_by=20)

This gives me a view with filtering, sorting, bulk edit and pagination.

All these examples and a bigger example using many more features can be found in the examples django project.

Read the full documentation for more.

Usage
-----

Add tri.form, tri.query, tri.table to INSTALLED_APPS.

Motivation
----------

tri.table grew out of a frustration with how tables were created at TriOptima. We have a /lot/ of tables and the code to produce them included long HTML templates and often the code to extract and massage the data in some trivial way ended up as methods on the model classes or template tags, even though it was only used by one view.

This code was also error prone to change since we often have columns that we show or hide based on the permissions of the user, which meant the `thead` and `tbody` had to be in sync. When you have a lot of columns and more and more complex logic for when to show/hide columns this can become harder than it sounds!

We also saw that almost always the names of the columns (aka the headers) could be derived from the name of the field they should display data for, so we opted for defaults to make this case easier.

It was very important for us to have customization available at many levels. Many table libraries have really nice and short code for the default case but when you have to customize some tiny thing you have to rewrite huge swaths of the library's code. We didn't want to do that since we made this library in order to refactor out exactly this thing from our existing code base. We ended up with the powerful pattern of being able to supply callables for the points of customization, leading to small tweaks moving into the table definition instead of being scattered in model or template tag code. We also have many levels or customization so that the path from "just display columns x, y and z somehow" to heavy customization is smooth and gradual.

We chose to mimic how django forms and models are declared because we really like that kind of declarative style, but you can also use it in a more functional style if you want. The latter is useful when you want to create a list of the columns to display programmatically for example.

This library has been a big win for us. The time to create a page with a table on it has been drastically reduced without sacrificing any flexibility when we later want to tweak the view.

Running tests
-------------

You need tox installed then just `make test`.


License
-------

BSD


Documentation
-------------

https://tritable.readthedocs.org.
