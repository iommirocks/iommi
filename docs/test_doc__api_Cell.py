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
    Cell
    ====
    
    Base class: `CellConfig`
    

Refinable members
-----------------

* `attrs`
    Type: :doc:`Attrs`
    
* `contents`
* `format`
    Type: `Callable`
    
* `link`
* `tag`
    Type: `str`
    
* `template`
    Type: `Union[str, iommi._web_compat.Template]`
    
* `url`
    Type: `str`
    
* `url_title`
    Type: `str`
    
* `value`

"""
