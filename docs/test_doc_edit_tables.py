import pytest
from docs.models import *
from iommi import *
from tests.helpers import (
    req,
    show_output,
)

pytestmark = pytest.mark.django_db


request = req('get')


def fill_dummy_data(): pass


def test_edit_tables(really_big_discography):
    # language=rst
    """
    .. _edit-tables:

    Edit tables
    ===========

    iommi edit tables builds on top of iommi tables but enable editing of cells too.

    A simple example:
    """

    # @test
    t = (
    # @end

    EditTable(
        auto__model=Album,
        page_size=10,
        # Turn on the edit feature for the year column
        columns__year__field__include=True,
        # Turn on the delete row feature
        columns__delete=EditColumn.delete(),
    )

    # @test
    )

    show_output(t.bind(request=request))
    # @end
