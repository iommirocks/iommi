from tri_struct import Struct
from iommi.form import handle_dispatch, DISPATCH_PATH_SEPARATOR
from .compat import RequestFactory


def test_handle_dispatch_no_dispatch():
    request = RequestFactory().get('/', dict(foo='asds'))
    assert handle_dispatch(request, None) == (False, None)


def test_handle_dispatch_one_level():
    request = RequestFactory().get('/', {DISPATCH_PATH_SEPARATOR + 'foo' + DISPATCH_PATH_SEPARATOR + 'bar': 'payload'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    # miss
    assert handle_dispatch(request, Struct(endpoint_dispatch_prefix='bar')) == (True, None)

    # hit
    should_return, response = handle_dispatch(request, Struct(endpoint_dispatch_prefix='foo', endpoint_dispatch=lambda key, value: {key: value}))
    assert (should_return, response.content) == (True, b'{"bar": "payload"}')
    assert response._headers['content-type'][-1] == 'application/json'


def test_handle_dispatch_two_levels():
    request = RequestFactory().get('/', {DISPATCH_PATH_SEPARATOR + 'foo' + DISPATCH_PATH_SEPARATOR + 'bar' + DISPATCH_PATH_SEPARATOR + 'baz': 'payload'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    # miss
    assert handle_dispatch(request, Struct(endpoint_dispatch_prefix='bar')) == (True, None)

    # hit
    def endpoint_dispatch(key, value):
        assert value == 'payload'
        assert key == 'bar' + DISPATCH_PATH_SEPARATOR + 'baz'
        return "dispatch_result"

    should_return, response = handle_dispatch(request, Struct(endpoint_dispatch_prefix='foo', endpoint_dispatch=endpoint_dispatch))
    assert (should_return, response.content) == (True, b'"dispatch_result"')


def test_handle_dispatch_remaining_key_is_none():
    request = RequestFactory().get('/', {DISPATCH_PATH_SEPARATOR + 'foo': 'payload'})

    def endpoint_dispatch(key, value):
        assert key is None
        assert value == 'payload'

    handle_dispatch(request, Struct(endpoint_dispatch_prefix='foo', endpoint_dispatch=endpoint_dispatch))
