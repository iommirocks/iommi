import json
from pathlib import Path

import pytest
from django.views.decorators.csrf import csrf_exempt

from iommi import Form
from iommi._web_compat import HttpResponse
from iommi.live_edit import (
    live_edit_view,
    get_wrapped_view,
    should_edit,
    dangerous_execute_code,
    orig_reload,
)
from iommi.part import render_root
from tests.helpers import req
from tests.models import TFoo


def view(request):
    return HttpResponse('hello!')   # pragma: no cover


@csrf_exempt
def csrf_exempt_view(request):
    return HttpResponse('hello!')   # pragma: no cover


def test_live_edit():
    result = render_root(part=live_edit_view(req('get'), csrf_exempt_view).bind(request=req('get')))
    assert '@csrf_exempt' in result, result
    assert "def csrf_exempt_view(request):" in result, result


def test_get_wrapped_view_function():
    assert get_wrapped_view(view) is view
    assert get_wrapped_view(csrf_exempt(view)) is view
    get_wrapped_view(Form.create(auto__model=TFoo).as_view())


def test_should_edit(settings):
    assert not should_edit(req('get'))
    assert not should_edit(req('get', _iommi_live_edit=''))

    settings.DEBUG = True
    assert should_edit(req('get', _iommi_live_edit=''))


def test_dangerous_execute_code_error():
    with pytest.raises(SyntaxError):
        dangerous_execute_code(code='invalid code', request=req('post'), view=view)


def test_dangerous_execute_code_success():
    code = """
def view(request):
    return HttpResponse(request.GET['foo'] + 'bar')    
"""

    assert json.loads(dangerous_execute_code(code=code, request=req('get', foo='foo'), view=view).content) == dict(page='foobar')


def test_edit(capsys):
    path = Path(__file__).parent.parent / 'tests' / 'test_edit_views_temp.py'

    orig_code = """
from iommi._web_compat import HttpResponse

def foo_view(request):
    return HttpResponse('foo view data')        
"""

    new_code = """
def foo_view(request):
    return HttpResponse('changed!')        
"""

    with open(path, 'w') as f:
        f.write(orig_code)

    from tests.test_edit_views_temp import foo_view

    # Broken changes are NOT written to disk
    data = json.loads(live_edit_view(req('post', data='syntax error!'), foo_view).content)
    assert data == {'error': 'invalid syntax (<string>, line 1)'}

    with open(path) as f:
        assert f.read() == orig_code

    # Valid changes are written to disk
    data = json.loads(live_edit_view(req('post', data=new_code), foo_view).content)
    assert data == {'page': 'changed!'}

    with open(path) as f:
        actual_new_code = f.read()

    assert actual_new_code == orig_code.replace('foo view data', 'changed!')

    # Reload trigger hack
    if orig_reload is not None:  # modern django

        from django.utils import autoreload
        autoreload.trigger_reload('notused')
        captured = capsys.readouterr()
        assert captured.out == 'Skipped reload\n'

        with pytest.raises(SystemExit):
            autoreload.trigger_reload('notused')
