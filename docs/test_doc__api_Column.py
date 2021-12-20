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
    Column
    ======
    
    Base class: :doc:`Part`
    
    Class that describes a column, i.e. the text of the header, how to get and display the data in the cell, etc.
    
    See :doc:`Table` for more complete examples.
    

Parameters with the prefix `filter__` will be passed along downstream to the `Filter` instance if applicable. This can be used to tweak the filtering of a column.

Refinable members
-----------------

* `after`
    Set the order of columns, see the `howto on ordering <https://docs.iommi.rocks/en/latest/cookbook_tables.html#how-do-i-reorder-columns>`_ for an example.

    Type: `Union[int, str]`
    
    Cookbook: :ref:`column.after`
    
* `assets`
    Type: `Namespace`
    
* `attr`
    What attribute to use, defaults to same as name. Follows django conventions to access properties of properties, so `foo__bar` is equivalent to the python code `foo.bar`. This parameter is based on the filter name of the Column if you use the declarative style of creating tables.

    Type: `str`
    
    Cookbook: :ref:`column.attr`
    
* `auto_rowspan`
    enable automatic rowspan for this column. To join two cells with rowspan, just set this `auto_rowspan` to `True` and make those two cells output the same text and we'll handle the rest.

    Type: `bool`
    
    Cookbook: :ref:`column.auto_rowspan`
    
* `bulk`
    Namespace to configure bulk actions. See `howto on bulk editing <https://docs.iommi.rocks/en/latest/cookbook_tables.html#how-do-i-enable-bulk-editing>`_ for an example and more information.

    Type: `Namespace`
    
    Cookbook: :ref:`column.bulk`
    
* `cell`
    Customize the cell, see See `howto on rendering <https://docs.iommi.rocks/en/latest/cookbook_tables.html#how-do-i-customize-the-rendering-of-a-cell>`_ and `howto on links <https://docs.iommi.rocks/en/latest/cookbook_tables.html#how-do-i-make-a-link-in-a-cell>`_

    Type: `Namespace`
    
* `choices`
    Type: `Iterable`
    
* `data_retrieval_method`
* `display_name`
    the text of the header for this column. By default this is based on the `_name` so normally you won't need to specify it.

    Cookbook: :ref:`column.display_name`
    
* `endpoints`
    Type: `Namespace`
    
* `extra`
    Type: `Dict[str, Any]`
    
* `extra_evaluated`
    Type: `Dict[str, Any]`
    
* `filter`
    Type: `Namespace`
    
    Cookbook: :ref:`column.filter`
    
* `group`
    string describing the group of the header. If this parameter is used the header of the table now has two rows. Consecutive identical groups on the first level of the header are joined in a nice way.

    Type: `Optional[str]`
    
    Cookbook: :ref:`column.group`
    
* `header`
    Type: `Namespace`
    
    Cookbook: :ref:`column.header`
    
* `include`
    set this to `False` to hide the column

    Type: `bool`
    
    Cookbook: :ref:`column.include`
    
* `iommi_style`
    Type: `str`
    
* `model`
    Type: `Type[django.db.models.base.Model]`
    
* `model_field`
* `model_field_name`
* `render_column`
    If set to `False` the column won't be rendered in the table, but still be available in `table.columns`. This can be useful if you want some other feature from a column like filtering.

    Type: `bool`
    
* `sort_default_desc`
    Set to `True` to make table sort link to sort descending first.

    Type: `bool`
    
    Cookbook: :ref:`column.sort_default_desc`
    
* `sort_key`
    string denoting what value to use as sort key when this column is selected for sorting. (Or callable when rendering a table from list.)

* `sortable`
    set this to `False` to disable sorting on this column

    Type: `bool`
    
    Cookbook: :ref:`column.sortable`
    
* `superheader`

Defaults
^^^^^^^^

* `auto_rowspan`
    * `False`
* `bulk__include`
    * `False`
* `cell__format`
    * `iommi.table.default_cell_formatter`
* `cell__template`
    * `None`
