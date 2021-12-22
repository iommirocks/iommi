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
    Form
    ====
    
    Base class: :doc:`Part`
    
    Describe a Form. Example:
    
    """

    class MyForm(Form):
        a = Field()
        b = Field.email()

    form = MyForm().bind(request=request)

    # language=rst
    """
    You can also create an instance of a form with this syntax if it's more convenient:
    
    """

    form = Form(
        fields=dict(
            a=Field(),
            b=Field.email(),
        ),
    ).bind(request=request)

    # language=rst
    """
    See tri.declarative docs for more on this dual style of declaration.
    
    In the common case the fields namespace will contain only instances of `Field`, but
    iommi actually supports arbitrary `Part` objects. For example:
    
    """

    form = Form(
        fields=dict(
            # Display a and b inside a box
            box=html.div(
                attrs__class__box=True,
                children__a=Field(),
                children__b=Field.email(),
            ),
            # And c regularly
            c=Field(),
        )
    )

    # language=rst
    """
    So that writing the application logic (e.g. validation and post handlers) is independent
    of minor changes to the layout, after bind the `fields` namespace of the form will contain
    only instances of `Field` keyed by their `_name` independently of how deep they are in the
    hierarchy. Given the above, an appropriate post_handler would be:
    
    """

    def post_handler(form, **_):
        if not form.is_valid():
            return

        print(form.fields.a.value, form.fields.b.value, form.fields.c.value)
        # And not:
        # print(form.fields.box.a.value, form.fields.box.b.value, form.fields.c.value)

    # @test
    post_handler(form.bind(request=req('post')))
    # @end
# language=rst
"""
    

Refinable members
-----------------

* `action_class`
    Type: `Type[iommi.action.Action]`
    
* `actions`
    Type: `Namespace`
    
* `actions_template`
    Type: `Union[str, iommi._web_compat.Template]`
    
* `after`
    Type: `Union[int, str]`
    
* `assets`
    Type: `Namespace`
    
* `attr`
    Type: `str`
    
* `attrs`
    Type: :doc:`Attrs`
    
    Cookbook: :ref:`form.attrs`
    
* `auto`
    Type: `Namespace`
    
* `editable`
    Type: `bool`
    
    Cookbook: :ref:`form.editable`
    
* `endpoints`
    Type: `Namespace`
    
* `errors`
    Type: `Errors`
    
* `extra`
    Type: `Dict[str, Any]`
    
* `extra_evaluated`
    Type: `Dict[str, Any]`
    
* `field_group`
    Type: `Namespace`
    
* `fields`
    Type: `Namespace`
    
* `h_tag`
    Type: `Union[iommi.fragment.Fragment, str]`
    
* `include`
    Type: `bool`
    
* `instance`
    Type: `Any`
    
* `iommi_style`
    Type: `str`
    
* `member_class`
    Type: `Type[iommi.form.Field]`
    
* `model`
    Type: `Type[django.db.models.base.Model]`
    
* `page_class`
    Type: `Type[iommi.page.Page]`
    
* `post_validation`
* `read_nested_form_from_instance`
* `template`
    Type: `Union[str, iommi._web_compat.Template]`
    
* `title`
    Type: :doc:`Fragment`
    
* `write_nested_form_to_instance`

Defaults
^^^^^^^^

* `attrs__action`
    * `""`
* `attrs__enctype`
    * `multipart/form-data`
* `attrs__method`
    * `post`
* `editable`
    * `True`
* `field_group__call_target`
    * `iommi.form.FieldGroup`
* `h_tag__call_target`
    * `iommi.fragment.Header`

Shortcuts
---------

`create`
^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `crud`
* `extra__is_create`
    * `True`
* `extra__new_instance`
    * `lambda form, **_: form.model()`
* `actions__submit__post_handler`
    * `iommi.form.create_object__post_handler`
* `auto__type`
    * `create`

`crud`
^^^^^^

Defaults
++++++++

* `extra__pre_save_all_but_related_fields`
    * `lambda **kwargs: None, # pragma: no mutate`
* `extra__on_save_all_but_related_fields`
    * `lambda **kwargs: None, # pragma: no mutate`
* `extra__pre_save`
    * `lambda **kwargs: None, # pragma: no mutate`
* `extra__on_save`
    * `lambda **kwargs: None, # pragma: no mutate`
* `extra__on_delete`
    * `lambda **kwargs: None, # pragma: no mutate`
* `extra__redirect`
    * `lambda redirect_to, **_: HttpResponseRedirect(redirect_to)`
* `extra__redirect_to`
    * `None`
* `auto`
    * `Namespace()`

`delete`
^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `crud`
* `actions__submit__call_target__attribute`
    * `delete`
* `actions__submit__post_handler`
    * `iommi.form.delete_object__post_handler`
* `auto__type`
    * `delete`
* `editable`
    * `False`

`edit`
^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `crud`
* `extra__is_create`
    * `False`
* `actions__submit__post_handler`
    * `iommi.form.edit_object__post_handler`
* `auto__type`
    * `edit`

"""
