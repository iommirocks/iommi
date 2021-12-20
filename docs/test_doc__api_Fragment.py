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
    Fragment
    ========
    
    Base class: :doc:`Part`
    
    `Fragment` is a class used to build small HTML fragments that plug into iommis structure.
    
    """

    # @ test
    from iommi.fragment import Fragment
    # @end

    h1 = Fragment(children__text='Tony', tag='h1')

    # language=rst
    """
    It's easiest to use via the html builder:
    
    """

    h1 = html.h1('Tony')

    # language=rst
    """
    Fragments are useful because attrs, template and tag are evaluated, so if
    you have a `Page` with a fragment in it you can configure it later:
    
    """

    class MyPage(Page):
        header = html.h1(
            'Hi!',
            attrs__class__staff=
                lambda request, **_: request.user.is_staff,
        )

    # language=rst
    """
    Rendering a `MyPage` will result in a `<h1>`, but if you do
    `MyPage(parts__header__tag='h2')` it will be rendered with a `<h2>`.
    

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


"""