* `cell__url`
    * `None`
* `cell__url_title`
    * `None`
* `cell__value`
    * `iommi.table.default_cell__value`
* `data_retrieval_method`
    * `DataRetrievalMethods.attribute_access`
* `header__attrs__class__ascending`
    * `lambda column, **_: column.sort_direction == ASCENDING`
* `header__attrs__class__descending`
    * `lambda column, **_: column.sort_direction == DESCENDING`
* `header__attrs__class__first_column`
    * `lambda header, **_: header.index_in_group == 0`
* `header__attrs__class__sorted`
    * `lambda column, **_: column.is_sorting`
* `header__attrs__class__subheader`
    * `True`
* `header__template`
    * `iommi/table/header.html`
* `header__url`
    * `None`
* `render_column`
    * `True`
* `sort_default_desc`
    * `False`
* `sortable`
    * `lambda column, **_: column.attr is not None`

Shortcuts
---------

`boolean`
^^^^^^^^^

Shortcut to render booleans as a check mark if true or blank if false.

Defaults
++++++++

* `filter__call_target__attribute`
    * `boolean`
* `filter__field__call_target__attribute`
    * `boolean_tristate`
* `bulk__call_target__attribute`
    * `boolean`
* `cell__format`
    * `lambda value, **_: mark_safe('<i class="fa fa-check" title="Yes"></i>') if value else ''`

`boolean_tristate`
^^^^^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `boolean`
* `filter__call_target__attribute`
    * `boolean_tristate`

`choice`
^^^^^^^^

Defaults
++++++++

* `bulk__call_target__attribute`
    * `choice`
* `filter__call_target__attribute`
    * `choice`

`choice_queryset`
^^^^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice`
* `bulk__call_target__attribute`
    * `choice_queryset`
* `filter__call_target__attribute`
    * `choice_queryset`

`date`
^^^^^^

Defaults
++++++++

* `filter__call_target__attribute`
    * `date`
* `filter__query_operator_to_q_operator`
    * `lambda op: {'=': 'exact', ':': 'contains'}.get(op)`
* `bulk__call_target__attribute`
    * `date`

`datetime`
^^^^^^^^^^

Defaults
++++++++

* `filter__call_target__attribute`
    * `datetime`
* `filter__query_operator_to_q_operator`
    * `lambda op: {'=': 'exact', ':': 'contains'}.get(op)`
* `bulk__call_target__attribute`
    * `datetime`

`decimal`
^^^^^^^^^

Defaults
++++++++

* `bulk__call_target__attribute`
    * `decimal`
* `filter__call_target__attribute`
    * `decimal`

`delete`
^^^^^^^^

Shortcut for creating a clickable delete icon. The URL defaults to `your_object.get_absolute_url() + 'delete/'`. Specify the option cell__url to override.

Defaults
++++++++

* `call_target__attribute`
    * `icon`
* `cell__url`
    * `lambda row, **_: row.get_absolute_url() + 'delete/'`
* `display_name`
    * `Delete`

`download`
^^^^^^^^^^

Shortcut for creating a clickable download icon. The URL defaults to `your_object.get_absolute_url() + 'download/'`. Specify the option cell__url to override.

Defaults
++++++++

* `call_target__attribute`
    * `icon`
* `cell__url`
    * `lambda row, **_: row.get_absolute_url() + 'download/'`
* `cell__value`
    * `lambda row, **_: getattr(row, 'pk', False)`
* `display_name`
    * `Download`

`edit`
^^^^^^

Shortcut for creating a clickable edit icon. The URL defaults to `your_object.get_absolute_url() + 'edit/'`. Specify the option cell__url to override.

Defaults
++++++++

* `call_target__attribute`
    * `icon`
* `cell__url`
    * `lambda row, **_: row.get_absolute_url() + 'edit/'`
* `display_name`
    * `Edit`

`email`
^^^^^^^

Defaults
++++++++

* `filter__call_target__attribute`
    * `email`
* `bulk__call_target__attribute`
    * `email`

`file`
^^^^^^

Defaults
++++++++

* `bulk__call_target__attribute`
    * `file`
* `filter__call_target__attribute`
    * `file`
* `cell__format`
    * `lambda value, **_: str(value)`

`float`
^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `number`
* `filter__call_target__attribute`
    * `float`
* `bulk__call_target__attribute`
    * `float`

`foreign_key`
^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice_queryset`
* `bulk__call_target__attribute`
    * `foreign_key`
