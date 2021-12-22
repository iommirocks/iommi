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
    Attrs
    =====
    
    Base class: `Namespace`
    
    The `attrs` namespace on `Field`, `Form`, `Header`, `Cell` and more is used to customize HTML attributes.
    
    """

    form = Form(
        auto__model=Album,
        fields__artist__attrs__foo='bar',
        fields__name__attrs__class__bar=True,
        fields__name__attrs__style__baz='qwe',
    )

    # language=rst
    """
    or more succinctly:
    
    """

    form = Form(
        auto__model=Album,
        fields__artist__attrs__foo='bar',
        fields__name__attrs=dict(
            class__bar=True,
            style__baz='qwe',
        )
    )


    # language=rst
    """
    The thing to remember is that the basic namespace is a dict with key value
    pairs that gets projected out into the HTML, but there are two special cases
    for `style` and `class`. The example above will result in the following
    attributes on the field tag:
    
    .. code-block:: html
    
    <div foo="bar" class="bar" style="baz: qwe">
    
    The values in these dicts can be callables:
    
    """

    form = Form(
        auto__model=Album,
        fields__name__attrs__class__bar=
            lambda request, **_: request.user.is_staff,
    )
# language=rst
"""
    

"""
