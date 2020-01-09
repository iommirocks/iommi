Tables FAQ
==========


How do I customize the rendering of a table?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Table rendering can be customized on multiple levels. You pass a template with the `template` argument, which
is either a template name or a `Template` object.

Customize the HTML attributes of the table tag via the `attrs` argument. See attrs_.

To customize the row, see `How do I customize the rendering of a row?`_

To customize the cell, see `How do I customize the rendering of a cell?`_


How do you turn off pagination?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specify `paginate_by=None`:

.. code:: python

    Table.from_model(
        model=Foo,
        paginate_by=None,
    )

.. code:: python

    class MyTable(Table):
        a = Column()

        class Meta:
            paginate_by = None


.. _How do I create a column based on computed data?:

How do I create a column based on computed data (aka a column not based on an attribute of the row)?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we have a model like this:

.. code:: python

    class Foo(models.Model):
        value = models.IntegerField()

And we want a computed column `square` that is the square of the value, then we can do:

.. code:: python

    Table.from_model(
        model=Foo,
        extra_fields=[
            Column(
                name='square',
                # computed value:
                cell__value=lambda row, **_: row.value * row.value,
            )
        ]
    )

or we could do:

.. code:: python

    Column(
        name='square',
        attr='value',
        cell__format=lambda value, **: value * value,
    )

This only affects the formatting when we render the cell value. Which might make more sense depending on your situation but for the simple case like we have here the two are equivalent.

How do I get tri.table to understand my Django ModelField subclasses?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You use the `tri_table.db_compat.register_column_factory` function to register your own factory. We can look at the pre-registered factories to understand how to make your own:

.. code:: python

    register_column_factory(
        TimeField,
        Shortcut(call_target__attribute='time')
    )

This registers the a factory that, when it sees a django `TimeField` will call the `Column.time` shortcut to create a column.

How do I reorder columns?
~~~~~~~~~~~~~~~~~~~~~~~~~

By default the columns come in the order defined so if you have an explicit table defined, just move them around there. If the table is generated from a model definition, you can also move them in the model definition if you like, but that might not be a good idea. So to handle this case we can set the ordering on a column by giving it the `after` argument. Let's start with a simple model:

.. code:: python

    class Foo(models.Model):
        a = models.IntegerField()
        b = models.IntegerField()
        c = models.IntegerField()

If we just do `Table.from_model(model=Foo)` we'll get the columns in the order a, b, c. But let's say I want to put c first, then we can pass it the `after` value -1:

.. code:: python

    Table.from_model(model=Foo, column__c__after=-1)

-1 means the first, other numbers mean index. We can also put columns after another named column like so:

.. code:: python

    Table.from_model(model=Foo, column__c__after='a')

this will put the columns in the order a, c, b.

How do I enable searching/filter on columns?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass the value `query__show=True` to the column, to enable searching in the advanced query language. To also get searching for the column in the simple GUI filtering also pass `query__gui__show=True`:

.. code:: python

    Table.from_model(
        model=Foo,
        column__a__query__show=True,
        column__a__query__gui__show=True,
    )

.. _attrs:

How do I customize HTML attributes, CSS classes or CSS style specifications?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `attrs` namespace has special handling to make it easy to customize. There are three main cases:

First the straight forward case where a key/value pair is rendered in the output:

.. code:: python

    >>> render_attrs(Namespace(foo='bar'))
    ' foo="bar"'

Then there's a special handling for CSS classes:

.. code:: python

    >>> render_attrs(Namespace(class__foo=True, class__bar=True))
    ' class="bar foo"'

Note that the class names are sorted alphabetically on render.

Lastly there is the special handling of `style`:

.. code:: python

    >>> render_attrs(Namespace(style__font='Arial'))
    ' style="font: Arial"'

If you need to add a style with `-` in the name you have to do this:


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

- You can modify the html attributes via `cell__attrs`. See the question on attrs_

- Use `cell__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

How do I customize the rendering of a row?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize the row rendering in two ways:

- You can modify the html attributes via `row__attrs`. See the question on attrs_

- Use `row__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

How do I customize the rendering of a header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize headers in two ways:

- You can modify the html attributes via `header__attrs`. See the question on attrs_

- Use `header__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object. The default is `tri_table/table_header_rows.html`.

How do I turn off the header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set `header_template` to `None`.

How do I add fields to a table that is generated from a model?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See the question `How do I create a column based on computed data?`_

How do I specify which columns to show?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Just pass `show=False` to hide the column or `show=True` to show it. By default columns are shown, except the primary key column that is by default hidden. You can also pass a callable here like so:

.. code:: python

    Table.from_model(
        model=Foo,
        column__a__show=lambda table, **_: table.request.GET.get('some_parameter') == 'hello!',
    )

This will show the column `a` only if the GET parameter `some_parameter` is set to `hello!`.

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

This is such a common case that there's a special case for it: pass the `url` and `url_title` parameters:

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

we can build a table of `Bar` that shows the data of `a` like this:

.. code:: python

    Table.from_model(
        model=Bar,
        extra_fields=[
            Column.from_model(name='c__a'),
        ],
    )

How do I turn off sorting? (on a column or table wide)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To turn off column on a column pass it `sortable=False` (you can also use a lambda here!):

.. code:: python

    Table.from_model(
        model=Foo,
        column__a__sortable=False,
    )

and to turn it off on the entire table:

.. code:: python

    Table.from_model(
        model=Foo,
        sortable=False,
    )

How do I specify the title of a header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `display_name` property of a column is displayed in the header.

.. code:: python

    Table.from_model(
        model=Foo,
        column__a__display_name='header title',
    )

How do I set the default sort order of a column to be descending instead of ascending?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    Table.from_model(
        model=Foo,
        column__a__sort_default_desc=True,  # or a lambda!
    )


How do I group columns?
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    Table.from_model(
        model=Foo,
        column__a__group='foo',
        column__b__group='foo',
    )

The grouping only works if the columns are next to each other, otherwise you'll get multiple groups. The groups are rendered by default as a second header row above the normal header row with colspans to group the headers.


How do I get rowspan on a table?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can manually set the rowspan attribute via `row__attrs__rowspan` but this is tricky to get right because you also have to hide the cells that are "overwritten" by the rowspan. We supply a simpler method: `auto_rowspan`. It automatically makes sure the rowspan count is correct and the cells are hidden. It works by checking if the value of the cell is the same, and then it becomes part of the rowspan.

.. code:: python

    Table.from_model(
        model=Foo,
        column__a__auto_rowspan=True,
    )

How do I make a freetext search field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to filter based on a freetext query on one or more columns we've got a nice little feature for this:

.. code:: python

    Table.from_model(
        model=Foo,
        column__a__query__freetext=True,
        column__b__query__freetext=True,
    )

(You don't need to enable querying with `column__b__query__show=True` first)

What is the difference between `attr` and `name`?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`attr` is the attribute path of the value tri.table reads from a row. In the simple case it's just the attribute name, but if you want to read the attribute of an attribute you can use `__`-separated paths for this: `attr='foo__bar'` is functionally equivalent to `cell__value=lambda row, **_: row.foo.bar`. Set `attr` to None to not read any attribute from the row.

`name` is the name used internally. By default `attr` is set to the value of `name`. This name is used when accessing the column from `Table.column_by_name` and it's the name used in the GET parameter to sort by that column. This is a required field.
