from django.template import Template

from docs.models import Album
from iommi import (
    Action,
    Column,
    Field,
    Filter,
    Form,
    Page,
    Query,
    Table,
)
from iommi.docs import show_output
from tests.helpers import req

request = req('get')

import pytest
pytestmark = pytest.mark.django_db


def test_general():
    # language=rst
    """
    General
    -------

    """


# noinspection PyUnusedLocal
def test_how_do_i_find_the_path_to_a_parameter():
    # language=rst
    """
    How do I find the path to a parameter?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Navigating the namespaces can sometimes feel a bit daunting. To help with
    this iommi has a special debug mode that can help a lot. By default it's
    set to settings.DEBUG, but to set it explicitly put this in your settings:


    """
    IOMMI_DEBUG = True

    # language=rst
    """
    Now iommi will output `data-iommi-path` attributes in the HTML that will
    help you find the path to stuff to configure. E.g. in the kitchen
    sink table example a cell looks like this:

    .. code-block:: html

        <td data-iommi-path="columns__e__cell">explicit value</td>

    To customize this cell you can pass for example
    `columns__e__cell__format=lambda value, **_: value.upper()`. 
    
    Instead of looking at the DOM, you can use the "pick" tool where you can get
    the path by clicking on the item you want. You will also get a link to the 
    right place into the API docs for the thing you clicked on. 

    Another nice way to find what is available is to append `?/debug_tree` in the
    url of your view. You will get a table of available paths with the ajax
    endpoint path, and their types with links to the appropriate documentation.

    If `IOMMI_DEBUG` is on you will also get the iommi debug toolbar on your pages.
    `Code` will jump to the code for the current view
    in PyCharm. You can configure the URL builder to make it open your favored
    editor by setting `IOMMI_DEBUG_URL_BUILDER` in settings:


    """
    IOMMI_DEBUG_URL_BUILDER = lambda filename, lineno: f'my_editor://{filename}:{lineno}'

    # language=rst
    """
    Visual Studio Code example:


    """
    IOMMI_DEBUG_URL_BUILDER = lambda filename, lineno: f"vscode://file/{filename}:{lineno}:0"

    # language=rst
    """
    The `Tree` link will open the `?/debug_tree` page mentioned above.

    """
    # @test
    assert True  # Until I come up with a nice way to test this
    # @end


def test_access_other_component(album):
    # language=rst
    """
    How do I access a sibling component?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Let's say we have a `Page` with a form and a custom template, and we want
    to access the form, we can do that via the `root` object:
    """

    class MyPage(Page):
        edit_album = Form.edit(auto__model=Album, instance=album)
        view_album = Template('''
            {{ root.parts.edit_album.fields.name.value }}
        ''')

    # @test
    show_output(MyPage())
    # @end


def test_how_do_i_use_a_custom_class_for_the_members_of_a_component(small_discography):
    # language=rst
    """
    .. _custom-member-class:

    How do I use a custom class for the columns/fields/filters of a component?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Table.member_class
    .. uses EditTable.member_class
    .. uses Form.member_class
    .. uses Query.member_class
    .. uses Page.member_class
    .. uses Table.form_class
    .. uses EditTable.form_class
    .. uses Query.form_class
    .. uses Table.query_class
    .. uses EditTable.query_class

    A `Table` creates `Column` instances, a `Form` creates `Field` instances and a
    `Query` creates `Filter` instances. If you have a custom subclass that you want
    iommi to use instead when it auto-generates members from a model, set
    `member_class`:
    """

    class MyColumn(Column):
        pass

    class MyTable(Table):
        class Meta:
            member_class = MyColumn

    table = MyTable(auto__model=Album)

    # @test
    show_output(table)
    assert isinstance(table.bind(request=req('get')).columns.name, MyColumn)
    # @end

    # language=rst
    """
    A `Table` also has a nested `Form` (used for bulk editing and create) and a nested
    `Query` (used for filtering). Swap those out with `form_class` and `query_class`, and
    the `Form` that a `Query` builds for its filters with `form_class`:
    """

    class MyField(Field):
        pass

    class MyForm(Form):
        class Meta:
            member_class = MyField

    class MyFilter(Filter):
        pass

    class MyQuery(Query):
        class Meta:
            member_class = MyFilter
            form_class = MyForm

    class MyTable2(Table):
        class Meta:
            member_class = MyColumn
            form_class = MyForm
            query_class = MyQuery

    # @test
    bound = MyTable2(auto__model=Album, columns__name__bulk__include=True).bind(request=req('get'))
    assert isinstance(bound.query, MyQuery)
    assert isinstance(bound.query.form, MyForm)
    assert isinstance(bound.bulk, MyForm)
    # @end

    # language=rst
    """
    .. uses Form.action_class
    .. uses Form.page_class

    The same pattern applies to the other parts a component builds. A `Form` uses
    `action_class` for its actions and `page_class` for when it is rendered as a
    standalone page:
    """

    class MyAction(Action):
        pass

    class MyForm2(Form):
        class Meta:
            action_class = MyAction

    # @test
    assert MyForm2(auto__model=Album).bind(request=req('get'))
    # @end
