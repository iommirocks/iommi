Tables FAQ
==========


How do I customize the rendering of a table?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Table rendering can be customized on multiple levels. You pass a template with the :code:`template` argument, which
is either a template name or a :code:`Template` object.

Customize the HTML attributes of the table tag via the :code:`attrs` argument. See attrs_.

To customize the row, see `How do I customize the rendering of a row?`_

To customize the cell, see `How do I customize the rendering of a cell?`_


How do you turn off pagination?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specify :code:`paginate_by=None`:

.. code:: python

    Table.from_model(
        model=Foo,
        page_size=None,
    )

.. code:: python

    class MyTable(Table):
        a = Column()

        class Meta:
            page_size = None


.. _How do I create a column based on computed data?:

How do I create a column based on computed data (i.e. a column not based on an attribute of the row)?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we have a model like this:

.. code:: python

    class Foo(models.Model):
        value = models.IntegerField()

And we want a computed column `square` that is the square of the value, then we can do:

.. code:: python

    Table.from_model(
        model=Foo,
        extra_fields=dict(
            square=Column(
                # computed value:
                cell__value=lambda row, **_: row.value * row.value,
            )
        )
    )

or we could do:

.. code:: python

    Column(
        name='square',
        attr='value',
        cell__format=lambda value, **: value * value,
    )

This only affects the formatting when we render the cell value. Which might make more sense depending on your situation but for the simple case like we have here the two are equivalent.

How do I get iommi tables to understand my Django ModelField subclasses?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :doc:`registrations`.

How do I reorder columns?
~~~~~~~~~~~~~~~~~~~~~~~~~

By default the columns come in the order defined so if you have an explicit table defined, just move them around there. If the table is generated from a model definition, you can also move them in the model definition if you like, but that might not be a good idea. So to handle this case we can set the ordering on a column by giving it the :code:`after` argument. Let's start with a simple model:

.. code:: python

    class Foo(models.Model):
        a = models.IntegerField()
        b = models.IntegerField()
        c = models.IntegerField()

If we just do :code:`Table.from_model(model=Foo)` we'll get the columns in the order a, b, c. But let's say I want to put c first, then we can pass it the :code:`after` value :code:`-1`:

.. code:: python

    Table.from_model(model=Foo, columns__c__after=-1)

:code:`-1` means the first, other numbers mean index. We can also put columns after another named column like so:

.. code:: python

    Table.from_model(model=Foo, columns__c__after='a')

this will put the columns in the order a, c, b.

There is a special value `LAST` (import from `tri_declarative`) to put something last in a list.

How do I enable searching/filter on columns?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass the value :code:`query__include=True` to the column, to enable searching in the advanced query language. To also get searching for the column in the simple GUI filtering also pass :code:`query__form__include=True`:

.. code:: python

    Table.from_model(
        model=Foo,
        columns__a__query__include=True,
        columns__a__query__form__include=True,
    )

.. _attrs:

How do I customize HTML attributes, CSS classes or CSS style specifications?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :code:`attrs` namespace has special handling to make it easy to customize. There are three main cases:

First the straight forward case where a key/value pair is rendered in the output:

.. code:: python

    >>> render_attrs(Namespace(foo='bar'))
    ' foo="bar"'

Then there's a special handling for CSS classes:

.. code:: python

    >>> render_attrs(Namespace(class__foo=True, class__bar=True))
    ' class="bar foo"'

Note that the class names are sorted alphabetically on render.

Lastly there is the special handling of :code:`style`:

.. code:: python

    >>> render_attrs(Namespace(style__font='Arial'))
    ' style="font: Arial"'

If you need to add a style with :code:`-` in the name you have to do this:


.. code:: python

    >>> render_attrs(Namespace(**{'style__font-family': 'sans-serif'}))
    ' style="font-family: sans-serif"'


Everything together:

.. code:: python

    >>> render_attrs(
    ...     Namespace(
    ...         foo='bar',
    ...         class__foo=True,
    ...         class__bar=True,
    ...         style__font='Arial',
    ...         **{'style__font-family': 'serif'}
    ...     )
    ... )
    ' class="bar foo" foo="bar" style="font-family: serif; font: Arial"'

How do I customize the rendering of a cell?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize the row rendering in two ways:

- You can modify the html attributes via :code:`cell__attrs`. See the question on attrs_

- Use :code:`cell__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a :code:`Template` object.

How do I customize the rendering of a row?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize the row rendering in two ways:

- You can modify the html attributes via :code:`row__attrs`. See the question on attrs_

- Use :code:`row__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a :code:`Template` object.

