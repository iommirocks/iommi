from iommi.profiling import ProfileMiddleware
from tests.helpers import (
    req,
    staff_req,
    user_req,
)


def test_profiler():
    class Sentinel:
        pass

    sentinel = Sentinel()
    sentinel.user = None

    middleware = ProfileMiddleware(lambda request: sentinel)
    assert middleware(req('get')) is sentinel
    assert middleware(user_req('get')) is sentinel
    assert middleware(user_req('get', prof='')) is sentinel

    assert 'white-space: nowrap' in middleware(staff_req('get', prof='')).content.decode()
