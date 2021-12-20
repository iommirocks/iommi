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
    Header
    ======
    
    Base class: :doc:`Fragment`
    
    `Header` is a special fragment that automatically calculates its level.
    This means that you will get `h1` for the top level, `h2` for the next level,
    and so on. If you want a specific `h1`/`h2`/etc tag use `Fragment`.
    
    The header level is only increased by the existence of `Header` objects,
    so putting a manual `h1` somewhere won't make the next `Header` into a
    `h2` tag.
    

Refinable members
-----------------

* `after`
    Type: `Union[int, str]`
    
* `assets`
    Type: `Namespace`
    
* `attrs`
    Type: :doc:`Attrs`
    
* `children`
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
    
* `tag`
* `template`
    Type: `Union[str, iommi._web_compat.Template]`
    

Defaults
^^^^^^^^


"""
