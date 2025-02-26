from docs.models import *
from iommi import *
from iommi._web_compat import Template
from tests.helpers import (
    req,
    show_output,
    show_output_collapsed,
)

request = req('get')

from tests.helpers import req
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
)
from django.db import models
import pytest
pytestmark = pytest.mark.django_db


def test_tables():
    # language=rst
    """
    .. _cookbook-tables:

    Tables
    ------

    """


def test_how_do_i_customize_the_rendering_of_a_table():
    # language=rst
    """
    How do I customize the rendering of a table?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Table rendering can be customized on multiple levels. You pass a template with the `template` argument, which
    is either a template name or a `Template` object.

    Customize the HTML attributes of the table tag via the `attrs` argument. See :ref:`attrs <attributes>`.

    To customize the row, see `How do I customize the rendering of a row?`_

    To customize the cell, see `How do I customize the rendering of a cell?`_

    To customize the rendering of the table, see `table-as-div`_
    """


def test_how_do_you_turn_off_pagination(small_discography):
    # language=rst
    """
    .. _turn-off-pagination:

    How do you turn off pagination?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Table.page_size
    .. uses EditTable.page_size
    .. uses TableAutoConfig.model

    Specify `page_size=None`:
    """

    table = Table(
        auto__model=Album,
        page_size=None,
    )

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    Or in the declarative style:
    """

    class MyTable(Table):
        name = Column()

        class Meta:
            page_size = None

    # @test
    show_output(MyTable(rows=Album.objects.all()))
    # @end


def test_how_do_i_customize_the_rendering_of_a_cell():
    # language=rst
    """
    .. _customize-table-cell-render:

    How do I customize the rendering of a cell?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Attrs
    .. uses Cell.attrs
    .. uses Cell.template
    .. uses Cell.url
    .. uses EditCell.attrs
    .. uses EditCell.template
    .. uses EditCell.url
    .. uses Column.cell
    .. uses EditColumn.cell

    You can customize the :doc:`Cell` rendering in several ways:

    - You can modify the html attributes via `cell__attrs`. See :ref:`attrs <attributes>`.

    - Use `cell__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

    - Pass a url (or callable that returns a url) to `cell__url` to make the cell a link (see next question).


    """


def test_how_do_i_make_a_link_in_a_cell(album):
    # language=rst
    """
    .. _cell-link:

    How do I make a link in a cell?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Cell.url
    .. uses EditCell.url
    .. uses Column.cell
    .. uses EditColumn.cell
    .. uses Table.columns
    .. uses TableAutoConfig.model

    This is such a common case that there's a special case for it: pass the `url` and `url_title` parameters to the `cell`:


    """
    table = Table(
        auto__model=Album,
        columns__name__cell__url='http://example.com',
        columns__name__cell__url_title='go to example',
    )

    # @test
    show_output(table)
    # @end



def test_how_do_i_create_a_column_based_on_computed_data_():
    # language=rst
    """
    .. _column-computed-data:

    How do I create a column based on computed data (i.e. a column not based on an attribute of the row)?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Cell.value
    .. uses Cell.format
    .. uses EditCell.value
    .. uses EditCell.format
    .. uses Column.cell
    .. uses EditColumn.cell
    .. uses Table.columns
    .. uses TableAutoConfig.model

    Let's say we have a model like this:


    """
    class Foo(models.Model):
        value = models.IntegerField()

    # @test
        class Meta:
            app_label = 'docs_computed'

    foos = [Foo(value=8)]
    # @end

    # language=rst
    """
    And we want a computed column `square` that is the square of the value, then we can do:
    """

    table = Table(
        auto__model=Foo,
        columns__square=Column(
            # computed value:
            cell__value=lambda row, **_: row.value * row.value,
        )
    )

    # @test
    show_output(table.refine(rows=foos))
    # @end

    # language=rst
    """
    or we could do:
    """

    Table(
        auto__model=Foo,
        columns__square=Column(
            attr='value',
            cell__format=lambda value, **_: value * value,
        )
    )

    # language=rst
    """
    This only affects the formatting when we render the cell value. Which might make more sense depending on your situation but for the simple case like we have here the two are equivalent.
    """


def test_how_do_i_get_iommi_tables_to_understand_my_django_modelfield_subclasses():
    # language=rst
    """
    How do I get iommi tables to understand my Django ModelField subclasses?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    See :doc:`registrations`.

    """


def test_how_do_i_reorder_columns():
    # language=rst
    """

    .. _reorder-columns:

    How do I reorder columns?
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Column.after
    .. uses EditColumn.after
    .. uses Table.columns
    .. uses TableAutoConfig.model

    By default the columns come in the order defined so if you have an explicit table defined, just move them around there. If the table is generated from a model definition, you can also move them in the model definition if you like, but that might not be a good idea. So to handle this case we can set the ordering on a column by giving it the `after` argument. Let's start with a simple model:


    """
    class Foo(models.Model):
        a = models.IntegerField()
        b = models.IntegerField()
        c = models.IntegerField()

    # @test
        class Meta:
            app_label = 'docs_reorder'
    # @end

    # language=rst
    """
    If we just do `Table(auto__model=Foo)` we'll get the columns in the order a, b, c. But let's say I want to put c first, then we can pass it the `after` value `-1`:
    """

    table = Table(auto__model=Foo, columns__c__after=-1)

    # @test
    show_output(table.refine(rows=[]))
    # @end

    # language=rst
    """
    `-1` means the first, other numbers mean index. We can also put columns after another named column like so:
    """

    table = Table(auto__model=Foo, columns__c__after='a')

    # @test
    show_output(table.refine(rows=[]))
    # @end

    # language=rst
    """
    this will put the columns in the order a, c, b.

    There is a special value `LAST` (import from `iommi.declarative`) to put something last in a list:
    """

    table = Table(auto__model=Foo, columns__a__after=LAST)

    # @test
    show_output(table.refine(rows=[]))
    # @end


def test_how_do_i_enable_searching_filter_on_columns():
    # language=rst
    """
    .. _filter-column:

    How do I enable searching/filter on columns?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Column.filter
    .. uses EditColumn.filter
    .. uses Filter.include
    .. uses TableAutoConfig.model

    Pass the value `filter__include=True` to the column, to enable searching
    in the advanced query language.


    """
    table = Table(
        auto__model=Album,
        columns__name__filter__include=True,
    )

    # language=rst
    """
    The `filter` namespace here is used to configure a :doc:`Filter` so you can
    configure the behavior of the searching by passing parameters here.

    The `filter__field` namespace is used to configure the :doc:`Field`, so here you
    can pass any argument to `Field` here to customize it.

    If you just want to have the filter available in the advanced query language,
    you can turn off the field in the generated form by passing
    `filter__field__include=False`:
    """

    # @test
    show_output(table)
    # @end


def test_how_do_i_make_a_freetext_search_field():
    # language=rst
    """
    .. _freetext-column:

    How do I make a freetext search field?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Filter.freetext
    .. uses Column.filter
    .. uses TableAutoConfig.model

    If you want to filter based on a freetext query on one or more columns we've got a nice little feature for this:


    """
    table = Table(
        auto__model=Album,
        columns__name__filter=dict(
            freetext=True,
            include=True,
        ),
        columns__year__filter__freetext=True,
        columns__year__filter__include=True,
    )

    # language=rst
    """
    This will display one search box to search both `year` and `name` columns:
    """

    # @test
    show_output(table.refine(rows=[]))
    # @end


def test_how_do_i_customize_html_attributes__css_classes_or_css_style_specifications():
    # @test
    # TODO: the code in here is no longer tested!
    # @end

    # language=rst
    """

    How do I customize HTML attributes, CSS classes or CSS style specifications?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Table.attrs
    .. uses Form.attrs
    .. uses Field.attrs

    The `attrs` namespace has special handling to make it easy to customize. There are three main cases:

    First the straight forward case where a key/value pair is rendered in the output:

    .. code-block:: pycon

        >>> from iommi.attrs import render_attrs
        >>> from iommi.declarative.namespace import Namespace
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
        ...     Namespace(
        ...         foo='bar',
        ...         class__foo=True,
        ...         class__bar=True,
        ...         style__font='Arial',
        ...         **{'style__font-family': 'serif'}
        ...     )
        ... )
        ' class="bar foo" foo="bar" style="font-family: serif; font: Arial"'

    """


def test_how_do_i_customize_the_rendering_of_a_row():
    # language=rst
    """

    .. _customize-rendering-row:

    How do I customize the rendering of a row?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Table.row
    .. uses EditTable.row
    .. uses RowConfig.attrs
    .. uses RowConfig.template

    You can customize the row rendering in two ways:

    - You can modify the html attributes via `row__attrs`. See :ref:`attrs <attributes>`.

    - Use `row__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

    In templates you can access the raw row via `row`. This would typically be one of your model objects. You can also access the cells of the table via `cells`. A naive template for a row would be `<tr>{% for cell in cells %}<td>{{ cell }}{% endfor %}</tr>`. You can access specific cells by their column names like `{{ cells.artist }}`.

    To customize the cell, see `How do I customize the rendering of a cell?`_
    """


def test_how_do_i_customize_the_rendering_of_a_header():
    # language=rst
    """
    .. _customize-header:

    How do I customize the rendering of a header?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.header
    .. uses EditColumn.header

    You can customize headers in two ways:

    - You can modify the html attributes via `header__attrs`. See :ref:`attrs <attributes>`.

    - Use `header__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

    """


def test_how_do_i_turn_off_the_header():
    # language=rst
    """

    .. _turn-off-header:

    How do I turn off the header?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Table.header
    .. uses EditTable.header

    Set `header__template` to `None`.


    """


def test_how_do_i_add_fields_to_a_table_that_is_generated_from_a_model():
    # language=rst
    """
    How do I add fields to a table that is generated from a model?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    See the question `column-computed-data`_
    """


def test_how_do_i_specify_which_columns_to_show():
    # language=rst
    """
    .. _show-columns:

    How do I specify which columns to show?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.include
    .. uses EditColumn.include
    .. uses TableAutoConfig.model
    .. uses Column.render_column

    Pass `include=False` to hide the column or `include=True` to show it. By default columns are shown, except the primary key column that is by default hidden. You can also pass a callable here like so:
    """

    Table(
        auto__model=Album,
        columns__name__include=
            lambda request, **_: request.GET.get('some_parameter') == 'hello!',
    )

    # language=rst
    """
    This will show the column `name` only if the GET parameter `some_parameter` is set to `hello!`.

    To be more precise, `include` turns off the entire column. Sometimes you want to have the searching turned on, but disable the rendering of the column. To do this use the `render_column` parameter instead. This is useful to for example turn on filtering for a column, but not render it:
    """

    table = Table(
        auto__model=Album,
        columns__year__render_column=False,
        columns__year__filter__include=True,
    )

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    Instead of using `auto__include`, you can also use `auto__exclude` to just exclude the columns you don't want:
    """

    table = Table(
        auto__model=Album,
        auto__exclude=['year'],
    )

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    There is also a config option `default_included` which is by default `True`, which is where iommi's default behavior of showing all columns comes from. If you set it to `False` columns are now opt-in:
    """

    table = Table(
        auto__model=Album,
        auto__default_included=False,
        # Turn on only the name column
        columns__name__include=True,
    )

    # @test
    show_output(table)
    # @end


def test_how_do_i_access_table_data_programmatically_(capsys, small_discography):
    # language=rst
    """
    .. _programmatic-table-data-access:

    How do I access table data programmatically (like for example to dump to json)?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.cells_for_rows
    .. uses EditTable.cells_for_rows

    Here's a simple example that prints a table to stdout:

    """
    def print_table(table):
        for row in table.cells_for_rows():
            for cell in row:
                print(cell.render_formatted(), end=' ')
            print()

    table = Table(auto__model=Album).bind(request=req('get'))
    print_table(table)

    # @test
    captured = capsys.readouterr()
    show_output(HttpResponse('<html><style>html {color: black; background: white}</style><pre>' + captured.out + '</pre></html>'))
    # @end


def test_how_do_i_access_foreign_key_related_data_in_a_column():
    # language=rst
    """
    .. _fk-related-data-access:

    How do I access foreign key related data in a column?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.attr
    .. uses Table.auto
    .. uses EditColumn.attr
    .. uses EditTable.auto

    Let's say we have two models:


    """
    class Foo(models.Model):
        a = models.IntegerField()

    # @test
        class Meta:
            app_label = 'docs_fk'
    # @end

    class Bar(models.Model):
        b = models.IntegerField()
        c = models.ForeignKey(Foo, on_delete=models.CASCADE)

    # @test
        class Meta:
            app_label = 'docs_fk'
    # @end

    # language=rst
    """
    we can build a table of `Bar` that shows the data of `a` like this:
    """

    table = Table(
        auto__model=Bar,
        columns__a=Column(attr='c__a'),
    )

    # @test
    f = Foo(a=7)
    b = Bar(b=3, c=f)
    show_output(table.refine(rows=[b]))
    # @end

    # language=rst
    """
    Or like this:
    """

    table = Table(
        auto__model=Bar,
        include=['b', 'c__a'],
    )

    # @test
    f = Foo(a=7)
    b = Bar(b=3, c=f)
    show_output(table.refine(rows=[b]))
    # @end

    # language=rst
    """
    iommi will do automatic `select_related` and/or `prefetch_related` as appropriate in many cases too, so you mostly don't need to worry about that.
    """


def test_how_do_i_turn_off_sorting(small_discography):
    # language=rst
    """

    .. _table-sorting:

    How do I turn off sorting? (on a column or table wide)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.sortable
    .. uses Column.sortable
    .. uses EditTable.sortable
    .. uses EditColumn.sortable

    To turn off column on a column pass it `sortable=False` (you can also use a lambda here!):
    """

    table = Table(
        auto__model=Album,
        columns__name__sortable=False,
    )

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    and to turn it off on the entire table:
    """

    table = Table(
        auto__model=Album,
        sortable=False,
    )

    # @test
    show_output(table)
    # @end


def test_how_do_i_specify_the_title_of_a_header(small_discography):
    # language=rst
    """
    .. _header-title:

    How do I specify the title of a header?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.display_name
    .. uses EditColumn.display_name

    The `display_name` property of a column is displayed in the header.


    """
    table = Table(
        auto__model=Album,
        columns__name__display_name='header title',
    )

    # @test
    assert Album.objects.count() > 0
    show_output(table)
    # @end


def test_how_do_i_set_the_default_sort_order_of_a_column_to_be_descending_instead_of_ascending(medium_discography):
    # language=rst
    """
    .. _sort-direction:

    How do I set the default sort direction of a column to be descending instead of ascending?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.sort_default_desc
    .. uses EditColumn.sort_default_desc

    """

    table = Table(
        auto__model=Album,
        columns__name__sort_default_desc=True,  # or a lambda!
    )

    # @test
    assert Album.objects.count() > 0
    show_output_collapsed(table)
    # @end


def test_how_do_i_set_the_default_sort_order_on_a_table(medium_discography):
    # language=rst
    """
    .. _default-sort-order:

    How do I set the default sorting column of a table?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.default_sort_order

    Tables are sorted by default on the order specified in the models `Meta` and then on `pk`. Set `default_sort_order` to set another default ordering:
    """

    table = Table(
        auto__model=Album,
        default_sort_order='year',
    )

    # @test
    assert Album.objects.count() > 0
    show_output(table)
    # @end


def test_how_do_i_group_columns(medium_discography):
    # language=rst
    """
    .. _group-columns:

    How do I group columns?
    ~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.group
    .. uses EditColumn.group
    .. uses TableAutoConfig.model

    """

    table = Table(
        auto__model=Album,
        columns__name__group='foo',
        columns__artist__group='bar',
        columns__year__group='bar',
    )

    # language=rst
    """
    The grouping only works if the columns are next to each other, otherwise you'll get multiple groups. The groups are rendered by default as a second header row above the normal header row with colspans to group the headers.
    """

    # @test
    show_output(table)
    # @end


def test_how_do_i_group_rows(medium_discography):
    # language=rst
    """
    .. _group-rows:

    How do I group rows?
    ~~~~~~~~~~~~~~~~~~~~
    .. uses Column.row_group
    .. uses EditColumn.row_group
    .. uses TableAutoConfig.rows

    Use `row_group`. By default this will output a `<th>` tag. You can configure it like any other fragment if you want to change that to a `<td>`. Note that the order of the columns in the table is used for grouping. This is why in the example below the `year` column is moved to index zero: we want to group on year first.
    """

    table = Table(
        auto__rows=Album.objects.order_by('year', 'artist', 'name'),
        columns__artist=dict(
            row_group__include=True,
            render_column=False,
        ),
        columns__year=dict(
            after=0,
            render_column=False,
            row_group=dict(
                include=True,
                template=Template('''
                <tr>
                    {{ row_group.iommi_open_tag }}
                        {{ value }} in our hearts
                    {{ row_group.iommi_close_tag }}
                </tr>
                '''),
            ),
        ),
    )

    # @test
    show_output(table)
    # @end


def test_how_do_i_get_rowspan_on_a_table(small_discography, black_sabbath):
    # language=rst
    """
    .. _rowspan:

    How do I get rowspan on a table?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.auto_rowspan
    .. uses EditColumn.auto_rowspan

    You can manually set the rowspan attribute via `row__attrs__rowspan` but this is tricky to get right because you also have to hide the cells that are "overwritten" by the rowspan. We supply a simpler method: `auto_rowspan`. It automatically makes sure the rowspan count is correct and the cells are hidden. It works by checking if the value of the cell is the same, and then it becomes part of the rowspan.
    """

    table = Table(
        auto__model=Album,
        columns__year__auto_rowspan=True,
        columns__year__after=0,  # put the column first
    )

    # @test
    Album.objects.create(name='Live at Last', year=1980, artist=black_sabbath)
    show_output(table)
    # @end


def test_how_do_i_enable_bulk_editing(small_discography):
    # language=rst
    """
    .. _bulk-edit:

    How do I enable bulk editing?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.bulk
    .. uses EditColumn.bulk

    Editing multiple items at a time is easy in iommi with the built in bulk
    editing. Enable it for a columns by passing `bulk__include=True`:
    """

    table = Table(
        auto__model=Album,
        columns__select__include=True,
        columns__year__bulk__include=True,
    )

    # language=rst
    """
    The bulk namespace here is used to configure a `Field` for the GUI so you
    can pass any parameter you can pass to `Field` there to customize the
    behavior and look of the bulk editing for the column.

    You also need to enable the select column, otherwise you can't select
    the columns you want to bulk edit.
    """

    # @test
    show_output(table)
    # @end


def test_how_do_i_enable_bulk_delete(small_discography):
    # language=rst
    """

    .. _bulk-delete:

    How do I enable bulk delete?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.bulk
    .. uses EditTable.bulk
    """

    table = Table(
        auto__model=Album,
        columns__select__include=True,
        bulk__actions__delete__include=True,
    )

    # language=rst
    """
    To enable the bulk delete, enable the `delete` action.

    You also need to enable the select column, otherwise you can't select
    the columns you want to delete.
    """

    # @test
    show_output(table)
    # @end


def test_how_do_i_make_a_custom_bulk_action(album):
    # language=rst
    """

    .. _custom-bulk-action:

    How do I make a custom bulk action?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.bulk
    .. uses EditTable.bulk

    You need to first show the select column by passing
    `columns__select__include=True`, then define a submit `Action` with a post
    handler:
    """

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

    # @test
    t.bind(request=req('post', **{'-my_action': '', '_all_pks_': '1'})).render_to_response()
    album.refresh_from_db()
    assert album.name == 'Paranoid'
    # @end


def test_what_is_the_difference_between_attr_and__name():
    # language=rst
    """
    .. _attr-name-diff:

    What is the difference between `attr` and `_name`?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.attr
    .. uses Column.name
    .. uses EditColumn.attr
    .. uses EditColumn.name
    .. uses Column.cell
    .. uses EditColumn.cell

    `attr` is the attribute path of the value iommi reads from a row. In the simple case it's just the attribute name, but if you want to read the attribute of an attribute you can use `__`-separated paths for this: `attr='foo__bar'` is functionally equivalent to `cell__value=lambda row, **_: row.foo.bar`. Set `attr` to `None` to not read any attribute from the row.

    `_name` is the name used internally. By default `attr` is set to the value of `_name`. This name is used when accessing the column from `Table.columns` and it's the name used in the GET parameter to sort by that column. This is a required field.
    """


def test_table_with_foreign_key_reverse(small_discography):
    # language=rst
    """
    .. _reverse-fk-table:

    How do I show a reverse foreign key relationship?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.include
    .. uses EditColumn.include

    By default reverse foreign key relationships are hidden. To turn it on, pass `include=True` to the column:
    """

    t = Table(
        auto__model=Artist,
        columns__albums__include=True,
    )

    # @test
    t = t.bind(request=req('get'))

    assert list(t.columns.keys()) == ['name', 'albums']
    assert t.columns.albums.display_name == 'Albums'
    assert t.columns.albums.model_field is Artist._meta.get_field('albums')

    show_output(t)
    # @end


def test_table_with_m2m_key_reverse(small_discography):
    # language=rst
    """
    .. _reverse-m2m:

    How do I show a reverse many-to-many relationship?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Column.include
    .. uses EditColumn.include

    By default reverse many-to-many relationships are hidden. To turn it on, pass `include=True` to the column:
    """

    # @test
    heavy_metal = Genre.objects.create(name='Heavy Metal')
    for album in Album.objects.all():
        album.genres.add(heavy_metal)
    # @end

    t = Table(
        auto__model=Genre,
        columns__albums__include=True,
    )

    # @test
    t = t.bind(request=req('get'))

    assert list(t.columns.keys()) == ['name', 'albums']
    assert t.columns.albums.display_name == 'Albums'
    assert t.columns.albums.model_field is Genre._meta.get_field('albums')

    show_output(t)
    # @end


def test_insert_arbitrary_html(big_discography):
    # language=rst
    """
    .. _arbitrary-html:

    How do I insert arbitrary html into a Table?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.container
    .. uses Table.outer
    .. uses EditTable.container
    .. uses EditTable.outer

    Sometimes you want to insert some extra html, css, or `Part` into a
    `Table`. You can do this with the `container` or `outer` namespaces.

    For `container`, by default items are added after the table but you
    can put them above with `after=0`.

    For `outer`, you can put content before the `h` tag even.
    """

    t = Table(
        auto__model=Genre,
        container__children__foo='Foo',
        container__children__bar=html.div('Bar', after=0),
        outer__children__bar=html.div('Baz', after=0),
    )

    # @test
    t = t.bind(request=req('get'))

    show_output(t)
    # @end


def test_custom_actions(small_discography):
    # language=rst
    """
    .. _custom-actions:

    How do I add custom actions/links to a table?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.actions
    .. uses Cell.url
    .. uses Column.link
    .. uses EditTable.actions
    .. uses EditCell.url
    .. uses EditColumn.link

    For the entire table:
    """

    t = Table(
        auto__model=Album,
        actions__link=Action(attrs__href='/'),
    )

    # @test
    t = t.bind(request=req('get'))

    show_output(t)
    # @end

    # language=rst
    """
    Or as a column:
    """

    t = Table(
        auto__model=Album,
        columns__link=Column.link(attr=None, cell__url='/', cell__value='Link'),
    )

    # @test
    t = t.bind(request=req('get'))

    show_output(t)
    # @end


def test_render_additional_rows(small_discography):
    # language=rst
    """
    .. _additional-rows:

    How do I render additional rows?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.rows
    .. uses EditTable.rows
    .. uses RowConfig.template

    Using `rows__template` you can render the default row with `{{ cells.render }}` and then your own custom data:


    """

    t = Table(
        auto__model=Album,
        row__template=Template('''
            {{ cells.render }}
            <tr>
                <td style="text-align: center" colspan="{{ cells|length }}">🤘🤘</td>
            </tr>
        '''),
    )

    # @test
    t = t.bind(request=req('get'))

    show_output(t)
    # @end


def test_initial_filter_on_table(really_big_discography):
    # language=rst
    """
    .. _initial-filter:

    How do I set an initial filter to a table?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.query
    .. uses EditTable.query
    .. uses Query.form

    The `Query` of a `Table` has a `Form` where you can set the initial value:


    """

    t = Table(
        auto__model=Album,
        columns__artist__filter__include=True,
        query__form__fields__artist__initial=lambda **_: Artist.objects.get(name='Dio'),
    )

    # @test
    t = t.bind(request=req('get'))

    show_output(t)
    # @end


def test_indexed_rows(small_discography):
    # language=rst
    """
    .. _row-numbers:

    How do I show row numbers?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Cells.row_index
    .. uses Cell.value
    .. uses EditCells.row_index
    .. uses EditCell.value
    .. uses Column.cell
    .. uses EditColumn.cell

    Use `cells.row_index` to get the index of the row in the current rendering.
    """

    t = Table(
        auto__model=Album,
        columns__index=Column(
            after=0,
            cell__value=lambda row, cells, **_: cells.row_index
        ),
    )

    # @test
    t = t.bind(request=req('get'))

    show_output(t)
    # @end


def test_nested_foreign_keys(big_discography):
    # language=rst
    """
    .. _nested-fk:

    How do I show nested foreign key relationships?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.auto
    .. uses EditTable.auto
    .. uses Column.cell
    .. uses EditColumn.cell
    .. uses TableAutoConfig.include

    Say you have a list of tracks and you want to show the album and then from that album, you also want to show the artist:
    """

    t = Table(
        auto__model=Track,
        auto__include=[
            'name',
            'album',
            'album__artist',  # <--
        ]
    )

    # @test
    t = t.bind(request=req('get'))

    show_output(t)
    # @end

    # language=rst
    """
    The column created is named `album_artist` (as `__` is reserved for traversing a namespace), so that's the name you need to reference is you need to add more configuration to that column:
    """

    t = Table(
        auto__model=Track,
        auto__include=[
            'name',
            'album',
            'album__artist',
        ],
        columns__album_artist__cell__attrs__style__background='blue',
    )

    # @test
    t = t.bind(request=req('get'))

    show_output(t)
    # @end


def test_dont_render_header(small_discography):
    # language=rst
    """
    .. _stop-header-render:

    How do I stop rendering the header?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.header
    .. uses EditTable.header
    .. uses HeaderConfig.include

    Use `header__template=None` to not render the header, or
    `header__include=False` to remove the processing of the header totally. The
    difference being that you might want the header object to access
    programmatically for some reason, so then it's appropriate to use the
    `template=None` method.
    """

    t = Table(
        auto__model=Album,
        header__include=False,
    )

    # @test
    t = t.bind(request=req('get'))

    show_output(t)
    assert '<thead>' not in t.__html__() and 'None' not in t.__html__()
    # @end

    t = Table(
        auto__model=Album,
        header__template=None,
    )

    # @test
    t = t.bind(request=req('get'))

    show_output(t)
    assert '<thead>' not in t.__html__() and 'None' not in t.__html__()
    # @end


def test_render_table_as_div(medium_discography):
    # language=rst
    """
    .. _table-as-div:

    How do I render a Table as divs?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.tag
    .. uses Table.tbody
    .. uses Table.cell
    .. uses CellConfig.tag
    .. uses RowConfig.tag
    .. uses Table.header
    .. uses Header.template

    You can render a `Table` as a div with the shortcut `Table.div`:
    """

    table = Table.div(
        auto__model=Album,
    )

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    This shortcut changes the rendering of the entire table from `<table>` to `<div>` by specifying the `tag` configuration, changes the `<tbody>` to a `<div>` via `tbody__tag`, the row via `row__tag` and removes the header with `header__template=None`.
    """


def test_how_do_i_do_custom_processing_on_rows(medium_discography):
    # language=rst
    """
    .. table-preprocess_rows:

    How do I do custom processing on rows before rendering?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.preprocess_row
    .. uses Table.preprocess_rows
    .. uses EditTable.preprocess_row
    .. uses EditTable.preprocess_rows

    Sometimes it's useful to further process the rows before rendering, by fetching more data, doing calculations, etc. If you can use `QuerySet.annotate()`, that's great, but sometimes that's not enough. This is where `preprocess_row` and `preprocess_rows` come in. The first is called on each row, and the second is called for the entire list as a whole.

    Note that this is all done *after* pagination.

    Modifying row by row:
    """
    def preprocess_album(row, **_):
        row.year += 1000
        return row

    table = Table(
        auto__model=Album,
        preprocess_row=preprocess_album,
    )

    # language=rst
    """
    Note that `preprocess_row` requires that you return the object. This is because you can return a different object if you'd like.
    """

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    Modifying the entire list:
    """

    def preprocess_albums(rows, **_):
        for i, row in enumerate(rows):
            row.index = i
        return rows

    table = Table(
        auto__model=Album,
        preprocess_rows=preprocess_albums,
        columns__index=Column.number(),
    )

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    Note that `preprocess_rows` requires that you return the list. That is because you can also return a totally new list if you'd like.
    """


def test_how_do_i_set_an_empty_message():
    # language=rst
    """
    .. table-empty-message:

    How do I set an empty message?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Table.empty_message
    .. uses EditTable.empty_message

    By default iommi will render an empty table simply as empty:
    """

    table = Table(
        auto__model=Album,
    )

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    If you want to instead display an explicit message when the table is empty, you use `empty_message`:
    """

    table = Table(
        auto__model=Album,
        empty_message='Destruction of the empty spaces is my one and only crime',
    )

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    This setting is probably something you want to set up in your `Style`, and not per table.
    """
