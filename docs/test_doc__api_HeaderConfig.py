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
    HeaderConfig
    ============
    
    Base class: :doc:`Traversable`
    

Refinable members
-----------------

* `assets`
* `attrs`
    Type: :doc:`Attrs`
    
* `endpoints`
* `extra`
    Type: `Dict[str, Any]`
    
* `extra_evaluated`
    Type: `Dict[str, Any]`
    
* `iommi_style`
    Type: `str`
    
* `template`
    Type: `Union[str, iommi._web_compat.Template]`
    
* `url`

"""
