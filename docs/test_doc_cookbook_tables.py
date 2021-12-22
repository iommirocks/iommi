from iommi import *
from iommi.admin import Admin
from django.urls import (
    include,
    path,
)
from django.db import models
from tests.helpers import req, user_req, staff_req
from docs.models import *
request = req('get')

from tests.helpers import req, user_req, staff_req
from django.template import Template
from tri_declarative import Namespace
from iommi.attrs import render_attrs
from django.http import HttpResponseRedirect
from datetime import date
import pytest
pytestmark = pytest.mark.django_db




def test_tables():
    # language=rst
    """
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

    Customize the HTML attributes of the table tag via the `attrs` argument. See attrs_.

    To customize the row, see `How do I customize the rendering of a row?`_

    To customize the cell, see `How do I customize the rendering of a cell?`_

    """
    

def test_how_do_you_turn_off_pagination():
    # language=rst
    """
    .. _Table.page_size:

    How do you turn off pagination?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Specify `page_size=None`:


    """
    Table(
        auto__model=Album,
        page_size=None,
    )


    class MyTable(Table):
        a = Column()

        class Meta:
            page_size = None


def test_how_do_i_customize_the_rendering_of_a_cell():
    # language=rst
    """
    .. _Table.cell:

    How do I customize the rendering of a cell?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    You can customize the :doc:`Cell` rendering in several ways:

    - You can modify the html attributes via `cell__attrs`. See the question on attrs_

    - Use `cell__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

    - Pass a url (or callable that returns a url) to `cell__url` to make the cell a link.


    """
    

def test_how_do_i_make_a_link_in_a_cell():
    # language=rst
    """
    How do I make a link in a cell?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This is such a common case that there's a special case for it: pass the `url` and `url_title` parameters to the `cell`:


    """
    Column(
        cell__url='http://example.com',
        cell__url_title='go to example',
    )


def test_how_do_i_create_a_column_based_on_computed_data_():
    # language=rst
    """
    .. _How do I create a column based on computed data?:

    How do I create a column based on computed data (i.e. a column not based on an attribute of the row)?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Let's say we have a model like this:


    """
    class Foo(models.Model):
        value = models.IntegerField()

    # @test
        class Meta:
            app_label = 'docs_computed'

    # language=rst
    """
    And we want a computed column `square` that is the square of the value, then we can do:


    """
    Table(
        auto__model=Foo,
        columns__square=Column(
            # computed value:
            cell__value=lambda row, **_: row.value * row.value,
        )
    )

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
    .. _Column.after:

    How do I reorder columns?
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    By default the columns come in the order defined so if you have an explicit table defined, just move them around there. If the table is generated from a model definition, you can also move them in the model definition if you like, but that might not be a good idea. So to handle this case we can set the ordering on a column by giving it the `after` argument. Let's start with a simple model:


    """
    class Foo(models.Model):
        a = models.IntegerField()
        b = models.IntegerField()
        c = models.IntegerField()

    # @test
        class Meta:
            app_label = 'docs_reorder'

    # language=rst
    """
    If we just do `Table(auto__model=Foo)` we'll get the columns in the order a, b, c. But let's say I want to put c first, then we can pass it the `after` value `-1`:


    """
    Table(auto__model=Foo, columns__c__after=-1)

    # language=rst
    """
    `-1` means the first, other numbers mean index. We can also put columns after another named column like so:


    """
    Table(auto__model=Foo, columns__c__after='a')

    # language=rst
    """
    this will put the columns in the order a, c, b.

    There is a special value `LAST` (import from `tri_declarative`) to put something last in a list.

    """
    

def test_how_do_i_enable_searching_filter_on_columns():
    # language=rst
    """
    .. _Column.filter:

    How do I enable searching/filter on columns?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Pass the value `filter__include=True` to the column, to enable searching
    in the advanced query language.


    """
    Table(
        auto__model=Album,
        columns__name__filter__include=True,
    )

    # language=rst
    """
    The `query` namespace here is used to configure a :doc:`Filter` so you can
    configure the behavior of the searching by passing parameters here.

    The `filter__field` namespace is used to configure the :doc:`Field`, so here you
    can pass any argument to `Field` here to customize it.

    If you just want to have the filter available in the advanced query language,
    you can turn off the field in the generated form by passing
    `filter__field__include=False`:

    """
    

def test_how_do_i_make_a_freetext_search_field():
    # language=rst
    """
    .. _Filter.freetext:

    How do I make a freetext search field?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    If you want to filter based on a freetext query on one or more columns we've got a nice little feature for this:


    """
    Table(
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
    This will display one search box to search both `year` and `name` columns.

    """
    

