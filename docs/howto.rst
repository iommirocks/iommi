HOWTO
=====

.. contents::
    :local:

General
-------


How do I find the path to a parameter?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Navigating the namespaces can sometimes feel a bit daunting. To help with
this iommi has a special debug mode that can help a lot. By default it's
set to settings.DEBUG, but to set it explicitly put this in your settings:

.. code:: python

    IOMMI_DEBUG = True

Now iommi will output `data-iommi-path` attributes in the HTML that will
help you find the path to stuff to configure. E.g. in the kitchen
sink table example a cell looks like this:

.. code:: html

    <td data-iommi-path="columns__e__cell">explicit value</td>

To customize this cell you can pass for example
`columns__e__cell__format=lambda value, **_: value.upper()`. See below for
many more examples.

Another nice way to find what is available is to append `?/debug_tree` in the
url of your view. You will get a table of available paths with the ajax
endpoint path, and their types with links to the appropriate documentation.


If `IOMMI_DEBUG` is on you will also get two links on the top of your pages
called `Code` and `Tree`. Code will jump to the code for the current view
in PyCharm. You can configure the URL builder to make it open your favored
editor by setting `IOMMI_DEBUG_URL_BUILDER` in settings:

.. code:: python

    IOMMI_DEBUG_URL_BUILDER = lambda filename, lineno: f'my_editor://{filename}:{lineno}'

The `Tree` link will open the `?/debug_tree` page mentioned above.


Forms
-----

How do I supply a custom parser for a field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable to the `parse_query_string` member of the field:

.. code:: python

    form = Form(
        auto__model=Foo,
        fields__foo__parse=
            lambda field, string_value, **_: int(string_value),
    )

How do I make a field non-editable?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable or `bool` to the `editable` member of the field:

.. code:: python

    form = Form(
        auto__model=Foo,
        fields__foo__editable=
            lambda request, **_: request.user.is_staff,
        fields__bar__editable=False,
    )

How do I make an entire form non-editable?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a very common case so there's a special syntax for this: pass a `bool` to the form:

.. code:: python

    form = Form(
        auto__model=Foo,
        editable=False,
    )

How do I supply a custom validator?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable that has the arguments `form`, `field`, and `parsed_data`. Return a tuple `(is_valid, 'error message if not valid')`.

.. code:: python

    form = Form(
        auto__model=Foo,
        fields__foo__is_valid=
            lambda form, field, parsed_data: (False, 'invalid!'),
    )

How do I exclude a field?
~~~~~~~~~~~~~~~~~~~~~~~~~

See `How do I say which fields to include when creating a form from a model?`_

How do I say which fields to include when creating a form from a model?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Form()` has four methods to select which fields are included in the final form:

1. the `auto__include` parameter: this is a list of strings for members of the model to use to generate the form.
2. the `auto__exclude` parameter: the inverse of `include`. If you use this the form gets all the fields from the model excluding the ones with names you supply in `exclude`.
3. for more advanced usages you can also pass the `include` parameter to a specific field like `fields__my_field__include=True`. Here you can supply either a `bool` or a callable like `fields__my_field__include=lambda request, **_: request.user.is_staff`.
4. you can also add fields that are not present in the model by passing configuration like `fields__foo__attr='bar__baz` (this means create a `Field` called `foo` that reads its data from `bar.baz`). You can either pass configuration data like that, or pass an entire `Field` instance.


How do I supply a custom initial value?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a value or callable to the `initial` member:

.. code:: python

    form = Form(
        auto__model=Foo,
        fields__foo__initial=7,
        fields__bar__initial=lambda field, form, **_: 11,
    )

If there are `GET` parameters in the request, iommi will use them to fill in the appropriate fields. This is very handy for supplying links with partially filled in forms from just a link on another part of the site.


How do I set if a field is required?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Normally this will be handled automatically by looking at the model definition, but sometimes you want a form to be more strict than the model. Pass a `bool` or a callable to the `required` member:

.. code:: python

    form = Form(
        auto__model=Foo,
        fields__foo__required=True,
        fields__bar__required=lambda field, form, **_: True,
    )



How do I change the order of the fields?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can change the order in your model definitions as this is what iommi uses. If that's not practical you can use the `after` member. It's either the name of a field or an index. There is a special value `LAST` to put a field last.

.. code:: python

    from tri_declarative import LAST

    form = Form(
        auto__model=Foo,
        fields__baz__after=LAST,
        fields__bar__after='foo',
        fields__foo__after=0,
    )

This will make the field order foo, bar, baz.

If there are multiple fields with the same index or name the order of the fields will be used to disambiguate.


