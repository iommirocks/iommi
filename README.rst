.. image:: https://travis-ci.org/TriOptima/tri.tables.svg?branch=master
    :target: https://travis-ci.org/TriOptima/tri.tables

tri.tables
==========

tri.tables is a library to make full featured HTML tables easily.

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
            c = Column(cell_format=lambda value: value[-1])  # Display the last value of the tuple
            sum_c = Column(cell_value=lambda row: sum(row.c), sortable=False)  # Calculate a value not present in Foo

        # now to get an HTML table:
        return render_table_to_response(request, FooTable(foos), template_name='base.html')

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
            b__a = Column.number()  # Show "a" from "b". This works for plain old objects too.
            c = Column(bulk=True)  # The form is created automatically

        return render_table_to_response(request, BarTable(Bar.objects.all()), template_name='base.html', paginate_by=20)

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