def test_how_do_i_customize_html_attributes__css_classes_or_css_style_specifications():
    # TODO: the code in here is no longer tested!

    # language=rst
    """
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

    """
    

def test_how_do_i_customize_the_rendering_of_a_row():
    # language=rst
    """
    .. _Table.row:

    How do I customize the rendering of a row?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    You can customize the row rendering in two ways:

    - You can modify the html attributes via `row__attrs`. See the question on attrs_

    - Use `row__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object.

    In templates you can access the raw row via `row`. This would typically be one of your model objects. You can also access the cells of the table via `cells`. A naive template for a row would be `<tr>{% for cell in cells %}<td>{{ cell }}{% endfor %}</tr>`. You can access specific cells by their column names like `{{ cells.artist }}`.

    To customize the cell, see `How do I customize the rendering of a cell?`_

    """
    

def test_how_do_i_customize_the_rendering_of_a_header():
    # language=rst
    """
    .. _Column.header:

    How do I customize the rendering of a header?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    You can customize headers in two ways:

    - You can modify the html attributes via `header__attrs`. See the question on attrs_

    - Use `header__template` to specify a template. You can give a string and it will be interpreted as a template name, or you can pass a `Template` object. The default is `iommi/table/table_header_rows.html`.

    """
    

def test_how_do_i_turn_off_the_header():
    # language=rst
    """
    .. _Table.header:

    How do I turn off the header?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Set `header__template` to `None`.


    """
    

def test_how_do_i_add_fields_to_a_table_that_is_generated_from_a_model():
    # language=rst
    """
    How do I add fields to a table that is generated from a model?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    See the question `How do I create a column based on computed data?`_

    """
    

def test_how_do_i_specify_which_columns_to_show():
    # language=rst
    """
    .. _Column.include:

    How do I specify which columns to show?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Just pass `include=False` to hide the column or `include=True` to show it. By default columns are shown, except the primary key column that is by default hidden. You can also pass a callable here like so:


    """
    Table(
        auto__model=Album,
        columns__name__include=
            lambda request, **_: request.GET.get('some_parameter') == 'hello!',
    )

    # language=rst
    """
    This will show the column `name` only if the GET parameter `some_parameter` is set to `hello!`.

    To be more precise, `include` turns off the entire column. Sometimes you want to have the searching turned on, but disable the rendering of the column. To do this use the `render_column` parameter instead.

    """
    

def test_how_do_i_access_table_data_programmatically_():
    # language=rst
    """
    .. _Table.cells_for_rows:

    How do I access table data programmatically (like for example to dump to json)?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Here's a simple example that prints a table to stdout:

    """
    # @test
    Artist.objects.create(name='foo')
    table = Table(auto__model=Artist).bind(request=req('get'))

    for row in table.cells_for_rows():
        for cell in row:
            print(cell.render_formatted(), end='')
        print()


def test_how_do_i_access_foreign_key_related_data_in_a_column():
    # language=rst
    """
    .. _Column.attr:

    How do I access foreign key related data in a column?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Let's say we have two models:


    """
    class Foo(models.Model):
        a = models.IntegerField()

    # @test
        class Meta:
            app_label = 'docs_fk'


    class Bar(models.Model):
        b = models.IntegerField()
        c = models.ForeignKey(Foo, on_delete=models.CASCADE)

    # @test
        class Meta:
            app_label = 'docs_fk'

    # language=rst
    """
    we can build a table of `Bar` that shows the data of `a` like this:


    """
    Table(
        auto__model=Bar,
        columns__a=Column(attr='c__a'),
    )


