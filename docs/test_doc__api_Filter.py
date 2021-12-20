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
    Filter
    ======
    
    Base class: :doc:`Part`
    
    Class that describes a filter that you can search for.
    
    See :doc:`Query` for more complete examples.
    

Parameters with the prefix `field__` will be passed along downstream to the `Field` instance if applicable. This can be used to tweak the basic style interface.

Refinable members
-----------------

* `after`
    Type: `Union[int, str]`
    
* `assets`
    Type: `Namespace`
    
* `attr`
* `choices`
* `endpoints`
    Type: `Namespace`
    
* `extra`
    Type: `Dict[str, Any]`
    
* `extra_evaluated`
    Type: `Dict[str, Any]`
    
* `field`
    Type: `Namespace`
    
* `freetext`
    Cookbook: :ref:`filter.freetext`
    
* `include`
    Type: `bool`
    
* `iommi_style`
    Type: `str`
    
* `is_valid_filter`
* `model`
    Type: `Type[django.db.models.base.Model]`
    
* `model_field`
* `model_field_name`
* `parse`
* `query_name`
* `query_operator_for_field`
    Type: `str`
    
* `query_operator_to_q_operator`
    Cookbook: :ref:`filter.query_operator_to_q_operator`
    
* `search_fields`
* `unary`
* `value_to_q`
    Cookbook: :ref:`filter.value_to_q`
    

Defaults
^^^^^^^^

* `field__required`
    * `False`
* `is_valid_filter`
    * `iommi.query.default_filter__is_valid_filter`
* `query_name`
    * `lambda filter, **_: filter.iommi_name()`
* `query_operator_for_field`
    * `=`

Shortcuts
---------

`boolean`
^^^^^^^^^

Defaults
++++++++

* `field__call_target__attribute`
    * `boolean`
* `parse`
    * `iommi.form.bool_parse`
* `unary`
    * `True`
* `query_operator_to_q_operator`
    * `iommi.query.boolean__query_operator_to_q_operator`

`boolean_tristate`
^^^^^^^^^^^^^^^^^^

Defaults
++++++++

* `field__call_target__attribute`
    * `boolean_tristate`
* `parse`
    * `iommi.form.boolean_tristate__parse`
* `query_operator_to_q_operator`
    * `iommi.query.boolean__query_operator_to_q_operator`
* `unary`
    * `True`

`case_sensitive`
^^^^^^^^^^^^^^^^

Defaults
++++++++

* `query_operator_to_q_operator`
    * `iommi.query.case_sensitive_query_operator_to_q_operator`

`choice`
^^^^^^^^

Field that has one value out of a set.
        :type choices: list

Defaults
++++++++

* `field__call_target__attribute`
    * `choice`

`choice_queryset`
^^^^^^^^^^^^^^^^^

Field that has one value out of a set.

Defaults
++++++++

* `field__call_target__attribute`
    * `choice_queryset`
* `query_operator_to_q_operator`
    * `lambda op: 'exact'`
* `value_to_q`
    * `iommi.query.choice_queryset_value_to_q`
* `is_valid_filter`
    * `iommi.query.choice_queryset__is_valid_filter`

`date`
^^^^^^

Defaults
++++++++

* `field__call_target__attribute`
    * `date`
* `parse`
    * `iommi.form.date_parse`

`datetime`
^^^^^^^^^^

Defaults
++++++++

* `field__call_target__attribute`
    * `datetime`
* `parse`
    * `iommi.form.datetime_parse`

`decimal`
^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `number`
* `field__call_target__attribute`
    * `decimal`

`email`
^^^^^^^

Defaults
++++++++

* `field__call_target__attribute`
    * `email`

`file`
^^^^^^

Defaults
++++++++

* `field__call_target__attribute`
    * `file`

`float`
^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `number`
* `field__call_target__attribute`
    * `float`
* `parse`
    * `iommi.form.float_parse`

`foreign_key`
^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice_queryset`
* `field__call_target__attribute`
    * `foreign_key`

`integer`
^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `number`
* `field__call_target__attribute`
    * `integer`
* `parse`
    * `iommi.form.int_parse`

`many_to_many`
^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `multi_choice_queryset`
* `field__call_target__attribute`
    * `many_to_many`

`multi_choice`
^^^^^^^^^^^^^^

Field that has one value out of a set.
        :type choices: list

Defaults
++++++++

* `field__call_target__attribute`
    * `multi_choice`

`multi_choice_queryset`
^^^^^^^^^^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice_queryset`
* `field__call_target__attribute`
    * `multi_choice_queryset`

`number`
^^^^^^^^

Defaults
++++++++

* `field__call_target__attribute`
    * `number`

`text`
^^^^^^

Defaults
++++++++

* `field__call_target__attribute`
    * `text`
* `query_operator_for_field`
    * `:`

`textarea`
^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `text`

`time`
^^^^^^

Defaults
++++++++

* `field__call_target__attribute`
    * `time`
* `parse`
    * `iommi.form.time_parse`

`url`
^^^^^

Defaults
++++++++

* `field__call_target__attribute`
    * `url`

"""
