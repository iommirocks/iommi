


Tables
======

iommi tables makes it easy to create full featured HTML tables easily:

* generates header, rows and cells
* sorting
* filtering
* pagination
* bulk edit
* link creation
* customization on multiple levels, all the way down to templates for cells
* automatic rowspan
* grouping of headers

.. image:: tables_example_albums.png

The code for the example above:


.. code-block:: python

    Table(
        auto__model=Album,
        page_size=10,
    )


Read the full documentation and the :doc:`cookbook` for more.

    


Creating tables from models
---------------------------

Say I have some model:

.. code-block:: python

    class Foo(models.Model):
        a = models.IntegerField()

        def __str__(self):
            return f'Foo: {self.a}'


    class Bar(models.Model):
        b = models.ForeignKey(Foo, on_delete=models.CASCADE)
        c = models.CharField(max_length=255)


Now I can display a list of `Bar` in a table like this:


.. code-block:: python

    def my_view(request):
        return Table(auto__model=Bar)



This automatically creates a table with pagination and sorting. If you pass
`query_from_indexes=True` you will get filters for all the model fields
that have database indexes. This filtering system includes an advanced filter
language. See :doc:`queries` for more on filtering.





Explicit tables
---------------

You can also create tables explicitly:


.. code-block:: python

    def albums(request):
        class AlbumTable(Table):
            # Shortcut for creating checkboxes to select rows
            select = Column.select()

            name = Column()

            # Show the name field from Artist. This works for plain old objects too.
            artist_name = Column.number(
                attr='artist__name',

                # put this field into the query language
                filter__include=True,
            )
            year = Column(
                # Enable bulk editing for this field
                bulk__include=True,
            )

        return AlbumTable(rows=Album.objects.all())


This gives me a view with filtering, sorting, bulk edit and pagination.

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('aa79a80a-ad37-41fd-9ede-b1508adc4eb2', this)">▼ Hide result</div>
        <iframe id="aa79a80a-ad37-41fd-9ede-b1508adc4eb2" src="doc_includes/tables/test_explicit_tables.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


Table of plain python objects
-----------------------------


.. code-block:: python

    def plain_objs_view(request):
        # Say I have a class...
        class Foo(object):
            def __init__(self, i):
                self.a = i
                self.b = 'foo %s' % (i % 3)
                self.c = (i, 1, 2, 3, 4)

        # and a list of them
        foos = [Foo(i) for i in range(4)]

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

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('fd1162b0-13d7-45f6-8bdb-241ad190438b', this)">▼ Hide result</div>
        <iframe id="fd1162b0-13d7-45f6-8bdb-241ad190438b" src="doc_includes/tables/test_table_of_plain_python_objects.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

All these examples and a bigger example using many more features can be found in the examples project.
