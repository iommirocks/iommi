from docs.models import Track
from iommi import (
    Column,
    Field,
    Form,
    Table,
)
from iommi.docs import show_output
import pytest
pytestmark = pytest.mark.django_db

# language=rst
"""
.. _attr:

`attr`
------

`attr` is the configuration for specifying what Python attribute is read from or written to. Set it to `None` to make a `Field`/`Column`/etc that does not write or read from an attribute on the objects it works on. This is useful for displaying computed data without needing to pollute your model class with single use methods.
"""


def test_name_attr_default():
    # language=rst
    """
    `attr` defaults to the `name`, so this:
    """

    class MyForm(Form):
        foo = Field()

    # language=rst
    """
    is the same as:
    """

    class MyForm(Form):
        foo = Field(attr='foo')


def test_attr_dunder_paths(big_discography):
    # language=rst
    """
    `attr` values can be dunder paths:
    """

    class TrackTable(Table):
        artist_name = Column(attr='album__artist__name')

        class Meta:
            auto__model = Track
            auto__include = []

    # @test
    show_output(TrackTable())
    # @end

    # language=rst
    """
    (Although this example is more idiomatically written with `auto`)
    """
