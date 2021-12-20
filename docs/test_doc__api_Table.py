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
    Table
    =====
    
    Base class: :doc:`Part`
    
    Describe a table. Example:
    
    """

    class FooTable(Table):
        a = Column()
        b = Column()

        class Meta:
            sortable = False
            attrs__style = 'background: green'
# language=rst
"""
    

Refinable members
-----------------

* `action_class`
    Type: `Type[iommi.action.Action]`
    
* `actions`
    Type: `Dict[str, iommi.action.Action]`
    
* `actions_below`
    Type: `bool`
    
* `actions_template`
    Type: `Union[str, iommi._web_compat.Template]`
    
* `after`
    Type: `Union[int, str]`
    
* `assets`
    Type: `Namespace`
    
* `attrs`
    dict of strings to string/callable of HTML attributes to apply to the table

    Type: :doc:`Attrs`
    
    Cookbook: :ref:`table.attrs`
    
* `auto`
* `bulk`
    Type: `Optional[iommi.form.Form]`
    
    Cookbook: :ref:`table.bulk`
    
* `bulk_container`
    Type: :doc:`Fragment`
    
* `bulk_exclude`
    exclude filters to apply to the `QuerySet` before performing the bulk operation

    Type: `Namespace`
    
* `bulk_filter`
    filters to apply to the `QuerySet` before performing the bulk operation

    Type: `Namespace`
    
* `cell`
    Type: `CellConfig`
    
    Cookbook: :ref:`table.cell`
    
* `cells_class`
    Type: `Type[iommi.table.Cells]`
    
* `columns`
    (use this only when not using the declarative style) a list of Column objects

    Type: `Dict[str, iommi.table.Column]`
    
* `container`
    Type: :doc:`Fragment`
    
* `default_sort_order`
* `empty_message`
    Type: `str`
    
* `endpoints`
    Type: `Namespace`
    
* `extra`
    Type: `Dict[str, Any]`
    
* `extra_evaluated`
    Type: `Dict[str, Any]`
    
* `form_class`
    Type: `Type[iommi.form.Form]`
    
* `h_tag`
    Type: `Union[iommi.fragment.Fragment, str]`
    
* `header`
    Cookbook: :ref:`table.header`
    
* `include`
    Type: `bool`
    
* `invalid_form_message`
    Type: `str`
    
* `iommi_style`
    Type: `str`
    
* `member_class`
* `model`
    Type: `Type[django.db.models.base.Model]`
    
* `outer`
    Type: :doc:`Fragment`
    
* `page_class`
    Type: `Type[iommi.page.Page]`
    
* `page_size`
    Type: `int`
    
    Cookbook: :ref:`table.page_size`
    
* `parts`
    Type: `Namespace`
    
* `post_bulk_edit`
* `preprocess_row`
* `preprocess_rows`
* `query`
* `query_class`
    Type: `Type[iommi.query.Query]`
    
* `query_from_indexes`
    Type: `bool`
    
* `row`
    Type: `RowConfig`
    
    Cookbook: :ref:`table.row`
    
* `rows`
    a list or QuerySet of objects

* `sortable`
    set this to `False` to turn off sorting for all columns

    Type: `bool`
    
    Cookbook: :ref:`table.sortable`
    
* `superheader`
    Type: `Namespace`
    
* `tag`
    Type: `str`
    
* `tbody`
    Type: :doc:`Fragment`
    
* `template`
    Type: `Union[str, iommi._web_compat.Template]`
    
* `title`
    Type: `str`
    

Defaults
^^^^^^^^

* `actions_below`
    * `False`
* `actions_template`
    * `iommi/form/actions.html`
* `bulk__title`
    * `Bulk change`
* `bulk_container__call_target`
    * `iommi.fragment.Fragment`
* `cell__tag`
    * `td`
* `container__attrs__class`
    * `{'iommi-table-container': True}`
* `container__call_target`
    * `iommi.fragment.Fragment`
* `container__children__text__template`
    * `iommi/table/table_container.html`
* `container__tag`
    * `div`
* `h_tag__call_target`
    * `iommi.fragment.Header`
* `header__template`
    * `iommi/table/table_header_rows.html`
* `outer__call_target`
    * `iommi.fragment.Fragment`
* `page_size`
    * `40`
* `parts__page__call_target`
    * `iommi.table.Paginator`
* `query__form__actions__submit__call_target`
    * `iommi.action.button`
* `row__attrs__data-pk`
    * `lambda row, **_: getattr(row, 'pk', None)}`
* `row__tag`
    * `tr`
* `row__template`
    * `None`
* `sortable`
    * `True`
* `superheader__attrs__class__superheader`
    * `True`
* `superheader__template`
    * `iommi/table/header.html`
* `tag`
    * `table`
* `tbody__call_target`
    * `iommi.fragment.Fragment`
* `tbody__tag`
    * `tbody`
* `template`
    * `iommi/table/table.html`

Shortcuts
---------

`div`
^^^^^

Defaults
++++++++

* `tag`
    * `div`
* `tbody__tag`
    * `div`
* `cell__tag`
    * `None`
* `row__tag`
    * `div`
* `header__template`
    * `None`

"""
