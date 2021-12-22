# NOTE: this file is automaticallly generated

from iommi import *
from iommi.admin import Admin
from django.urls import (
    include,
    path,
)
from django.db import models
from tests.helpers import req, user_req, staff_req
from docs.models import *
request = req('get')


def test_class_doc():
    # language=rst
    """
    Endpoint
    ========
    
    Base class: :doc:`Traversable`
    
    Class that describes an endpoint in iommi. You can create your own custom
    endpoints on any :doc:`Part`.
    
    Example:
    
    """

    def my_view(request):
        return Page(
            parts__h1=html.h1('Hi!'),
            endpoints__echo__func=lambda value, **_: value,
        )

    # @test
    import json
    request = req('get', **{'/echo': 'foo'})
    response = my_view(request).bind(request=request).render_to_response()
    assert json.loads(response.content) == 'foo'
    # @end

    # language=rst
    """
    this page will respond to `?/echo=foo` by returning a json response `"foo"`.
    
    An endpoint can return an HttpResponse directly, a `Part` which is rendered for you,
    and everything else we try to dump to json for you.
    

Refinable members
-----------------

* `assets`
* `endpoints`
* `func`
    Type: `Callable`
    
* `include`
    Type: `bool`
    
* `iommi_style`
    Type: `str`
    

Defaults
^^^^^^^^

* `include`
    * `True`

"""