* `filter__call_target__attribute`
    * `foreign_key`
* `data_retrieval_method`
    * `DataRetrievalMethods.select`
* `sort_key`
    * `iommi.table.foreign_key__sort_key`

`icon`
^^^^^^

Shortcut to create font awesome-style icons.

        :param extra__icon: the font awesome name of the icon

Defaults
++++++++

* `display_name`
    * `""`
* `cell__value`
    * `lambda table, **_: True`
* `cell__format`
    * `iommi.table.default_icon__cell__format`
* `extra__icon_attrs__class`
    * `Namespace()`
* `extra__icon_attrs__style`
    * `Namespace()`
* `attr`
    * `None`

`integer`
^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `number`
* `filter__call_target__attribute`
    * `integer`
* `bulk__call_target__attribute`
    * `integer`

`link`
^^^^^^

`many_to_many`
^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `multi_choice_queryset`
* `bulk__call_target__attribute`
    * `many_to_many`
* `filter__call_target__attribute`
    * `many_to_many`
* `cell__format`
    * `lambda value, **_: ', '.join(['%s' % x for x in value.all()])`
* `data_retrieval_method`
    * `DataRetrievalMethods.prefetch`
* `sortable`
    * `False`
* `extra__django_related_field`
    * `True`

`multi_choice`
^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice`
* `bulk__call_target__attribute`
    * `multi_choice`
* `filter__call_target__attribute`
    * `multi_choice`

`multi_choice_queryset`
^^^^^^^^^^^^^^^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `choice_queryset`
* `bulk__call_target__attribute`
    * `multi_choice_queryset`
* `filter__call_target__attribute`
    * `multi_choice_queryset`

`number`
^^^^^^^^

`run`
^^^^^

Shortcut for creating a clickable run icon. The URL defaults to `your_object.get_absolute_url() + 'run/'`. Specify the option cell__url to override.

Defaults
++++++++

* `call_target__attribute`
    * `icon`
* `cell__url`
    * `lambda row, **_: row.get_absolute_url() + 'run/'`
* `display_name`
    * `Run`

`select`
^^^^^^^^

Shortcut for a column of checkboxes to select rows. This is useful for implementing bulk operations.

        To implement a custom post handler that operates on the selected rows, do

         .. code-block:: python

            def my_handler(table):
                rows = table.selection()
                # rows will either be a queryset, or a list of elements
                # matching the type of rows of the table
                ...

            Table(.... ,
                bulk__actions=Action.submit(post_handler=my_handler)
            )

        :param checkbox_name: the name of the checkbox. Default is `"pk"`, resulting in checkboxes like `"pk_1234"`.
        :param checked: callable to specify if the checkbox should be checked initially. Defaults to `False`.

Defaults
++++++++

* `header__template`
    * `iommi/table/select_column_header.html`
* `sortable`
    * `False`
* `filter__is_valid_filter`
    * `lambda **_: (True, '')`
* `filter__field__include`
    * `False`
* `attr`
    * `None`

`substring`
^^^^^^^^^^^

Defaults
++++++++

* `filter__query_operator_for_field`
    * `:`

`text`
^^^^^^

Defaults
++++++++

* `bulk__call_target__attribute`
    * `text`
* `filter__call_target__attribute`
    * `text`

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

* `filter__call_target__attribute`
    * `time`
* `filter__query_operator_to_q_operator`
    * `lambda op: {'=': 'exact', ':': 'contains'}.get(op)`
* `bulk__call_target__attribute`
    * `time`

"""
