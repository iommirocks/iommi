from iommi.thread_locals import (
    _thread_locals,
    get_current_request,
    set_current_request,
)


def test_threadlocals():
    _thread_locals.__dict__.clear()

    assert get_current_request() is None

    sentinel = object()
    set_current_request(sentinel)
    assert get_current_request() == sentinel
