import json
from pathlib import Path

import pytest
from django.http import HttpResponse, HttpResponseForbidden
from django.test import override_settings
from django.views.decorators.csrf import csrf_exempt

from iommi import (
    Form,
    Page,
    register_style,
)
from iommi.live_edit import (
    LIVE_EDIT_TOKEN_FIELD,
    Middleware,
    _live_edit_token,
    dangerous_execute_code,
    live_edit_view,
    orig_reload,
    should_edit,
    style_editor__edit,
    style_editor__new,
    style_editor__select,
    style_showcase,
)
from iommi.part import render_root
from tests.helpers import req


def function_based_view(request):
    return HttpResponse('hello!')  # pragma: no cover


class PartBasedViewPage(Page):
    hello = 'hello!'


with override_settings(DEBUG=True):
    page = PartBasedViewPage()
    part_based_view = page.as_view()


@csrf_exempt
def csrf_exempt_view(request):
    return HttpResponse('hello!')  # pragma: no cover


def test_live_edit():
    result = render_root(part=live_edit_view(req('get'), csrf_exempt_view, args=(), kwargs={}).bind(request=req('get')))
    assert '@csrf_exempt' in result, result
    assert "def csrf_exempt_view(request):" in result, result
    assert f"headers: {{'X-Iommi-Live-Edit-Token': '{_live_edit_token}'}}" in result, result


def test_live_edit_dispatch_error(settings):
    settings.DEBUG = True
    m = Middleware(lambda _: 'response')
    request = req('get', _iommi_live_edit='bad data')
    request.META['SERVER_NAME'] = 'localhost'
    assert m(request) == 'response'
    with pytest.raises(KeyError):
        m.process_view(request, None, None, None)


def test_live_edit_part():
    result = render_root(part=live_edit_view(req('get'), part_based_view, args=(), kwargs={}).bind(request=req('get')))
    assert 'class PartBasedViewPage' in result, result


def test_should_edit(settings):
    assert not should_edit(req('get'))
    assert not should_edit(req('get', _iommi_live_edit=''))

    settings.DEBUG = True

    # Non-localhost is rejected even in DEBUG mode
    assert not should_edit(req('get', _iommi_live_edit=''))

    # Localhost is allowed
    r = req('get', _iommi_live_edit='')
    r.META['SERVER_NAME'] = 'localhost'
    assert should_edit(r)


def test_should_edit_requires_a_local_client(settings):
    settings.DEBUG = True

    def request(**meta):
        r = req('get', _iommi_live_edit='')
        r.META['SERVER_NAME'] = 'localhost'
        r.META.update(meta)
        return r

    assert should_edit(request())
    assert should_edit(request(REMOTE_ADDR='::1'))
    assert should_edit(request(REMOTE_ADDR='::ffff:127.0.0.1'))
    assert should_edit(request(HTTP_X_FORWARDED_FOR='127.0.0.1'))

    # The Host header says localhost, but the request came from somewhere else...
    assert not should_edit(request(REMOTE_ADDR='203.0.113.7'))
    assert not should_edit(request(REMOTE_ADDR='::ffff:203.0.113.7'))
    assert not should_edit(request(REMOTE_ADDR=''))
    assert not should_edit(request(REMOTE_ADDR='not an address'))
    # ...or through a proxy or tunnel on this machine
    assert not should_edit(request(HTTP_X_FORWARDED_FOR='203.0.113.7'))
    assert not should_edit(request(HTTP_X_FORWARDED_FOR='127.0.0.1, 203.0.113.7'))


def live_edit_post(url='/?_iommi_live_edit=', data=None, **meta):
    request = req('post', url=url, **(data if data is not None else dict(data='assert False')))
    request.META['SERVER_NAME'] = 'localhost'
    request.META.update(meta)
    return Middleware(lambda _: None).process_view(request, function_based_view, (), {})


