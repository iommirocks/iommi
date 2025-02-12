# language=rst
"""
.. _endpoints:

`endpoints`
-----------

You can add arbitrary `GET` endpoints with the `endpoints` namespace on any :doc:`Part`.


An endpoint can return an `HttpResponse` directly, or a `Part` (which is
rendered for you); everything else we try to dump to json for you.

Example:

"""
from iommi import (
    html,
    Page,
)
from tests.helpers import req


def test_endpoints():

    page = Page(
        parts__h1=html.h1('Hi!'),
        endpoints__echo__func=lambda value, **_: value,
    )

    # @test
    import json
    request = req('get', **{'/echo': 'foo'})
    response = page.bind(request=request).render_to_response()
    assert json.loads(response.content) == 'foo'
    # @end

    # language=rst
    """
    This page will respond to `?/echo=foo` by returning a json response `"foo"`.    
    """
