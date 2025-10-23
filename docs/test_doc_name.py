# language=rst
"""
.. _name:

.. _display_name:

.. _iommi_name:

.. _iommi_path:


`name`/`display_name`/`iommi_path`
-----------------------------------------------

The different name concepts in iommi can be confusing, but each has a logical place.

"""
from docs.models import Track
from iommi import (
    Column,
    Table,
)
from iommi.docs import show_output
from tests.helpers import req
import pytest
pytestmark = pytest.mark.django_db


def test_name():
    # language=rst
    """
    `name`
    ~~~~~~

    The `name` is the name used in configuration for a part:
    """

    class MyTable(Table):
        foo = Column()

    # language=rst
    """
    The `name` is "foo". 
     
    There is a special situation when using deep dunder paths with :ref:`auto`:     
    """

    table = Table(
        auto__model=Track,
        auto__include=[
            'album__artist__name',
        ],
    )

    # @test
    table.bind(request=req('get')).render_to_response()
    # @end

    # language=rst
    """
    Here the `name` of the column is `album_artist_name`, with the double underscore collapsed down to single underscores. This is because otherwise iommi can't know if `__` means "enter the configuration namespace of the `Column` object, or if it means "traverse the foreign key to go from one model to another". So in this situation, to further configure the artist name column, you need the configuration path `columns__album_artist_name`.
    """


def test_display_name():
    # language=rst
    """
    `display_name`
    ~~~~~~~~~~~~~~

    By default iommi will pick up `verbose_name` from your model if you use :ref:`auto`, and if there is no such information, it will take the `name` and capitalize it. If you want to override this you specify `display_name`:

    """

    table = Table(
        auto__model=Track,
        auto__include=[
            'album__artist__name',
        ],
        columns__album_artist_name__display_name='Hello',
    )

    # @test
    show_output(table)
    # @end


def test_iommi_path():
    # language=rst
    """
    `iommi_path`
    ~~~~~~~~~~~~

    The `iommi_path` is used in HTTP dispatching, so AJAX endpoints, and POST requests. Normally you don't need to use this yourself. These paths are `/` separated.

    """


def test_iommi_dunder_path():
    # language=rst
    """
    `iommi_dunder_path`
    ~~~~~~~~~~~~~~~~~~~
    This is useful for finding the full path for an object. It's the value you get with the pick tool, and it's the same as `iommi_path` except `__` replaces `/`.
    """
