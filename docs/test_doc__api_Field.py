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
    Field
    =====
    
    Base class: :doc:`Part`
    
    Class that describes a field, i.e. what input controls to render, the label, etc.
    
    See :doc:`Form` for more complete examples.
    
    The life cycle of the data is:
    1. `raw_data`: will be set if the corresponding key is present in the HTTP request
    2. `parsed_data`: set if parsing is successful, which only happens if the previous step succeeded
    3. `value`: set if validation is successful, which only happens if the previous step succeeded
    

Note that, in addition to the parameters with the defined behavior below, you can pass in any keyword argument you need yourself, including callables that conform to the protocol, and they will be added and evaluated as members.

All these parameters can be callables, and if they are, will be evaluated with the keyword arguments form and field. The only exceptions are `is_valid` (which gets `form`, `field` and `parsed_data`), `render_value` (which takes `form`, `field` and `value`) and `parse` (which gets `form`, `field`, `string_value`). Example of using a lambda to specify a value:

.. code-block:: python

    Field(attrs__id=lambda form, field: 'my_id_%s' % field._name)

Refinable members
-----------------

* `after`
    Set the order of columns, see the `howto <https://docs.iommi.rocks/en/latest/cookbook_forms.html#how-do-i-change-the-order-of-the-fields>`_ for an example.

    Type: `Union[int, str]`
    
    Cookbook: :ref:`field.after`
    
* `assets`
    Type: `Namespace`
    
* `attr`
    The attribute path to apply or get the data from. For example using `foo__bar__baz` will result in `your_instance.foo.bar.baz` will be set by the `apply()` function. Defaults to same as name

    Type: `str`
    
* `attrs`
    A dict containing any custom html attributes to be sent to the `input__template`.

    Type: :doc:`Attrs`
    
    Cookbook: :ref:`field.attrs`
    
* `choice_display_name_formatter`
    Callback given the keyword argument `choice` in addition to standard parameters, to obtain the display name representing a given choice to the end user. Default implementation will use `str(choice)`

    Type: `Callable[..., str]`
    
* `choice_id_formatter`
    Callback given the keyword argument `choice` in addition to standard parameters, to obtain the string value to represent the identity of a given `choice`. Default implementation will use `str(choice)`

    Type: `Callable[..., str]`
    
* `choice_to_optgroup`
    Type: `Optional[Callable[..., Optional[str]]]`
    
* `choice_to_option`
    DEPRECATED: Callback to generate the choice data given a choice value. It will get the keyword arguments `form`, `field` and `choice`. It should return a 4-tuple: `(choice, internal_value, display_name, is_selected)` It is deprecated since it was too complicated and did too much, and has been replaced with `choice_id_formatter` and `choice_display_name_formatter`.

    Type: `Callable[..., Tuple[Any, str, str, bool]]`
    
* `choices`
    Type: `Callable[..., List[Any]]`
    
* `display_name`
    The text in the HTML label tag. Default: `capitalize(name).replace('_', ' ')`

    Type: `str`
    
* `editable`
    Default: `True`

    Type: `bool`
    
    Cookbook: :ref:`field.editable`
    
* `empty_choice_tuple`
    Type: `Tuple[Any, str, str, bool]`
    
* `empty_label`
    Type: `str`
    
* `endpoints`
    Type: `Namespace`
    
* `errors`
    Type: `Errors`
    
* `extra`
    Type: `Dict[str, Any]`
    
* `extra_evaluated`
    Type: `Dict[str, Any]`
    
* `group`
    Type: `str`
    
* `help`
    Type: :doc:`Fragment`
    
* `help_text`
    The help text will be grabbed from the django model if specified and available.

* `include`
    Type: `bool`
    
* `initial`
    Initial value of the field

    Type: `Any`
    
    Cookbook: :ref:`field.initial`
    
* `input`
    Type: :doc:`Fragment`
    
    Cookbook: :ref:`field.input`
    
* `iommi_style`
    Type: `str`
    
* `is_boolean`
    Type: `bool`
    
