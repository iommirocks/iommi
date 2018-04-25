from tri.form.compat import RequestFactory
from tri.struct import Struct

from tri.form import handle_dispatch, DISPATCH_PATH_SEPARATOR


def test_handle_dispatch_no_dispatch():
    request = RequestFactory().get('/', dict(foo='asds'))
    assert handle_dispatch(request, None) == (False, None)


def test_handle_dispatch_one_level():
    request = RequestFactory().get('/', {DISPATCH_PATH_SEPARATOR + 'foo' + DISPATCH_PATH_SEPARATOR + 'bar': 'payload'})
    # miss
    assert handle_dispatch(request, Struct(endpoint_dispatch_prefix='bar')) == (True, None)

    # hit
    should_return, response = handle_dispatch(request, Struct(endpoint_dispatch_prefix='foo', endpoint_dispatch=lambda key, value: {key: value}))
    assert (should_return, response.content) == (True, b'{"bar": "payload"}')
    assert response._headers['content-type'][-1] == 'application/json'


def test_handle_dispatch_two_levels():
    request = RequestFactory().get('/', {DISPATCH_PATH_SEPARATOR + 'foo' + DISPATCH_PATH_SEPARATOR + 'bar' + DISPATCH_PATH_SEPARATOR + 'baz': 'payload'})
    # miss
    assert handle_dispatch(request, Struct(endpoint_dispatch_prefix='bar')) == (True, None)

    # hit
    def endpoint_dispatch(key, value):
        assert key == 'bar' + DISPATCH_PATH_SEPARATOR + 'baz'
        return "dispatch_result"

    should_return, response = handle_dispatch(request, Struct(endpoint_dispatch_prefix='foo', endpoint_dispatch=endpoint_dispatch))
    assert (should_return, response.content) == (True, b'"dispatch_result"')