def test_post_runs_the_code_with_the_token(settings):
    settings.DEBUG = True

    # `assert False` is the posted code: this error is what running it gives, and nothing is written to disk
    expected = {'error': "<class 'AssertionError'>"}

    assert json.loads(live_edit_post(HTTP_X_IOMMI_LIVE_EDIT_TOKEN=_live_edit_token).content) == expected
    assert (
        json.loads(
            live_edit_post(
                HTTP_X_IOMMI_LIVE_EDIT_TOKEN=_live_edit_token,
                HTTP_HOST='localhost:8000',
                HTTP_ORIGIN='http://localhost:8000',
                HTTP_SEC_FETCH_SITE='same-origin',
            ).content
        )
        == expected
    )


@pytest.mark.parametrize('token', [None, '', 'wrong', 'åäö'])
def test_post_is_refused_without_the_token(settings, token):
    settings.DEBUG = True

    response = live_edit_post(**({} if token is None else dict(HTTP_X_IOMMI_LIVE_EDIT_TOKEN=token)))
    assert isinstance(response, HttpResponseForbidden)
    # The page shows this to the user
    assert 'Reload the page' in json.loads(response.content)['error']


@pytest.mark.parametrize(
    'meta',
    [
        dict(HTTP_SEC_FETCH_SITE='cross-site'),
        # Another port on localhost is the same site, but not the same origin
        dict(HTTP_SEC_FETCH_SITE='same-site'),
        dict(HTTP_HOST='localhost:8000', HTTP_ORIGIN='https://evil.example'),
        dict(HTTP_HOST='localhost:8000', HTTP_ORIGIN='http://localhost:3000'),
        dict(HTTP_HOST='localhost:8000', HTTP_ORIGIN='null'),
    ],
)
def test_post_from_another_origin_is_refused(settings, meta):
    settings.DEBUG = True

    response = live_edit_post(HTTP_X_IOMMI_LIVE_EDIT_TOKEN=_live_edit_token, **meta)
    assert isinstance(response, HttpResponseForbidden)


@pytest.mark.parametrize('command', ['style_editor', 'style_editor__new'])
def test_style_editor_forms_carry_the_token(settings, command):
    settings.DEBUG = True
    url = f'/?_iommi_live_edit={command}'

    request = req('get', url=url)
    request.META['SERVER_NAME'] = 'localhost'
    form = Middleware(lambda _: None).process_view(request, function_based_view, (), {})
    assert isinstance(form, Form)
    html = form.bind(request=request).__html__()
    assert f'name="{LIVE_EDIT_TOKEN_FIELD}" type="hidden" value="{_live_edit_token}"' in html, html

    assert isinstance(live_edit_post(url=url, data={}), HttpResponseForbidden)
    assert isinstance(live_edit_post(url=url, data={LIVE_EDIT_TOKEN_FIELD: _live_edit_token}), Form)


@pytest.mark.parametrize('view', [function_based_view, part_based_view])
def test_dangerous_execute_code_error(view):
    with pytest.raises(SyntaxError):
        dangerous_execute_code(code='invalid code', request=req('post'), view=view, args=(), kwargs={})


def test_dangerous_execute_code_success():
    view = function_based_view
    code = """
def view(request):
    return HttpResponse(request.GET['foo'] + 'bar')
"""

    assert json.loads(
        dangerous_execute_code(code=code, request=req('get', foo='foo'), view=view, args=(), kwargs={}).content
    ) == dict(page='foobar')


def test_edit(capsys):
    path = Path(__file__).parent.parent / 'tests' / 'edit_views_temp.py'

    orig_code = """
from django.http import HttpResponse

def foo_view(request):
    return HttpResponse('foo view data')
"""

    new_code = """
def foo_view(request):
    return HttpResponse('changed!')
"""

    with open(path, 'w') as f:
        f.write(orig_code)

    from tests.edit_views_temp import foo_view

    # Broken changes are NOT written to disk
    data = json.loads(live_edit_view(req('post', data='syntax error!'), foo_view, args=(), kwargs={}).content)
    assert data == {'error': 'invalid syntax (<string>, line 1)'}

    with open(path) as f:
        assert f.read() == orig_code

    # Broken changes are NOT written to disk, this time with the exception string empty
    data = json.loads(live_edit_view(req('post', data='assert False'), foo_view).content)
    assert data == {'error': "<class 'AssertionError'>"}

    with open(path) as f:
        assert f.read() == orig_code

    # Valid changes are written to disk
    data = json.loads(live_edit_view(req('post', data=new_code), foo_view, args=(), kwargs={}).content)
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


