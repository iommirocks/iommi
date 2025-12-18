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
