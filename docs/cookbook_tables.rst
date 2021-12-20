
Tables
------

    


How do I customize the rendering of a table?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Table rendering can be customized on multiple levels. You pass a template with the `template` argument, which
is either a template name or a `Template` object.

Customize the HTML attributes of the table tag via the `attrs` argument. See attrs_.

To customize the row, see `How do I customize the rendering of a row?`_

To customize the cell, see `How do I customize the rendering of a cell?`_


.. _Table.page_size:

    


How do you turn off pagination?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specify `page_size=None`:


.. code-block:: python

    Table(
        auto__model=Album,
        page_size=None,
    )


    class MyTable(Table):
        a = Column()

        class Meta:
            page_size = None



.. _Table.cell:

    


How do I customize the rendering of a cell?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize the :doc:`Cell` rendering in several ways:

- You can modify the html attributes via `cell__attrs`. See the question on attrs_

- Use `cell__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

- Pass a url (or callable that returns a url) to `cell__url` to make the cell a link.


    


How do I make a link in a cell?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is such a common case that there's a special case for it: pass the `url` and `url_title` parameters to the `cell`:


.. code-block:: python

    Column(
        cell__url='http://example.com',
        cell__url_title='go to example',
    )



.. _How do I create a column based on computed data?:

    


How do I create a column based on computed data (i.e. a column not based on an attribute of the row)?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we have a model like this:


.. code-block:: python

    class Foo(models.Model):
        value = models.IntegerField()


And we want a computed column `square` that is the square of the value, then we can do:


.. code-block:: python

    Table(
        auto__model=Foo,
        columns__square=Column(
            # computed value:
            cell__value=lambda row, **_: row.value * row.value,
        )
    )


or we could do:


.. code-block:: python

    Table(
        auto__model=Foo,
        columns__square=Column(
            attr='value',
            cell__format=lambda value, **_: value * value,
        )
    )


This only affects the formatting when we render the cell value. Which might make more sense depending on your situation but for the simple case like we have here the two are equivalent.


    


How do I get iommi tables to understand my Django ModelField subclasses?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :doc:`registrations`.


.. _Column.after:

    


How do I reorder columns?
~~~~~~~~~~~~~~~~~~~~~~~~~

By default the columns come in the order defined so if you have an explicit table defined, just move them around there. If the table is generated from a model definition, you can also move them in the model definition if you like, but that might not be a good idea. So to handle this case we can set the ordering on a column by giving it the `after` argument. Let's start with a simple model:


.. code-block:: python

    class Foo(models.Model):
        a = models.IntegerField()
        b = models.IntegerField()
        c = models.IntegerField()


If we just do `Table(auto__model=Foo)` we'll get the columns in the order a, b, c. But let's say I want to put c first, then we can pass it the `after` value `-1`:


.. code-block:: python

    Table(auto__model=Foo, columns__c__after=-1)


`-1` means the first, other numbers mean index. We can also put columns after another named column like so:


.. code-block:: python

    Table(auto__model=Foo, columns__c__after='a')


this will put the columns in the order a, c, b.

There is a special value `LAST` (import from `tri_declarative`) to put something last in a list.


.. _Column.filter:

    


How do I enable searching/filter on columns?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass the value `filter__include=True` to the column, to enable searching
in the advanced query language.


.. code-block:: python

    Table(
        auto__model=Album,
        columns__name__filter__include=True,
    )


The `query` namespace here is used to configure a :doc:`Filter` so you can
configure the behavior of the searching by passing parameters here.

The `filter__field` namespace is used to configure the :doc:`Field`, so here you
can pass any argument to `Field` here to customize it.

If you just want to have the filter available in the advanced query language,
you can turn off the field in the generated form by passing
`filter__field__include=False`:


.. _Filter.freetext:

    


How do I make a freetext search field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to filter based on a freetext query on one or more columns we've got a nice little feature for this:


.. code-block:: python

    Table(
        auto__model=Album,
        columns__name__filter=dict(
            freetext=True,
            include=True,
        ),
        columns__year__filter__freetext=True,
        columns__year__filter__include=True,
    )



This will display one search box to search both `year` and `name` columns.

    

.. code-block:: python

    # TODO: the code in here is no longer tested!


.. _Table.attrs:

.. _Form.attrs:

.. _Field.attrs:

.. _attrs:

How do I customize HTML attributes, CSS classes or CSS style specifications?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `attrs` namespace has special handling to make it easy to customize. There are three main cases:

First the straight forward case where a key/value pair is rendered in the output:

.. code-block:: pycon

    >>> render_attrs(Namespace(foo='bar'))
    ' foo="bar"'

Then there's a special handling for CSS classes:

.. code-block:: pycon

    >>> render_attrs(Namespace(class__foo=True, class__bar=True))
    ' class="bar foo"'

Note that the class names are sorted alphabetically on render.

Lastly there is the special handling of `style`:

.. code-block:: pycon

    >>> render_attrs(Namespace(style__font='Arial'))
    ' style="font: Arial"'

If you need to add a style with `-` in the name you have to do this:


.. code-block:: pycon

    >>> render_attrs(Namespace(**{'style__font-family': 'sans-serif'}))
    ' style="font-family: sans-serif"'


Everything together:

.. code-block:: pycon

    >>> render_attrs(
         Namespace(
             foo='bar',
             class__foo=True,
             class__bar=True,
             style__font='Arial',
             **{'style__font-family': 'serif'}
         )
     )
    ' class="bar foo" foo="bar" style="font-family: serif; font: Arial"'


.. _Table.row:

    


How do I customize the rendering of a row?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize the row rendering in two ways:

- You can modify the html attributes via `row__attrs`. See the question on attrs_

- Use `row__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

