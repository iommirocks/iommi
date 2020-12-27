import json

import pytest
from django.views.decorators.csrf import csrf_exempt

from iommi import Form
from iommi._web_compat import HttpResponse
from iommi.live_edit import (
    live_edit_view,
    get_wrapped_view_function,
    should_edit,
    dangerous_execute_code,
)
from iommi.part import render_root
from tests.helpers import req
from tests.models import TFoo


def view(request):
    return HttpResponse('hello!')


@csrf_exempt
def csrf_exempt_view(request):
    return HttpResponse('hello!')


def test_live_edit():
    result = render_root(part=live_edit_view(req('get'), csrf_exempt_view).bind(request=req('get')))
    assert '@csrf_exempt' in result, result
    assert "def csrf_exempt_view(request):" in result, result


def test_get_wrapped_view_function():
    assert get_wrapped_view_function(view) is view
    assert get_wrapped_view_function(csrf_exempt(view)) is view
    with pytest.raises(AssertionError) as e:
        get_wrapped_view_function(Form.create(auto__model=TFoo).as_view())

    assert str(e.value) == "Edit mode isn't supported for the as_view() style yet."


def test_should_edit(settings):
    assert not should_edit(req('get'))
    assert not should_edit(req('get', _iommi_live_edit=''))

    settings.DEBUG = True
    assert should_edit(req('get', _iommi_live_edit=''))


def test_dangerous_execute_code_error():
    with pytest.raises(SyntaxError):
        dangerous_execute_code(code='invalid code', request=req('post'), view_func=view)


def test_dangerous_execute_code_success():
    code = """
def view(request):
    return HttpResponse(request.GET['foo'] + 'bar')    
"""

    assert json.loads(dangerous_execute_code(code=code, request=req('get', foo='foo'), view_func=view).content) == dict(page='foobar')
