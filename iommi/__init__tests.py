import re
from unittest.mock import patch, Mock

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
def test_middleware_commit():
    from django.db import connections

    default_database_settings = connections['default'].settings_dict
    old_value = default_database_settings['ATOMIC_REQUESTS']
    default_database_settings['ATOMIC_REQUESTS'] = True
    mock_response = Mock()

    try:
        with patch('iommi.render_if_needed', return_value=mock_response), \
             patch('django.db.transaction.savepoint') as mock_savepoint, \
             patch('django.db.transaction.savepoint_commit') as mock_commit, \
             patch('django.db.transaction.savepoint_rollback') as mock_rollback:

            response = request_with_middleware(object(), req('get'))

            # Assert that a savepoint was created and committed, but not rolled back
            mock_savepoint.assert_called_once()
            mock_commit.assert_called_once()
            mock_rollback.assert_not_called()

            assert response == mock_response

    finally:
        default_database_settings['ATOMIC_REQUESTS'] = old_value


@pytest.mark.django_db
def test_middleware_rollback():
    from django.db import connections

    default_database_settings = connections['default'].settings_dict
    old_value = default_database_settings['ATOMIC_REQUESTS']
    default_database_settings['ATOMIC_REQUESTS'] = True

    try:
        with patch('iommi.render_if_needed', side_effect=Exception), \
             patch('django.db.transaction.savepoint') as mock_savepoint, \
             patch('django.db.transaction.savepoint_commit') as mock_commit, \
             patch('django.db.transaction.savepoint_rollback') as mock_rollback:

            with pytest.raises(Exception):
                request_with_middleware(object(), req('get'))

            # Assert that a savepoint was created and rolled back, but not committed
            mock_savepoint.assert_called_once()
            mock_commit.assert_not_called()
            mock_rollback.assert_called_once()

    finally:
        default_database_settings['ATOMIC_REQUESTS'] = old_value


@pytest.mark.django_db
def test_middleware_no_atomic_requests():
    from django.db import connections

    default_database_settings = connections['default'].settings_dict
    old_value = default_database_settings['ATOMIC_REQUESTS']
    default_database_settings['ATOMIC_REQUESTS'] = False
    mock_response = Mock()

    try:
        with patch('iommi.render_if_needed', return_value=mock_response), \
             patch('django.db.transaction.savepoint') as mock_savepoint, \
             patch('django.db.transaction.savepoint_commit') as mock_commit, \
             patch('django.db.transaction.savepoint_rollback') as mock_rollback:

            response = request_with_middleware(object(), req('get'))

            # Assert that no transaction savepoint was created, committed, or rolled back
            mock_savepoint.assert_not_called()
            mock_commit.assert_not_called()
            mock_rollback.assert_not_called()

            assert response == mock_response

    finally:
        default_database_settings['ATOMIC_REQUESTS'] = old_value
