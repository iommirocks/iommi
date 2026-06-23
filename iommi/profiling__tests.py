import sys

import pytest
from django.http.response import HttpResponseBase
from django.test import override_settings

from iommi.profiling import (
    Middleware,
    get_dot_path,
    should_profile,
    strip_extra_path,
)
from tests.helpers import (
    req,
    staff_req,
    user_req,
)


class Sentinel(HttpResponseBase):
    pass


sentinel = Sentinel()
sentinel.user = None
middleware = Middleware(lambda request: sentinel)


def test_profiler_no_access():
    assert middleware(req('get')) is sentinel
    assert middleware(user_req('get')) is sentinel
    assert middleware(user_req('get', _iommi_prof='')) is sentinel
    assert middleware(user_req('post', _iommi_prof='')) is sentinel


def test_profiler_plain():
    middleware = Middleware(lambda request: sentinel)
    assert 'white-space: nowrap' in middleware(staff_req('get', _iommi_prof='')).content.decode()


def test_profiler_graph_error():
    old_sys_executable = sys.executable
    sys.executable = 'does_not_exist'
    with pytest.raises(Exception) as e:
        middleware(staff_req('get', _iommi_prof='graph'))
    sys.executable = old_sys_executable

    assert str(e.value) == 'gprof2dot not found. Please install it to use the graph feature.'


def test_profiler_graph_dot_present():
    if get_dot_path():
        content = middleware(staff_req('get', _iommi_prof='graph')).content.decode()
        assert '<!DOCTYPE svg ' in content, content


def test_profiler_graph_dot_not_present():
    import iommi.profiling

    orig = iommi.profiling._dot_search_paths[:]
    iommi.profiling._dot_search_paths[:] = ['does_not_exist']

    response = middleware(staff_req('get', _iommi_prof='graph'))

    iommi.profiling._dot_search_paths[:] = orig

    assert response.content.decode().startswith('digraph {')


def test_strip_extra_path():
    # No token -> returned unchanged.
    assert strip_extra_path('abc def', 'XYZ') == 'abc def'
    # With token -> everything up to and including the last token in the last space-separated
    # part is stripped.
    assert strip_extra_path('foo /a/b/site-packages/django/x.py', 'site-packages/') == 'foo django/x.py'
    # When the token appears more than once, the LAST occurrence is used (rindex, not index).
    assert strip_extra_path('foo /x/site-packages/a/site-packages/b.py', 'site-packages/') == 'foo b.py'


class _ProfReq:
    def __init__(self, *, get=None, post=None, is_staff=False, profiler_disabled=True):
        self.GET = get or {}
        self.POST = post or {}
        self.profiler_disabled = profiler_disabled

        class _User:
            pass

        self.user = _User()
        self.user.is_staff = is_staff


@override_settings(DEBUG=True)
def test_should_profile_in_debug():
    assert should_profile(_ProfReq(get={'_iommi_prof': ''})) is True
    assert should_profile(_ProfReq(post={'_iommi_prof': ''})) is True
    # The _iommi_prof marker is required even in DEBUG.
    assert should_profile(_ProfReq()) is False


@override_settings(DEBUG=False)
def test_should_profile_outside_debug_requires_enabled_staff():
    assert should_profile(_ProfReq(get={'_iommi_prof': ''}, is_staff=True, profiler_disabled=False)) is True
    # Not staff, or profiler disabled -> not allowed.
    assert should_profile(_ProfReq(get={'_iommi_prof': ''}, is_staff=False, profiler_disabled=False)) is False
    assert should_profile(_ProfReq(get={'_iommi_prof': ''}, is_staff=True, profiler_disabled=True)) is False


@override_settings(DEBUG=False)
def test_should_profile_defaults_to_disabled_when_attribute_missing():
    class _Req:
        GET = {'_iommi_prof': ''}
        POST = {}

        class user:
            is_staff = True

    # No profiler_disabled attribute -> defaults to disabled=True -> profiling not allowed.
    assert should_profile(_Req()) is False
