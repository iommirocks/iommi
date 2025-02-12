# language=rst
"""
.. _fragments:

Fragments
---------

If you are just using iommi's built in components like `Form` and `Table`, you won't need to use `Fragment` directly. `Fragment` is a class that is used to compose HTML tags in a way that is later :ref:`refinable`. The most basic example of this is the :ref:`h_tag <h_tag>` of a form or table. A `Fragment` has :ref:`attrs <attributes>`, :ref:`template` and :ref:`tag` configuration:
"""
from docs.models import Artist
from tests.helpers import show_output
from iommi import Table
import pytest
pytestmark = pytest.mark.django_db


def test_fragment():
    table = Table(
        auto__model=Artist,
        h_tag__attrs__style__background='blue',
    )

    # @test
    show_output(table)
    # @end

    # language=rst
    """
    See the API reference for :doc:`Fragment` for more details. 
    """
