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
    MenuItem
    ========
    
    Base class: `MenuBase`
    
    Class that is used for the clickable menu items in a menu.
    
    See :doc:`Menu` for more complete examples.
    

Refinable members
-----------------

* `a`
* `active_class`
* `after`
    Type: `Union[int, str]`
    
* `assets`
    Type: `Namespace`
    
* `attrs`
    Type: :doc:`Attrs`
    
* `display_name`
    Type: `str`
    
* `endpoints`
    Type: `Namespace`
    
* `extra`
    Type: `Dict[str, Any]`
    
* `extra_evaluated`
    Type: `Dict[str, Any]`
    
* `group`
    Type: `str`
    
* `include`
    Type: `bool`
    
* `iommi_style`
    Type: `str`
    
* `regex`
    Type: `str`
    
* `sort`
    Type: `bool`
    
* `sub_menu`
    Type: `Dict`
    
* `tag`
    Type: `str`
    
* `template`
    Type: `Union[str, iommi._web_compat.Template]`
    
* `url`
    Type: `str`
    

Defaults
^^^^^^^^

* `display_name`
    * `lambda menu_item, **_: capitalize(menu_item.iommi_name()).replace('_', ' ')`
* `regex`
    * `lambda menu_item, **_: '^' + str(menu_item.url) if menu_item.url else None`
* `url`
    * `lambda menu_item, **_: '/'`

"""
