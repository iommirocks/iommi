# language=rst
"""
.. _extra_params:


`extra_params`
--------------
"""
from django.template import Template

from iommi import Page
from iommi.docs import show_output
from tests.helpers import req


def test_extra_params():
    # language=rst
    """
    `extra_params` is used to provide extra parameters, on top of the parameters already provided by Django and the iommi path machinery:
    """

    def some_function(a, b):
        return a + b

    class IommiPage(Page):
        class Meta:
            @staticmethod
            def extra_params(request, a, b):
                return dict(
                    c=some_function(a, b),
                )

        content = Template('{{ params.a }} + {{ params.b }} = {{ params.c }}')

    iommi_view = IommiPage().as_view()

    # @test
    show_output(iommi_view(req('get'), a=1, b=2))
    # @end
