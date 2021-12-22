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
    Menu
    ====
    
    Base class: `MenuBase`
    
    Class that describes menus.
    
    Example:
    
    """

    menu = Menu(
        sub_menu=dict(
            root=MenuItem(url='/'),

            albums=MenuItem(url='/albums/'),

            # url defaults to /<name>/ so we
            # don't need to write /musicians/ here
            musicians=MenuItem(),
        ),
    )
# language=rst
"""
    

Refinable members
-----------------

* `after`
    Type: `Union[int, str]`
    
* `assets`
    Type: `Namespace`
    
* `attrs`
    Type: :doc:`Attrs`
    
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
    
* `items_container`
* `sort`
    Type: `bool`
    
* `sub_menu`
    Type: `Dict`
    
* `tag`
    Type: `str`
    
* `template`
    Type: `Union[str, iommi._web_compat.Template]`
    

Defaults
^^^^^^^^

* `sort`
    * `False`

"""