* `is_list`
    Interpret request data as a list (can NOT be a callable). Default: `False``

    Type: `bool`
    
* `is_valid`
    validation function. Should return a tuple of `(bool, reason_for_failure_if_bool_is_false)` or raise ValidationError. Default: `lambda form, field, parsed_data: (True, '')`

    Cookbook: :ref:`field.is_valid`
    
* `label`
    Type: :doc:`Fragment`
    
* `model`
    Type: `Type[django.db.models.base.Model]`
    
* `model_field`
* `model_field_name`
* `non_editable_input`
    Type: :doc:`Fragment`
    
* `parse`
    Parse function. Default just returns the string input unchanged: `lambda form, field, string_value: string_value`. This function can raise `ValueError` or `ValidationError` to produce a field error message.

    Cookbook: :ref:`field.parse`
    
* `parse_empty_string_as_none`
    Type: `bool`
    
* `parsed_data`
    Type: `Any`
    
* `post_validation`
* `raw_data`
    Type: `str`
    
* `read_from_instance`
    Callback to retrieve value from edited instance. Invoked with parameters field and instance.

* `render_value`
    Render the parsed and validated value into a string. Default just converts to unicode: `lambda form, field, value: unicode(value)`

* `required`
    If the field is a required field. Default: `True`

    Type: `bool`
    
    Cookbook: :ref:`field.required`
    
* `search_fields`
    Cookbook: :ref:`field.search_fields`
    
* `strip_input`
    Runs the input data through standard python .strip() before passing it to the parse function (can NOT be callable). Default: `True`

    Type: `bool`
    
* `tag`
    Type: `str`
    
* `template`
    django template filename for the entire row. Normally you shouldn't need to override on this level. Prefer overriding `input__template`, `label__template` or `error__template` as needed.

    Type: `Union[str, iommi._web_compat.Template]`
    
    Cookbook: :ref:`field.template`
    
* `write_to_instance`
    Callback to write value to instance. Invoked with parameters field, instance and value.


Defaults
^^^^^^^^

* `choice_display_name_formatter`
    * `lambda choice, **_: '%s' % choice`
* `choice_id_formatter`
    * `lambda choice, **_: '%s' % choice`
* `editable`
    * `True`
* `endpoints__config__func`
    * `iommi.form.default_endpoints__config`
* `endpoints__validate__func`
    * `iommi.form.default_endpoints__validate`
* `help__call_target`
    * `iommi.fragment.Fragment`
* `input__attrs__id`
    * `iommi.form.default_input_id`
* `input__attrs__name`
    * `lambda field, **_: field.iommi_path`
* `input__call_target`
    * `iommi.fragment.Fragment`
* `input__extra__placeholder`
    * `""`
* `is_boolean`
    * `False`
* `is_list`
    * `False`
* `label__attrs__for`
    * `iommi.form.default_input_id`
* `label__call_target`
    * `iommi.fragment.Fragment`
* `non_editable_input__attrs__type`
    * `None`
* `non_editable_input__call_target`
    * `iommi.fragment.Fragment`
* `parse_empty_string_as_none`
    * `True`
* `required`
    * `True`
* `strip_input`
    * `True`

Shortcuts
---------

`boolean`
^^^^^^^^^

Defaults
++++++++

* `parse`
    * `iommi.form.bool_parse`
* `required`
    * `False`
* `is_boolean`
    * `True`

`boolean_tristate`
^^^^^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice`
* `choices`
    * `[True, False]`
* `choice_id_formatter`
    * `lambda choice, **_: 'true' if choice else 'false'`
* `choice_display_name_formatter`
    * `lambda choice, **_: gettext('Yes') if choice else gettext('No')`
* `parse`
    * `iommi.form.boolean_tristate__parse`
* `required`
    * `False`

`choice`
^^^^^^^^

Shortcut for single choice field. If required is false it will automatically add an option first with the value '' and the title '---'. To override that text pass in the parameter empty_label.
        :param choice_to_option: callable with three arguments: form, field, choice. Convert from a choice object to a tuple of (choice, value, label, selected), the last three for the <option> element

