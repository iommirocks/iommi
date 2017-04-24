from django.test import RequestFactory
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
    assert (should_return, response.content) == (True, '{"bar": "payload"}')
