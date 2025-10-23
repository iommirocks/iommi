# language=rst
"""
.. _title:

.. _h_tag:

`title`/`h_tag`
---------------

The `title` attribute is for setting the title or heading of a component. To customize the exact rendering you use `h_tag`.

"""
from django.template import Template

from docs.models import Artist
from iommi import Form
from iommi.docs import show_output


def test_template_as_path():
    # language=rst
    """
    `title`
    ~~~~~~~

    """

    form = Form.create(
        auto__model=Artist,
        title='Custom title',
    )

    # @test
    show_output(form)
    # @end


def test_template_objects():
    # language=rst
    """
    `h_tag`
    ~~~~~~~
    """

    form = Form.create(
        auto__model=Artist,
        h_tag__attrs__style__background='blue',
    )

    # @test
    show_output(form)
    # @end
