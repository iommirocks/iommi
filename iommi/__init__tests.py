from unittest.mock import patch

import pytest
from django.db import connections, transaction
from django.http import HttpResponse

from iommi import iommi_render
from iommi.fragment import Fragment
from tests.helpers import (
    call_view_through_middleware,
    req,
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
def test_middleware_no_atomic_requests():
    def view(request):
        return Fragment('The content')

    with patch('django.db.transaction.atomic') as mock_atomic:
        response = call_view_through_middleware(view, req('get'))

    mock_atomic.assert_not_called()

    assert isinstance(response, HttpResponse)
    assert 'The content' in response.content.decode()


@pytest.fixture
def atomic_requests_fixture():
    default_database_settings = connections['default'].settings_dict
    old_value = default_database_settings['ATOMIC_REQUESTS']
    default_database_settings['ATOMIC_REQUESTS'] = True
    yield
    default_database_settings['ATOMIC_REQUESTS'] = old_value


def atomic_mock(using):
    assert using == 'default'
    return lambda f: f


@pytest.mark.django_db
@pytest.mark.usefixtures("atomic_requests_fixture")
def test_middleware_atomic_block():
    def view(request):
        return Fragment('The content')

    with patch('django.db.transaction.atomic', side_effect=atomic_mock) as mock_atomic:
        response = call_view_through_middleware(view, req('get'))

    mock_atomic.assert_called_once()

    assert isinstance(response, HttpResponse)
    assert 'The content' in response.content.decode()


@pytest.mark.django_db
@pytest.mark.usefixtures("atomic_requests_fixture")
def test_no_atomic_block_on_decorated_view():
    @transaction.non_atomic_requests
    def non_atomic_requests_view(request):
        return Fragment('The content')

    with patch('django.db.transaction.atomic', side_effect=atomic_mock) as mock_atomic:
        response = call_view_through_middleware(non_atomic_requests_view, req('get'))

    mock_atomic.assert_not_called()

    assert isinstance(response, HttpResponse)
    assert 'The content' in response.content.decode()
