Tables
======

iommi tables makes it easy to create full featured HTML tables easily:

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

Read the full documentation and the :doc:`howto` for more.

.. contents::
    :local:


Creating tables from models
---------------------------

Say I have some models:

.. code:: python

    class Foo(models.Model):
        a = models.IntegerField()

        def __str__(self):
            return 'Foo: %s' % self.a

    class Bar(models.Model):
        b = models.ForeignKey(Foo)
        c = models.CharField(max_length=255)

Now I can display a list of `Bar` in a table like this:

.. code:: python

    def my_view(request):
        return Table(auto__model=Bar)

This automatically creates a table with pagination and sorting. If you pass
`query_from_indexes=True` you will get filters for all the model fields
that have database indexes. This filtering system includes an advanced filter
language. See :doc:`queries` for more on filtering.


Explicit tables
---------------

You can also create tables explicitly:

.. code:: python

    def readme_example_2(request):
        fill_dummy_data()

        class BarTable(Table):
            # Shortcut for creating checkboxes to select rows
            select = Column.select()

            # Show "a" from "b". This works for plain old objects too.
            a = Column.number(
                attr='b__a',

                # put this field into the query language
                query__include=True,

                # put this field into the simple filtering GUI
                query__form__include=True,
            )
            c = Column(
                # Enable bulk editing for this field
                bulk=True,
                query__include=True,
                query__form__include=True,
            )

        return BarTable(rows=Bar.objects.all())

This gives me a view with filtering, sorting, bulk edit and pagination.


Table of plain python objects
-----------------------------

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
            a = Column.number()

            b = Column()

            # Display the last value of the tuple
            c = Column(
                cell__format=lambda value, **_: value[-1],
            )

            # Calculate a value not present in Foo
            sum_c = Column(
                cell__value=lambda row, **_: sum(row.c),
                sortable=False,
            )

        # now to get an HTML table:
        return FooTable(rows=foos)

And this is what you get:

.. image:: table_example_1.png

All these examples and a bigger example using many more features can be found in the examples django project.

Read the full documentation for more.
