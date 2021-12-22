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
    Asset
    =====
    
    Base class: :doc:`Fragment`
    
    Class that describes an asset in iommi. Assets are meant to be the elements that you refer
    to in the HEAD of your document such as links to scripts, style sheets as well as
    inline scripts or css. But if necessary you can specify an arbitrary django template.
    
    Every :doc:`Part` can include the assets it needs. Similarly :doc:`Style` can include assets.
    When a part is rendered all assets are included in the head of the document.
    
    Because assets have names (`Everything has a name`), assets with the same name will overwrite
    each other, resulting in only one asset with a given name being rendered.
    

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


Shortcuts
---------

`css`
^^^^^

To use this shortcut, pass `attrs__href='/my_url_to_the.js'`

        Example:

        .. code-block:: python

            Asset.css(
                attrs__href='https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css',
                attrs__integrity='sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh',
                attrs__crossorigin='anonymous',
            )

Defaults
++++++++

* `tag`
    * `link`
* `attrs__rel`
    * `stylesheet`

`js`
^^^^

To use this shortcut, pass `attrs__src='/my_url_to_the.js'`

        Example:

        .. code-block:: python

            Asset.js(
                attrs__src='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/js/select2.min.js',
            )

Defaults
++++++++

* `tag`
    * `script`

"""
