# language=rst
"""
.. _iommi_style:

`iommi_style`
-------------

The :ref:`style` system is what you normally use to specify how your product should look and behave, but something you want something more limited for just one or a few places. You can then specify a :doc:`Style` object directly on a component:

"""
from docs.models import Album
from iommi import (
    Form,
    Style,
)
from iommi.docs import show_output
import pytest
pytestmark = pytest.mark.django_db


def test_iommi_style(small_discography):
    from iommi.style_bootstrap5 import bootstrap5
    form = Form(
        auto__model=Album,
        iommi_style=Style(
            bootstrap5,  # Based on the bootstrap style
            Field=dict(
                input__attrs__style__background='blue',
            )
        )
    )

    # @test
    show_output(form)
    # @end
