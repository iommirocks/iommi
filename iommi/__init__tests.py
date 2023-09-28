from unittest.mock import patch, Mock

import pytest
from django.db import connections
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
def test_middleware_atomic_block():
    default_database_settings = connections['default'].settings_dict
    old_value = default_database_settings['ATOMIC_REQUESTS']
    default_database_settings['ATOMIC_REQUESTS'] = True
    mock_response = Mock()

    try:
        with patch('iommi.render_if_needed', return_value=mock_response) as mock_render, \
             patch('django.db.transaction.atomic') as mock_atomic:

            response = request_with_middleware(object(), req('get'))

            # Assert that transaction.atomic was called and render_if_needed was called
            mock_atomic.assert_called_once()
            mock_render.assert_called_once()

            assert response == mock_response

    finally:
        default_database_settings['ATOMIC_REQUESTS'] = old_value


@pytest.mark.django_db
def test_middleware_rollback_on_exception():
    default_database_settings = connections['default'].settings_dict
    old_value = default_database_settings['ATOMIC_REQUESTS']
    default_database_settings['ATOMIC_REQUESTS'] = True

    try:
        with patch('iommi.render_if_needed', side_effect=Exception) as mock_render, \
             patch('django.db.transaction.atomic') as mock_atomic:

            with pytest.raises(Exception):
                request_with_middleware(object(), req('get'))

            # Assert that transaction.atomic was called and render_if_needed was called
            mock_atomic.assert_called_once()
            mock_render.assert_called_once()

    finally:
        default_database_settings['ATOMIC_REQUESTS'] = old_value


@pytest.mark.django_db
def test_middleware_no_atomic_requests():
    default_database_settings = connections['default'].settings_dict
    old_value = default_database_settings['ATOMIC_REQUESTS']
    default_database_settings['ATOMIC_REQUESTS'] = False
    mock_response = Mock()

    try:
        with patch('iommi.render_if_needed', return_value=mock_response) as mock_render, \
             patch('django.db.transaction.atomic') as mock_atomic:

            response = request_with_middleware(object(), req('get'))

            # Assert that transaction.atomic was not called and render_if_needed was called
            mock_atomic.assert_not_called()
            mock_render.assert_called_once()

            assert response == mock_response

    finally:
        default_database_settings['ATOMIC_REQUESTS'] = old_value
