# language=rst
"""
.. _include:

`include`
---------

The `include` configuration is used to include or exclude parts programmatically. Let's start with a simple example of a table:
"""

from docs.models import (
    Album,
    Artist,
)
from iommi import Table
from iommi.docs import show_output
import pytest
pytestmark = pytest.mark.django_db

def test_include():
    table = Table(
        auto__model=Album,
    )

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    We could make the `name` column only visible for staff users:
    """

    table = Table(
        auto__model=Album,
        columns__name__include=lambda user, **_: user.is_staff,
    )

    # @test
    show_output(table)
    # @end