How do I customize the rendering of a header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize headers in two ways:

- You can modify the html attributes via :code:`header__attrs`. See the question on attrs_

- Use :code:`header__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a :code:`Template` object. The default is :code:`iommi/table/table_header_rows.html`.

How do I turn off the header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set :code:`header_template` to :code:`None`.

How do I add fields to a table that is generated from a model?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See the question `How do I create a column based on computed data?`_

How do I specify which columns to show?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Just pass :code:`include=False` to hide the column or :code:`include=True` to show it. By default columns are shown, except the primary key column that is by default hidden. You can also pass a callable here like so:

.. code:: python

    Table.from_model(
        model=Foo,
        columns__a__include=lambda table, **_: table.request().GET.get('some_parameter') == 'hello!',
    )

This will show the column :code:`a` only if the GET parameter :code:`some_parameter` is set to `hello!`.

To be more precise, :code:`include` turns off the entire column. Sometimes you want to have the searching turned on, but disable the rendering of the column. To do this use the :code:`render_column` parameter instead.

How do I access table data programmatically (like for example to dump to json)?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's a simple example that prints a table to stdout:

.. code:: python

    for row in table:
        for cell in row:
            print(cell.render_formatted(), end='')
        print()

How do I make a link in a cell?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is such a common case that there's a special case for it: pass the :code:`url` and :code:`url_title` parameters:

.. code:: python

    Column(
        name='foo',
        url='http://example.com',
        url_title='go to example',
    )

How do I access foreign key related data in a column?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we have two models:

.. code:: python

    class Foo(models.Model):
        a = models.IntegerField()

    class Bar(models.Model):
        b = models.IntegerField()
        c = models.ForeignKey(Foo)

we can build a table of :code:`Bar` that shows the data of `a` like this:

.. code:: python

    Table.from_model(
        model=Bar,
        extra_fields=dict(
            c__a=Column.from_model,
        ),
    )

How do I turn off sorting? (on a column or table wide)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To turn off column on a column pass it :code:`sortable=False` (you can also use a lambda here!):

.. code:: python

    Table.from_model(
        model=Foo,
        columns__a__sortable=False,
    )

and to turn it off on the entire table:

.. code:: python

    Table.from_model(
        model=Foo,
        sortable=False,
    )

How do I specify the title of a header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :code:`display_name` property of a column is displayed in the header.

.. code:: python

    Table.from_model(
        model=Foo,
        columns__a__display_name='header title',
    )

How do I set the default sort order of a column to be descending instead of ascending?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    Table.from_model(
        model=Foo,
        columns__a__sort_default_desc=True,  # or a lambda!
    )


How do I group columns?
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    Table.from_model(
        model=Foo,
        columns__a__group='foo',
        columns__b__group='foo',
    )

The grouping only works if the columns are next to each other, otherwise you'll get multiple groups. The groups are rendered by default as a second header row above the normal header row with colspans to group the headers.


How do I get rowspan on a table?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can manually set the rowspan attribute via :code:`row__attrs__rowspan` but this is tricky to get right because you also have to hide the cells that are "overwritten" by the rowspan. We supply a simpler method: :code:`auto_rowspan`. It automatically makes sure the rowspan count is correct and the cells are hidden. It works by checking if the value of the cell is the same, and then it becomes part of the rowspan.

.. code:: python

    Table.from_model(
        model=Foo,
        columns__a__auto_rowspan=True,
    )

How do I make a freetext search field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to filter based on a freetext query on one or more columns we've got a nice little feature for this:

.. code:: python

    Table.from_model(
        model=Foo,
        columns__a__query__freetext=True,
        columns__b__query__freetext=True,
    )

(You don't need to enable querying with :code:`columns__b__query__include=True` first)

What is the difference between `attr` and `name`?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:code:`attr` is the attribute path of the value iommi reads from a row. In the simple case it's just the attribute name, but if you want to read the attribute of an attribute you can use :code:`__`-separated paths for this: :code:`attr='foo__bar'` is functionally equivalent to :code:`cell__value=lambda row, **_: row.foo.bar`. Set :code:`attr` to :code:`None` to not read any attribute from the row.

:code:`name` is the name used internally. By default :code:`attr` is set to the value of :code:`name`. This name is used when accessing the column from :code:`Table.columns` and it's the name used in the GET parameter to sort by that column. This is a required field.
