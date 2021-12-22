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
    Traversable
    ===========
    
    Base class: `RefinableObject`
    
    Abstract API for objects that have a place in the iommi path structure.
    You should not need to care about this class as it is an implementation
    detail.
    

Refinable members
-----------------

* `assets`
* `endpoints`
* `iommi_style`
    Type: `str`
    

"""
