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
    Query
    =====
    
    Base class: :doc:`Part`
    
    Declare a query language. Example:
    
    """

    class CarQuery(Query):
        make = Filter.choice(choices=['Toyota', 'Volvo', 'Ford'])
        model = Filter()

    query_set = Car.objects.filter(
        CarQuery().bind(request=request).get_q()
    )
# language=rst
"""
    

Refinable members
-----------------

* `advanced`
    Type: `Namespace`
    
* `after`
    Type: `Union[int, str]`
    
* `assets`
    Type: `Namespace`
    
* `auto`
    Type: `Namespace`
    
* `endpoints`
    Type: `Namespace`
    
* `extra`
    Type: `Dict[str, Any]`
    
* `extra_evaluated`
    Type: `Dict[str, Any]`
    
* `filter`
* `filters`
    Type: `Namespace`
    
* `form`
    Type: `Namespace`
    
* `form_class`
* `form_container`
    Type: :doc:`Fragment`
    
* `include`
    Type: `bool`
    
* `iommi_style`
    Type: `str`
    
* `member_class`
* `model`
    Type: `Type[django.db.models.base.Model]`
    
* `postprocess`
* `rows`
* `template`
    Type: `Union[str, iommi._web_compat.Template]`
    

Defaults
^^^^^^^^

* `advanced__call_target`
    * `iommi.query.Advanced`
* `endpoints__errors__func`
    * `iommi.query.default_endpoint__errors`
* `form__attrs`
    * `{'data-iommi-errors': <function Query.<lambda> at 0x1070a8670>}`
* `form_container__attrs__class__iommi_query_form_simple`
    * `True`
* `form_container__call_target`
    * `iommi.fragment.Fragment`
* `form_container__tag`
    * `span`

"""
