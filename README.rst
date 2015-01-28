tri.tables
==========

tri.tables is a library to make full featured HTML tables easily.

Simple example
--------------

.. code:: python

    # Say I have a class...
    class Foo(object):
        def __init__(self, i):
            self.a = i
            self.b = 'foo'
            self.c = (1, 2, 3, 4)

    # and a list of them
    foos = [Foo(i) for i in xrange(10)]

    # I can declare a table:
    class FooTable(Table):
        a = Column.number()  # This is a shortcut that results in the css class "rj" (for right justified) being added to the header and cell
        b = Column()
        last_c = Column(cell_format value: value[-1])  # We want to show the last value of the tuple, not the entire thing

    # now to get an HTML table:
    html_table = render_table(request, FooTable(foos))

Fancy django features
---------------------

.. code:: python

    # Say I have some models:
    class Foo(models.Model):
        a = models.IntegerField()

    class Bar(models.Model):
        b = models.ForeignKey(Foo)
        c = models.CharField(max_length=255)

    # ...I can do this:
    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        b__a = Column.number()  # Show "a" from "b". This works for plain old objects too.
        c = Column(bulk=True)  # The form is created automatically

    html_table = render_table(request, BarTable(Bar.objects.all())

    # ...and now I have a paginated and sortable table with bulk editing on the "c" column!

This only scratches the surface. Some other features include:

* automatic rowspan
* filtering
* grouping of headers
* link creation
* templates for cells

Read the full documentation for more.

License
-------

BSD


Documentation
-------------

http://tritables.rtfd.org.