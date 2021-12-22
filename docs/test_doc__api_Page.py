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
    Page
    ====
    
    Base class: :doc:`Part`
    
    A page is used to compose iommi parts into a bigger whole.
    
    See the `howto <https://docs.iommi.rocks/en/latest/cookbook_parts_pages.html#parts-pages>`_ for example usages.
    

Refinable members
-----------------

* `after`
    Type: `Union[int, str]`
    
* `assets`
    Type: `Namespace`
    
* `context`
    Cookbook: :ref:`page.context`
    
* `endpoints`
    Type: `Namespace`
    
* `extra`
    Type: `Dict[str, Any]`
    
* `extra_evaluated`
    Type: `Dict[str, Any]`
    
* `h_tag`
    Type: `Union[iommi.fragment.Fragment, str]`
    
* `include`
    Type: `bool`
    
* `iommi_style`
    Type: `str`
    
* `member_class`
    Type: `Type[iommi.fragment.Fragment]`
    
* `parts`
    Type: `Dict[str, Union[iommi.part.Part, str, iommi._web_compat.Template]]`
    
* `title`
    Type: `str`
    
    Cookbook: :ref:`page.title`
    

Defaults
^^^^^^^^

* `include`
    * `True`

"""
