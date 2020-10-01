import sys

import pytest

from iommi.profiling import (
    get_dot_path,
    ProfileMiddleware,
)
from tests.helpers import (
    req,
    staff_req,
    user_req,
)


class Sentinel:
    pass


sentinel = Sentinel()
sentinel.user = None
middleware = ProfileMiddleware(lambda request: sentinel)


def test_profiler_no_access():
    assert middleware(req('get')) is sentinel
    assert middleware(user_req('get')) is sentinel
    assert middleware(user_req('get', prof='')) is sentinel


def test_profiler_plain():
    middleware = ProfileMiddleware(lambda request: sentinel)
    assert 'white-space: nowrap' in middleware(staff_req('get', prof='')).content.decode()


def test_profiler_graph_error():
    old_sys_executable = sys.executable
    sys.executable = 'does_not_exist'
    with pytest.raises(Exception) as e:
        middleware(staff_req('get', prof='', graph=''))
    sys.executable = old_sys_executable

    assert str(e.value) == 'gprof2dot not found. Please install it to use the graph feature.'


def test_profiler_graph_dot_present():
    if get_dot_path():
        assert '<!DOCTYPE svg ' in middleware(staff_req('get', prof='', graph='')).content.decode()


def test_profiler_graph_dot_not_present():
    import iommi.profiling
    orig = iommi.profiling._dot_search_paths[:]
    iommi.profiling._dot_search_paths[:] = ['does_not_exist']

    response = middleware(staff_req('get', prof='', graph=''))

    iommi.profiling._dot_search_paths[:] = orig

    assert response.content.decode().startswith('digraph {')
