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
    Part
    ====
    
    Base class: :doc:`Traversable`
    
    `Part` is the base class for parts of a page that can be rendered as html, and can respond to ajax and post.
    
    See the `howto <https://docs.iommi.rocks/en/latest/cookbook_parts_pages.html#parts-pages>`_ for example usages.
    

Refinable members
-----------------

* `after`
    Type: `Union[int, str]`
    
* `assets`
    Type: `Namespace`
    
* `endpoints`
    Type: `Namespace`
    
* `extra`
    Type: `Dict[str, Any]`
    
* `extra_evaluated`
    Type: `Dict[str, Any]`
    
* `include`
    Type: `bool`
    
* `iommi_style`
    Type: `str`
    

Defaults
^^^^^^^^

* `include`
    * `True`

"""
