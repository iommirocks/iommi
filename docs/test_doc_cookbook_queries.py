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

from tests.helpers import req, user_req, staff_req
from django.template import Template
from tri_declarative import Namespace
from iommi.attrs import render_attrs
from django.http import HttpResponseRedirect
from datetime import date
import pytest
pytestmark = pytest.mark.django_db




def test_queries():
    # language=rst
    """
    Queries
    -------

    .. _Filter.query_operator_to_q_operator:

    """
    

def test_how_do_i_override_what_operator_is_used_for_a_query():
    # language=rst
    """
    How do I override what operator is used for a query?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The member `query_operator_to_q_operator` for `Filter` is used to convert from e.g. `:`
    to `icontains`. You can specify another callable here:


    """
    Table(
        auto__model=Track,
        columns__album__filter__query_operator_to_q_operator=lambda op: 'exact',
    )

    # language=rst
    """
    The above will force the album name to always be looked up with case
    sensitive match even if the user types `album<Paranoid` in the
    advanced query language. Use this feature with caution!

    See also `How do I control what Q is produced?`_

    .. _Filter.value_to_q:

    """
    

def test_how_do_i_control_what_q_is_produced():
    # language=rst
    """
    How do I control what Q is produced?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    For more advanced customization you can use `value_to_q`. It is a
    callable that takes `filter, op, value_string_or_f` and returns a
    `Q` object. The default handles `__`, different operators, negation
    and special handling of when the user searches for `null`.
    """