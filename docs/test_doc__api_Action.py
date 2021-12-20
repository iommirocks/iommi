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
    Action
    ======
    
    Base class: :doc:`Fragment`
    
    The `Action` class describes buttons and links.
    
    Examples:
    
    """

    # Link
    Action(attrs__href='http://example.com')

    # Link with icon
    Action.icon('edit', attrs__href="edit/")

    # Button
    Action.button(display_name='Button title!')

    # A submit button
    Action.submit(display_name='Do this')

    # The primary submit button on a form.
    Action.primary()

    # Notice that because forms
    # with a single primary submit button are so common, iommi assumes
    # that if you have a action called submit and do NOT explicitly
    # specify the action that it is a primary action. This is only
    # done for the action called submit, inside the Forms actions
    # Namespace.
    #
    # For that reason this works:

    class MyForm(Form):
        class Meta:
            @staticmethod
            def actions__submit__post_handler(form, **_):
                if not form.is_valid():
                    return

                ...

    # and is roughly equivalent to

    def on_submit(form, **_):
        if not form.is_valid():
            return

    class MyOtherForm(Form):
        class Meta:
            actions__submit = Action.primary(post_handler=on_submit)

    # @test
    r = req('post', **{'-submit': ''})
    MyForm().bind(request=r).render_to_response()
    MyOtherForm().bind(request=r).render_to_response()
    # @end
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
    
* `children`
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
    
* `post_handler`
    Type: `Callable`
    
* `tag`
* `template`
    Type: `Union[str, iommi._web_compat.Template]`
    

Defaults
^^^^^^^^

* `display_name`
    * `lambda action, **_: capitalize(action._name).replace('_', ' ')`
* `tag`
    * `a`

Shortcuts
---------

`button`
^^^^^^^^

Defaults
++++++++

* `tag`
    * `button`

`delete`
^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `submit`

`icon`
^^^^^^

Defaults
++++++++

* `icon_classes`
    * `[]`

`primary`
^^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `submit`

`submit`
^^^^^^^^

Defaults
++++++++

* `call_target__attribute`
    * `button`
* `attrs__accesskey`
    * `s`
* `attrs__name`
    * `lambda action, **_: action.own_target_marker()`
* `display_name`
    * `Submit`

"""