def test_how_do_i_turn_off_sorting_():
    # language=rst
    """
    .. _Table.sortable:

    .. _Column.sortable:

    How do I turn off sorting? (on a column or table wide)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    To turn off column on a column pass it `sortable=False` (you can also use a lambda here!):


    """
    Table(
        auto__model=Album,
        columns__name__sortable=False,
    )

    # language=rst
    """
    and to turn it off on the entire table:


    """
    Table(
        auto__model=Album,
        sortable=False,
    )


def test_how_do_i_specify_the_title_of_a_header():
    # language=rst
    """
    .. _Column.display_name:

    How do I specify the title of a header?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The `display_name` property of a column is displayed in the header.


    """
    Table(
        auto__model=Album,
        columns__name__display_name='header title',
    )


def test_how_do_i_set_the_default_sort_order_of_a_column_to_be_descending_instead_of_ascending():
    # language=rst
    """
    .. _Column.sort_default_desc:

    How do I set the default sort order of a column to be descending instead of ascending?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    """
    Table(
        auto__model=Album,
        columns__name__sort_default_desc=True,  # or a lambda!
    )


def test_how_do_i_group_columns():
    # language=rst
    """
    .. _Column.group:

    How do I group columns?
    ~~~~~~~~~~~~~~~~~~~~~~~


    """
    Table(
        auto__model=Album,
        columns__name__group='foo',
        columns__year__group='foo',
    )

    # language=rst
    """
    The grouping only works if the columns are next to each other, otherwise you'll get multiple groups. The groups are rendered by default as a second header row above the normal header row with colspans to group the headers.

    """
    

def test_how_do_i_get_rowspan_on_a_table():
    # language=rst
    """
    .. _Column.auto_rowspan:

    How do I get rowspan on a table?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    You can manually set the rowspan attribute via `row__attrs__rowspan` but this is tricky to get right because you also have to hide the cells that are "overwritten" by the rowspan. We supply a simpler method: `auto_rowspan`. It automatically makes sure the rowspan count is correct and the cells are hidden. It works by checking if the value of the cell is the same, and then it becomes part of the rowspan.


    """
    Table(
        auto__model=Album,
        columns__year__auto_rowspan=True,
    )


def test_how_do_i_enable_bulk_editing():
    # language=rst
    """
    .. _Column.bulk:

    How do I enable bulk editing?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Editing multiple items at a time is easy in iommi with the built in bulk
    editing. Enable it for a columns by passing `bulk__include=True`:


    """
    Table(
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
    

def test_how_do_i_enable_bulk_delete():
    # language=rst
    """
    .. _Table.bulk:

    How do I enable bulk delete?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    """
    Table(
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
    

def test_how_do_i_make_a_custom_bulk_action():
    # language=rst
    """
    How do I make a custom bulk action?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
    artist = Artist.objects.create(name='Black Sabbath')
    album = Album.objects.create(artist=artist, name='foo', year=1970)
    r = t.bind(request=req('post', **{'-my_action': '', '_all_pks_': '1'})).render_to_response()
    album.refresh_from_db()
    assert album.name == 'Paranoid'


    

def test_what_is_the_difference_between_attr_and__name():
    # language=rst
    """
    What is the difference between `attr` and `_name`?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    `attr` is the attribute path of the value iommi reads from a row. In the simple case it's just the attribute name, but if you want to read the attribute of an attribute you can use `__`-separated paths for this: `attr='foo__bar'` is functionally equivalent to `cell__value=lambda row, **_: row.foo.bar`. Set `attr` to `None` to not read any attribute from the row.

    `_name` is the name used internally. By default `attr` is set to the value of `_name`. This name is used when accessing the column from `Table.columns` and it's the name used in the GET parameter to sort by that column. This is a required field.
    """
