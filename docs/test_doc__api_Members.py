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
    Members
    =======
    
    Base class: :doc:`Traversable`
    
    Internal iommi class that holds members of another class, for example the columns of a `Table` instance.
    

Refinable members
-----------------

* `assets`
* `endpoints`
* `iommi_style`
    Type: `str`
    

"""