In templates you can access the raw row via `row`. This would typically be one of your model objects. You can also access the cells of the table via `cells`. A naive template for a row would be `<tr>{% for cell in cells %}<td>{{ cell }}{% endfor %}</tr>`. You can access specific cells by their column names like `{{ cells.artist }}`.

To customize the cell, see `How do I customize the rendering of a cell?`_

.. _Column.header:

    


How do I customize the rendering of a header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize headers in two ways:

- You can modify the html attributes via `header__attrs`. See the question on attrs_

- Use `header__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object. The default is `iommi/table/table_header_rows.html`.


.. _Table.header:

    


How do I turn off the header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set `header__template` to `None`.


    


How do I add fields to a table that is generated from a model?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See the question `How do I create a column based on computed data?`_


.. _Column.include:

    


How do I specify which columns to show?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Just pass `include=False` to hide the column or `include=True` to show it. By default columns are shown, except the primary key column that is by default hidden. You can also pass a callable here like so:


.. code-block:: python

    Table(
        auto__model=Album,
        columns__name__include=
            lambda request, **_: request.GET.get('some_parameter') == 'hello!',
    )


This will show the column `name` only if the GET parameter `some_parameter` is set to `hello!`.

To be more precise, `include` turns off the entire column. Sometimes you want to have the searching turned on, but disable the rendering of the column. To do this use the `render_column` parameter instead.


.. _Table.cells_for_rows:

    


How do I access table data programmatically (like for example to dump to json)?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's a simple example that prints a table to stdout:


.. _Column.attr:

    


How do I access foreign key related data in a column?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say we have two models:


.. code-block:: python

    class Foo(models.Model):
        a = models.IntegerField()


we can build a table of `Bar` that shows the data of `a` like this:


.. code-block:: python

    Table(
        auto__model=Bar,
        columns__a=Column(attr='c__a'),
    )


.. _Table.sortable:

.. _Column.sortable:

    


How do I turn off sorting? (on a column or table wide)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To turn off column on a column pass it `sortable=False` (you can also use a lambda here!):


.. code-block:: python

    Table(
        auto__model=Album,
        columns__name__sortable=False,
    )


and to turn it off on the entire table:


.. code-block:: python

    Table(
        auto__model=Album,
        sortable=False,
    )


.. _Column.display_name:

    


How do I specify the title of a header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `display_name` property of a column is displayed in the header.


.. code-block:: python

    Table(
        auto__model=Album,
        columns__name__display_name='header title',
    )


.. _Column.sort_default_desc:

    


How do I set the default sort order of a column to be descending instead of ascending?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: python

    Table(
        auto__model=Album,
        columns__name__sort_default_desc=True,  # or a lambda!
    )



.. _Column.group:

    


How do I group columns?
~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: python

    Table(
        auto__model=Album,
        columns__name__group='foo',
        columns__year__group='foo',
    )


The grouping only works if the columns are next to each other, otherwise you'll get multiple groups. The groups are rendered by default as a second header row above the normal header row with colspans to group the headers.


.. _Column.auto_rowspan:

    


How do I get rowspan on a table?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can manually set the rowspan attribute via `row__attrs__rowspan` but this is tricky to get right because you also have to hide the cells that are "overwritten" by the rowspan. We supply a simpler method: `auto_rowspan`. It automatically makes sure the rowspan count is correct and the cells are hidden. It works by checking if the value of the cell is the same, and then it becomes part of the rowspan.


.. code-block:: python

    Table(
        auto__model=Album,
        columns__year__auto_rowspan=True,
    )



.. _Column.bulk:

    


How do I enable bulk editing?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Editing multiple items at a time is easy in iommi with the built in bulk
editing. Enable it for a columns by passing `bulk__include=True`:


.. code-block:: python

    Table(
        auto__model=Album,
        columns__select__include=True,
        columns__year__bulk__include=True,
    )


The bulk namespace here is used to configure a `Field` for the GUI so you
can pass any parameter you can pass to `Field` there to customize the
behavior and look of the bulk editing for the column.

You also need to enable the select column, otherwise you can't select
the columns you want to bulk edit.


.. _Table.bulk:

    


How do I enable bulk delete?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


.. code-block:: python

    Table(
        auto__model=Album,
        columns__select__include=True,
        bulk__actions__delete__include=True,
    )


To enable the bulk delete, enable the `delete` action.

You also need to enable the select column, otherwise you can't select
the columns you want to delete.


    


How do I make a custom bulk action?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need to first show the select column by passing
`columns__select__include=True`, then define a submit `Action` with a post
handler:


.. code-block:: python

    def my_action_post_handler(table, request, **_):
        queryset = table.bulk_queryset()
        queryset.update(name='Paranoid')
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    t = Table(
        auto__model=Album,
        columns__select__include=True,
        bulk__actions__my_action=Action.submit(
            post_handler=my_action_post_handler,
        )
    )


What is the difference between `attr` and `_name`?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`attr` is the attribute path of the value iommi reads from a row. In the simple case it's just the attribute name, but if you want to read the attribute of an attribute you can use `__`-separated paths for this: `attr='foo__bar'` is functionally equivalent to `cell__value=lambda row, **_: row.foo.bar`. Set `attr` to `None` to not read any attribute from the row.

`_name` is the name used internally. By default `attr` is set to the value of `_name`. This name is used when accessing the column from `Table.columns` and it's the name used in the GET parameter to sort by that column. This is a required field.
