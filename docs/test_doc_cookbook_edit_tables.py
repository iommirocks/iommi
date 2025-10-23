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

    profile = Profile.objects.create(artist=black_sabbath)

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


def test_how_do_I_change_delete_to_checkboxes():
    # language=rst
    """
    .. _edit-table-delete-as-checkbox:

    How do I change the delete buttons to checkboxes?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Just add `data-iommi-edit-table-delete-with="checkbox"`:
    """

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
