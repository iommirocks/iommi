from docs.models import *
from iommi import *
from iommi.docs import show_output
from tests.helpers import req

request = req('get')

from tests.helpers import req
import pytest
pytestmark = pytest.mark.django_db


def test_tables():
    # language=rst
    """
    Edit tables
    -----------

    """


def test_how_do_you_edit_one_to_one_in_a_table(black_sabbath):
    # language=rst
    """
    .. _edit-table-one-to-one:

    How do you edit one-to-one fields in an edit table?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses EditColumn.field
    .. uses EditColumn.columns
    .. uses EditColumn.auto

    Include them in `auto__include`. Say you have a profile model for an artist:
    """

    # @test
    profile = Profile.objects.create(artist=black_sabbath)
    # @end

    # language=rst
    """
    Then you can include the artist name field:
    """

    edit_table = EditTable(
        auto__model=Profile,
        auto__include=['artist__name'],
        columns__artist_name__field__include=True,
    )

    # @test
    show_output(edit_table)
    # @end

    # @test
    bound = edit_table.bind(
        request=req(
            'POST',
            **{
                f'columns/artist_name/{profile.pk}': 'new name',
                '-save': '',
            },
        )
    )
    response = bound.render_to_response()
    assert not edit_table.get_errors()
    assert response.status_code == 302, response.content.decode()
    assert Artist.objects.get(pk=black_sabbath.pk).name == 'new name'
    # @end


def test_how_do_i_change_delete_to_checkboxes(ozzy):
    # language=rst
    """
    .. _edit-table-delete-as-checkbox:

    How do I change the delete buttons to checkboxes?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Just add `data-iommi-edit-table-delete-with="checkbox"`:
    """

    # @test
    Profile.objects.create(artist=ozzy)
    # @end

    edit_table = EditTable(
        auto__model=Profile,
        auto__include=['artist__name'],
        columns__artist_name__field__include=True,
        columns__delete=EditColumn.delete(),
        **{
            'attrs__data-iommi-edit-table-delete-with': 'checkbox',
        }
    )

    # @test
    show_output(edit_table)
    # @end


def test_how_do_i_include_labels_for_fields(ozzy):
    # language=rst
    """
    .. _edit-table-include-field-labels:

    How do I include labels for fields?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    If you're using `EditTable` and not `EditTable.div`, then by default you get fields rendered without labels,
    because the label text is in the table header. But in case you still want to render labels (e.g. as floating labels),
    you can just set `extra_evaluated__input_labels_include = True`:
    """

    # @test
    Profile.objects.create(artist=ozzy)
    # @end

    edit_table = EditTable(
        auto__model=Profile,
        auto__include=['artist__name'],
        columns__artist_name__field__include=True,
        extra_evaluated__input_labels_include=True,
    )

    # @test
    show_output(edit_table)
    # @end


def test_how_do_i_let_users_reorder_rows(fav_artists):
    # language=rst
    """
    .. _edit-table-reorderable:

    How do I let users drag to reorder rows?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses EditTable.reorderable

    The easiest way to make a manually reorderable table is to inherit from `iommi.models.Orderable`.
    This gives your model a `sort_order` field, a default `order_by` set on the model to sort on that field,
    and that field has the `iommi.model_fields.SortOrderField` which is mapped to the correct column type automatically.
    If you do this then set `reorderable=True` on an `EditTable` to get drag-and-drop reordering
    of the rows. You can also pass a dict of `SortableJS` options instead of `True`:
    """

    edit_table = EditTable(
        auto__model=FavoriteArtist,
        auto__include=['artist__name', 'comment', 'sort_order'],
        columns__comment__field__include=True,
        reorderable=True,
        sortable=False,
    )

    # @test
    show_output(edit_table)
    # @end


def test_how_do_i_configure_the_edit_and_create_forms(black_sabbath):
    # language=rst
    """
    .. _edit-table-forms:

    How do I configure the edit and create forms of an edit table?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses EditTable.edit_form
    .. uses EditTable.create_form

    An `EditTable` builds two forms behind the scenes: `edit_form` for the existing
    rows and `create_form` for new rows added via "Add row". Both are configured
    through the matching namespaces:
    """

    edit_table = EditTable(
        auto__model=Album,
        columns__name__field__include=True,
        columns__year__field__include=True,
        create_form__title='Add an album',
    )

    # @test
    show_output(edit_table)
    bound = edit_table.bind(request=req('get'))
    assert set(bound.edit_form.fields.keys()) >= {'name', 'year'}
    assert str(bound.create_form.title) == 'Add an album'
    # @end


def test_how_do_i_customize_the_edit_table_actions(black_sabbath):
    # language=rst
    """
    .. _edit-table-actions:

    How do I customize the Save and Add row actions?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses EditTable.edit_actions

    The buttons below an `EditTable` (`save` and `add_row`) live in the `edit_actions` namespace.
    You can rename, restyle, hide or add buttons via this namespace. For example, to hide the "Add row"
    button so users can only edit existing rows:
    """

    edit_table = EditTable(
        auto__model=Album,
        columns__name__field__include=True,
        edit_actions__add_row__include=False,
    )

    # @test
    show_output(edit_table)
    # @end


def test_how_do_i_set_defaults_on_newly_added_rows(black_sabbath):
    # language=rst
    """
    .. _edit-table-preprocess-create:

    How do I set defaults on newly added rows?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses EditTable.preprocess_row_for_create

    When a user adds a row, iommi creates a blank instance for it. Use
    `preprocess_row_for_create` to fill in defaults on that instance, for example a
    foreign key that isn't one of the editable columns:
    """

    def preprocess_row_for_create(row, **_):
        row.artist = black_sabbath
        return row

    edit_table = EditTable(
        auto__model=Album,
        columns__name__field__include=True,
        columns__year__field__include=True,
        preprocess_row_for_create=preprocess_row_for_create,
    )

    # @test
    show_output(edit_table)

    # Simulate the user having added one new row (virtual pk -1): the instance for it
    # runs through our hook, so its artist is already set before saving.
    bound = edit_table.bind(
        request=req('post', **{'columns/name/-1': 'Master of Reality', 'columns/year/-1': '1971'}),
    )
    new_rows = [cells.row for cells in bound.cells_for_rows_for_create()]
    assert [row.artist for row in new_rows] == [black_sabbath]
    # @end


def test_how_do_i_nest_an_edit_table_in_a_form(black_sabbath):
    # language=rst
    """
    .. _edit-table-parent-form:

    How do I nest an edit table inside a form?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses EditTable.parent_form

    Declare an `EditTable` as an attribute of a `Form` and it becomes a nested form.
    iommi sets `parent_form` on the edit table for you, and saving the outer form
    (with the `save_nested_forms` post handler) saves the edit table too:
    """

    from iommi.form import save_nested_forms

    class AlbumsTable(EditTable):
        class Meta:
            auto__model = Album
            auto__include = ['name', 'year']
            columns__name__field__include = True
            columns__year__field__include = True

    class MyForm(Form):
        albums = AlbumsTable()

        class Meta:
            actions__submit__post_handler = save_nested_forms

    # @test
    bound = MyForm().bind(request=req('get'))
    assert bound.nested_forms.albums.parent_form is bound
    show_output(bound)
    # @end
