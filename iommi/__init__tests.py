import re

import pytest
from django.http import HttpResponse

from iommi import iommi_render
from iommi.fragment import Fragment
from tests.helpers import (
    req,
    request_with_middleware,
)


def test_render_decorator():
    @iommi_render
    def my_view(request, *args, **kwargs):
        assert args == ('foo',)
        assert kwargs == {'bar': 'baz'}
        return Fragment('The content')

    result = my_view(req('get'), 'foo', bar='baz')

    assert isinstance(result, HttpResponse)
    assert 'The content' in result.content.decode()


@pytest.mark.django_db
def test_middleware():
    from django.db import connections
    default_database_settings = connections['default'].settings_dict
    old_value = default_database_settings['ATOMIC_REQUESTS']
    try:
        default_database_settings['ATOMIC_REQUESTS'] = True
        with pytest.raises(TypeError) as e:
            request_with_middleware(object(), req('get'))
        assert re.match(
            'The iommi middleware is unable to retain atomic transactions. Disable '
            'ATOMIC_REQUEST for database connections '
            r'\(.*\) or remove middleware and '
            'use the @iommi_render decorator on the views instead.',
            str(e.value)
        )
    finally:
        default_database_settings['ATOMIC_REQUESTS'] = old_value