How do I specify which model fields the search of a choice_queryset use?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Form.choice_queryset` defaults to using the registered name field to search.
See :doc:`registrations` for how to register one. If present it will default
to a model field `name`. You can override which attributes it uses for
searching by specifing `extra__create_q_from_value`:

.. code:: python

    form = Form(
        auto__model=Foo,
        fields__foo__create_q_from_value=lambda field, value, **_: Q(foo__icontains=value) | Q(bar__icontains=value),
    )



How do I insert a CSS class or HTML attribute?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :doc:`Attrs`.


How do I override rendering of an entire field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a template name or a `Template` object:

.. code:: python

    form = Form(
        auto__model=Foo,
        fields__bar__template='my_template.html',
    )

.. code:: python

    form = Form(
        auto__model=Foo,
        fields__bar__template=Template('{{ field.attrs }}'),
    )


How do I override rendering of the input field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Pass a template name or a `Template` object to the `input` namespace:

.. code:: python

    form = Form(
        auto__model=Foo,
        fields__bar__input__template='my_template.html',
    )

.. code:: python

    form = Form(
        auto__model=Foo,
        fields__bar__input__template=Template('{{ field.attrs }}'),
    )

Tables
------


How do I customize the rendering of a table?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Table rendering can be customized on multiple levels. You pass a template with the `template` argument, which
is either a template name or a `Template` object.

Customize the HTML attributes of the table tag via the `attrs` argument. See attrs_.

To customize the row, see `How do I customize the rendering of a row?`_

To customize the cell, see `How do I customize the rendering of a cell?`_


How do you turn off pagination?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specify `page_size=None`:

.. code:: python

    Table(
        auto__model=Foo,
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

    Table(
        auto__model=Foo,
        column__square=Column(
            # computed value:
            cell__value=lambda row, **_: row.value * row.value,
        )
    )

or we could do:

.. code:: python

    Table(
        auto__model=Foo,
        column__square=Column(
            attr='value',
            cell__format=lambda value, **: value * value,
        )

This only affects the formatting when we render the cell value. Which might make more sense depending on your situation but for the simple case like we have here the two are equivalent.

How do I get iommi tables to understand my Django ModelField subclasses?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :doc:`registrations`.

How do I reorder columns?
~~~~~~~~~~~~~~~~~~~~~~~~~

By default the columns come in the order defined so if you have an explicit table defined, just move them around there. If the table is generated from a model definition, you can also move them in the model definition if you like, but that might not be a good idea. So to handle this case we can set the ordering on a column by giving it the `after` argument. Let's start with a simple model:

.. code:: python

    class Foo(models.Model):
        a = models.IntegerField()
        b = models.IntegerField()
        c = models.IntegerField()

If we just do `Table(auto__model=Foo)` we'll get the columns in the order a, b, c. But let's say I want to put c first, then we can pass it the `after` value `-1`:

.. code:: python

    Table(auto__model=Foo, columns__c__after=-1)

`-1` means the first, other numbers mean index. We can also put columns after another named column like so:

.. code:: python

    Table(auto__model=Foo, columns__c__after='a')

this will put the columns in the order a, c, b.

There is a special value `LAST` (import from `tri_declarative`) to put something last in a list.

How do I enable searching/filter on columns?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass the value `filter__include=True` to the column, to enable searching
in the advanced query language.

.. code:: python

    Table(
        auto__model=Foo,
        columns__a__filter__include=True,
    )

The `query` namespace here is used to configure a :doc:`Filter` so you can
configure the behavior of the searching by passing parameters here.

The `filter__field` namespace is used to configure the :doc:`Field`, so here you
can pass any argument to `Field` here to customize it.

If you just want to have the filter available in the advanced query language,
you can turn off the field in the generated form by passing
`filter__field__include=False`:

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

You can customize the :doc:`Cell` rendering in several ways:

- You can modify the html attributes via `cell__attrs`. See the question on attrs_

- Use `cell__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

- Pass a url (or callable that returns a url) to `cell__url` to make the cell a link.

How do I customize the rendering of a row?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize the row rendering in two ways:

- You can modify the html attributes via `row__attrs`. See the question on attrs_

- Use `row__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

In templates you can access the raw row via `row`. This would typically be one of your model objects. You can also access the cells of the table via `cells`. A naive template for a row would be `<tr>{% for cell in cells %}<td>{{ cell }}{% endfor %}</tr>`. You can access specific cells by their column names like `{{ cells.artist }}`.

To customize the cell, see `How do I customize the rendering of a cell?`_

How do I customize the rendering of a header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can customize headers in two ways:

- You can modify the html attributes via `header__attrs`. See the question on attrs_

- Use `header__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object. The default is `iommi/table/table_header_rows.html`.

How do I turn off the header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set `header_template` to `None`.

How do I add fields to a table that is generated from a model?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See the question `How do I create a column based on computed data?`_

How do I specify which columns to show?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Just pass `include=False` to hide the column or `include=True` to show it. By default columns are shown, except the primary key column that is by default hidden. You can also pass a callable here like so:

