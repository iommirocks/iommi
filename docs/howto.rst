HOWTO
=====

Forms
-----

How do I supply a custom parser for a field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable to the `parse` member of the field:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__parse=
            lambda field, string_value, **_: int(string_value),
    )

How do I make a field non-editable?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable or `bool` to the `editable` member of the field:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__editable=
            lambda field, form, **_: form.request().user.is_staff,
        fields__bar__editable=False,
    )

How do I make an entire form non-editable?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a very common case so there's a special syntax for this: pass a `bool` to the form:

.. code:: python

    form = Form.from_model(
        model=Foo,
        editable=False,
    )

How do I supply a custom validator?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable that has the arguments `form`, `field`, and `parsed_data`. Return a tuple `(is_valid, 'error message if not valid')`.

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__is_valid=
            lambda form, field, parsed_data: (False, 'invalid!'),
    )

How do I exclude a field?
~~~~~~~~~~~~~~~~~~~~~~~~~

See `How do I say which fields to include when creating a form from a model?`_

How do I say which fields to include when creating a form from a model?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Form.from_model()` has four methods to select which fields are included in the final form:

1. the `include` parameter: this is a list of strings for members of the model to use to generate the form.
2. the `exclude` parameter: the inverse of `include`. If you use this the form gets all the fields from the model excluding the ones with names you supply in `exclude`.
3. for more advanced usages you can also pass the `include` parameter to a specific field like `fields__my_field__include=True`. Here you can supply either a `bool` or a callable like `fields__my_field__include=lambda form, field, **_: form.request().user.is_staff`.
4. you can also add fields that are not present in the model with the `extra_fields`. This is a `dict` from name to either a `Field` instance or a `dict` containing a definition of how to create a `Field`.


How do I supply a custom initial value?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a value or callable to the `initial` member:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__initial=7,
        fields__bar__initial=lambda field, form, **_: 11,
    )

If there are `GET` parameters in the request, iommi will use them to fill in the appropriate fields. This is very handy for supplying links with partially filled in forms from just a link on another part of the site.


How do I set if a field is required?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Normally this will be handled automatically by looking at the model definition, but sometimes you want a form to be more strict than the model. Pass a `bool` or a callable to the `required` member:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__required=True,
        fields__bar__required=lambda field, form, **_: True,
    )



How do I change the order of the fields?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can change the order in your model definitions as this is what iommi uses. If that's not practical you can use the `after` member. It's either the name of a field or an index. There is a special value `LAST` to put a field last.

.. code:: python

    from tri_declarative import LAST

    form = Form.from_model(
        model=Foo,
        fields__baz__after=LAST,
        fields__bar__after='foo',
        fields__foo__after=0,
    )

This will make the field order foo, bar, baz.

If there are multiple fields with the same index or name the order of the fields will be used to disambiguate.


How do I insert a CSS class or HTML attribute?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `attrs` namespace on `Field`, `Form`, `Header`, `Cell` and more is used to customize HTML attributes.

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__attrs__foo='bar',
        fields__bar__after__class__bar=True,
        fields__bar__after__style__baz='qwe,
    )

or more succinctly:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__attrs=dict(
            foo='bar',
            class__bar=True,
            style__baz='qwe,
        )
    )


The thing to remember is that the basic namespace is a dict with key value
pairs that gets projected out into the HTML, but there are two special cases
for `style` and `class`. The example above will result in the following
attributes on the field tag:

.. code:: html

   <div foo="bar" class="bar" style="baz: qwe">

The values in these dicts can be callables:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__bar__after__class__bar=
            lambda form, **_: form.request().user.is_staff,
    )


How do I override rendering of an entire field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a template name or a `Template` object:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__bar__template='my_template.html',
        fields__bar__template=Template('{{ field.attrs }}'),
    )


How do I override rendering of the input field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Pass a template name or a `Template` object to the `input` namespace:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__bar__input__template='my_template.html',
        fields__bar__input__template=Template('{{ field.attrs }}'),
    )


Tables
------


How do I customize the rendering of a table?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Table rendering can be customized on multiple levels. You pass a template with the :code:`template` argument, which
is either a template name or a :code:`Template` object.

Customize the HTML attributes of the table tag via the :code:`attrs` argument. See attrs_.

To customize the row, see `How do I customize the rendering of a row?`_

To customize the cell, see `How do I customize the rendering of a cell?`_


How do you turn off pagination?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specify `page_size=None`:

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
        extra_columns=dict(
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
        columns__a__include=
            lambda table, **_: table.request().GET.get('some_parameter') == 'hello!',
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
        extra_columns=dict(
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
