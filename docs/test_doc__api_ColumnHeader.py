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
    ColumnHeader
    ============
    
    Base class: `object`
    
    Internal class implementing a column header. For configuration options
    read the docs for :doc:`HeaderConfig`.
    

"""