.. code:: python

    Table(
        auto__model=Foo,
        columns__a__include=
            lambda request, **_: request.GET.get('some_parameter') == 'hello!',
    )

This will show the column `a` only if the GET parameter `some_parameter` is set to `hello!`.

To be more precise, `include` turns off the entire column. Sometimes you want to have the searching turned on, but disable the rendering of the column. To do this use the `render_column` parameter instead.

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

    Table(
        auto__model=Bar,
        columns__a__attr='c__a',
    )

How do I turn off sorting? (on a column or table wide)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To turn off column on a column pass it `sortable=False` (you can also use a lambda here!):

.. code:: python

    Table(
        auto__model=Foo,
        columns__a__sortable=False,
    )

and to turn it off on the entire table:

.. code:: python

    Table(
        auto__model=Foo,
        sortable=False,
    )

How do I specify the title of a header?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `display_name` property of a column is displayed in the header.

.. code:: python

    Table(
        auto__model=Foo,
        columns__a__display_name='header title',
    )

How do I set the default sort order of a column to be descending instead of ascending?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    Table(
        auto__model=Foo,
        columns__a__sort_default_desc=True,  # or a lambda!
    )


How do I group columns?
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    Table(
        auto__model=Foo,
        columns__a__group='foo',
        columns__b__group='foo',
    )

The grouping only works if the columns are next to each other, otherwise you'll get multiple groups. The groups are rendered by default as a second header row above the normal header row with colspans to group the headers.


How do I get rowspan on a table?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can manually set the rowspan attribute via `row__attrs__rowspan` but this is tricky to get right because you also have to hide the cells that are "overwritten" by the rowspan. We supply a simpler method: `auto_rowspan`. It automatically makes sure the rowspan count is correct and the cells are hidden. It works by checking if the value of the cell is the same, and then it becomes part of the rowspan.

.. code:: python

    Table(
        auto__model=Foo,
        columns__a__auto_rowspan=True,
    )


How do I enable bulk editing?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Editing multiple items at a time is easy in iommi with the built in bulk
editing. Enable it for a columns by passing `bulk__include=True`:

.. code:: python

    Table(
        auto__model=Foo,
        columns__select__include=True,
        columns__a__bulk__include=True,
    )

The bulk namespace here is used to configure a `Field` for the GUI so you
can pass any parameter you can pass to `Field` there to customize the
behavior and look of the bulk editing for the column.

You also need to enable the select column, otherwise you can't select
the columns you want to bulk edit.


How do I enable bulk delete?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Editing multiple items at a time is easy in iommi with the built in bulk
editing. Enable it for a columns by passing `bulk__include=True`:

.. code:: python

    Table(
        auto__model=Foo,
        columns__select__include=True,
        actions__delete__include=True,
    )

To enable the bulk delete, enable the `delete` action.

You also need to enable the select column, otherwise you can't select
the columns you want to delete.


How do I make a custom bulk action?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You need to first show the select column by passing
`columns__select__include=True`, then define a submit `Action` with a post
handler:

.. code:: python
    def my_action_post_handler(table, request, **_):
        queryset = table.bulk_queryset()
        queryset.update(spiral='architect')
        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    Table(
        auto__model=Foo,
        columns__select__include=True,
        actions__my_action=Action.submit(
            post_handler=my_action_post_handler,
        )
    )


How do I make a freetext search field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to filter based on a freetext query on one or more columns we've got a nice little feature for this:

.. code:: python

    Table(
        auto__model=Foo,
        columns__a__filter__freetext=True,
        columns__b__filter__freetext=True,
    )

(You don't need to enable querying with `columns__b__filter__include=True` first)


What is the difference between `attr` and `_name`?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`attr` is the attribute path of the value iommi reads from a row. In the simple case it's just the attribute name, but if you want to read the attribute of an attribute you can use `__`-separated paths for this: `attr='foo__bar'` is functionally equivalent to `cell__value=lambda row, **_: row.foo.bar`. Set `attr` to `None` to not read any attribute from the row.

`_name` is the name used internally. By default `attr` is set to the value of `_name`. This name is used when accessing the column from `Table.columns` and it's the name used in the GET parameter to sort by that column. This is a required field.


Queries
-------

How do I override what operator is used for a query?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The member `query_operator_to_q_operator` for `Filter` is used to convert from e.g. `:`
to `icontains`. You can specify another callable here:

.. code:: python

    Table(
        auto__model=Song,
        columns__album__filter__query_operator_to_q_operator=lambda op: 'exact',
    )

The above will force the album name to always be looked up with case
sensitive match even if the user types `album<Paranoid` in the
advanced query language. Use this feature with caution!

See also `How do I control what Q is produced?`_

How do I control what Q is produced?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For more advanced customization you can use `value_to_q`. It is a
callable that takes `filter, op, value_string_or_f` and returns a
`Q` object. The default handles `__`, different operators, negation
and special handling of when the user searches for `null`.