def test_style_editor__select():
    style_editor__select().bind(request=req('get')).render_to_response()


def test_showcase():
    request = req('get')
    style_showcase(request).bind(request=request).render_to_response()


def test_edit_style(settings, capsys):
    settings.DEBUG = True
    path = Path(__file__).parent.parent / 'tests' / 'edit_style_temp.py'

    orig_code = """
from iommi.style import Style
from iommi.style_base import base
test_edit_style = Style(
    base,
    Field=dict(),
)
"""

    new_code = """
from iommi.style import Style
from iommi.style_base import base
test_edit_style = Style(
    base,
    Form=dict(),
)
"""

    with open(path, 'w') as f:
        f.write(orig_code)

    from tests.edit_style_temp import test_edit_style

    with register_style('test_edit_style', test_edit_style, allow_overwrite=True):
        # Broken changes are NOT written to disk
        data = json.loads(style_editor__edit(req('post', data='syntax error!', name='test_edit_style')).content)
        assert data == {'error': 'invalid syntax (<string>, line 1)'}

        with open(path) as f:
            assert f.read() == orig_code

        # Valid changes are written to disk
        data = json.loads(style_editor__edit(req('post', data=new_code, name='test_edit_style')).content)
        assert '<title>Style showcase</title>' in data['page']

        with open(path) as f:
            actual_new_code = f.read()

        assert actual_new_code == orig_code.replace('Field', 'Form')

        # Reload trigger hack
        if orig_reload is not None:  # modern django
            from django.utils import autoreload

            autoreload.trigger_reload('notused')
            captured = capsys.readouterr()
            assert captured.out == 'Skipped reload\n'

            with pytest.raises(SystemExit):
                autoreload.trigger_reload('notused')


def test_style_editor__new():
    style_editor__new().bind(
        request=req(
            'post',
            module='tests.style_editor_new_tmp',
            **{'-submit': ''},
        )
    ).render_to_response()


def test_is_localhost_detects_local_hosts():
    from iommi.live_edit import _is_localhost

    class _Req:
        def __init__(self, **meta):
            self.META = meta

    # local hosts (with and without port, IPv4 and IPv6) are recognised
    assert _is_localhost(_Req(HTTP_HOST='localhost'))
    assert _is_localhost(_Req(HTTP_HOST='localhost:8000'))
    assert _is_localhost(_Req(HTTP_HOST='127.0.0.1'))
    assert _is_localhost(_Req(HTTP_HOST='127.0.0.1:8000'))
    assert _is_localhost(_Req(HTTP_HOST='[::1]'))
    assert _is_localhost(_Req(HTTP_HOST='[::1]:8000'))

    # *.localhost subdomains resolve to loopback (e.g. in Chrome)
    assert _is_localhost(_Req(HTTP_HOST='foo.localhost'))
    assert _is_localhost(_Req(HTTP_HOST='foo.bar.localhost:8000'))

    # non-local hosts are rejected
    assert not _is_localhost(_Req(HTTP_HOST='example.com'))
    assert not _is_localhost(_Req(HTTP_HOST='evil.com:8000'))
    assert not _is_localhost(_Req(HTTP_HOST='localhost.evil.com'))
    assert not _is_localhost(_Req(HTTP_HOST='notlocalhost'))

    # HTTP_HOST takes precedence, but SERVER_NAME is the fallback
    assert _is_localhost(_Req(SERVER_NAME='localhost'))
    assert not _is_localhost(_Req(SERVER_NAME='example.com'))
    assert not _is_localhost(_Req())