Defaults
++++++++

* `required`
    * `True`
* `is_list`
    * `False`
* `empty_label`
    * `---`
* `is_valid`
    * `iommi.form.choice_is_valid`
* `input__attrs__multiple`
    * `lambda field, **_: True if field.is_list else None`
* `parse`
    * `iommi.form.choice_parse`

`choice_queryset`
^^^^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice`
* `parse`
    * `iommi.form.choice_queryset__parse`
* `choice_id_formatter`
    * `lambda choice, **_: choice.pk`
* `endpoints__choices__func`
    * `iommi.form.choice_queryset__endpoint_handler`
* `is_valid`
    * `iommi.form.choice_queryset__is_valid`
* `extra__filter_and_sort`
    * `iommi.form.choice_queryset__extra__filter_and_sort`
* `extra__model_from_choices`
    * `iommi.form.choice_queryset__extra__model_from_choices`

`date`
^^^^^^

Defaults
++++++++

* `parse`
    * `iommi.form.date_parse`
* `render_value`
    * `iommi.form.date_render_value`

`datetime`
^^^^^^^^^^

Defaults
++++++++

* `parse`
    * `iommi.form.datetime_parse`
* `render_value`
    * `iommi.form.datetime_render_value`

`decimal`
^^^^^^^^^

Defaults
++++++++

* `parse`
    * `iommi.form.decimal_parse`
* `call_target__attribute`
    * `number`

`email`
^^^^^^^

Defaults
++++++++

* `input__attrs__type`
    * `email`
* `parse`
    * `iommi.form.email_parse`

`file`
^^^^^^

Defaults
++++++++

* `input__attrs__type`
    * `file`
* `raw_data`
    * `iommi.form.file__raw_data`
* `write_to_instance`
    * `iommi.form.file_write_to_instance`

`float`
^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `number`
* `parse`
    * `iommi.form.float_parse`

`foreign_key`
^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice_queryset`

`heading`
^^^^^^^^^

Defaults
++++++++

* `editable`
    * `False`
* `attr`
    * `None`

`hidden`
^^^^^^^^

Defaults
++++++++

* `input__attrs__type`
    * `hidden`
* `attrs__style__display`
    * `none`

`image`
^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `file`
* `template`
    * `iommi/form/image_row.html`

`info`
^^^^^^

Shortcut to create an info entry.

Defaults
++++++++

* `editable`
    * `False`
* `attr`
    * `None`

`integer`
^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `number`
* `parse`
    * `iommi.form.int_parse`

`many_to_many`
^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `multi_choice_queryset`

`multi_choice`
^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice`
* `is_list`
    * `True`

`multi_choice_queryset`
^^^^^^^^^^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice_queryset`
* `is_list`
    * `True`

`number`
^^^^^^^^

`password`
^^^^^^^^^^

Defaults
++++++++

* `input__attrs__type`
    * `password`

`phone_number`
^^^^^^^^^^^^^^

Defaults
++++++++

* `is_valid`
    * `iommi.form.phone_number_is_valid`

`radio`
^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice`
* `input__attrs__id`
    * `None`
* `extra_evaluated__id`
    * `iommi.form.default_input_id`

`text`
^^^^^^

Defaults
++++++++

* `input__attrs__type`
    * `text`

`textarea`
^^^^^^^^^^

Defaults
++++++++

* `input__tag`
    * `textarea`
* `input__attrs__type`
    * `None`
* `input__attrs__value`
    * `None`
* `input__attrs__readonly`
    * `lambda field, **_: True if field.editable is False else None`
* `input__children__text`
    * `lambda field, **_: field.rendered_value`

`time`
^^^^^^

Defaults
++++++++

* `parse`
    * `iommi.form.time_parse`
* `render_value`
    * `iommi.form.time_render_value`

`url`
^^^^^

Defaults
++++++++

* `input__attrs__type`
    * `url`
* `parse`
    * `iommi.form.url_parse`

"""
