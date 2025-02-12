# language=rst
"""

.. _template:

`template`
----------

With the :ref:`philosophy of escape hatches <escape-hatches>`, at the edge we enable replacing the entire rendering of components with the `template` config. You can use it in `Table` cells, to render table rows, to replace the rendering of fields, inputs, headers, and more. The `template` argument supports two types of values:

"""
from django.template import Template

from docs.models import Artist
from iommi import Form
from tests.helpers import show_output


def test_template_as_path():
    # language=rst
    """
    Template path
    ~~~~~~~~~~~~~

    Strings are interpreted as template paths:
    """

    form = Form.create(
        auto__model=Artist,
        fields__name__template='test_template_as_path.html',
    )

    # @test
    show_output(form)
    # @end


def test_template_objects():
    # language=rst
    """
    `Template` object
    ~~~~~~~~~~~~~~~~~

    Pass a Django `Template` object to write the template code you want inline:
    """

    form = Form.create(
        auto__model=Artist,
        fields__name__template=Template('template contents <b>here</b>'),
    )

    # @test
    show_output(form)
    # @end
