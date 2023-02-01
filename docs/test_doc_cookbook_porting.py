from django.template import RequestContext

from iommi import Page
from iommi._web_compat import (
    HttpResponse,
    Template,
)
from tests.helpers import (
    req,
    show_output,
)


def test_porting():
    # language=rst
    """
    Porting
    -------

    """


def test_existing_views():
    # language=rst
    """
    Existing function based views often have an initial part building a set of values from the view parameters that then is passed on as a context to the template rendering.

    When refactoring this to the more iommi ideomatic style of calculating values in callbacks it can sometimes be helpfull to not have to move everythin at once.

    """

    def some_function(a, b):
        return a + b

    def legacy_view(request, a, b):
        context = dict(a=a, b=b, c=some_function(a, b))
        return HttpResponse(Template('{{a}} + {{b}} = {{c}}').render(RequestContext(request, context)))

    # @test
    show_output(legacy_view(req('get'), a=1, b=2))
    # @end

    # language=rst
    """
    There is a configurable callback, `extra_params`, to provide extra parameters given the parameters already provided by django and the iommi path machinery.
    """

    class IommiPage(Page):
        class Meta:
            @staticmethod
            def extra_params(a, b):
                return dict(
                    c=some_function(a, b),
                )

        content = Template('{{ params.a }} + {{ params.b }} = {{ params.c }}')

    iommi_view = IommiPage().as_view()

    # @test
    show_output(iommi_view(req('get'), a=1, b=2))
    # @end
