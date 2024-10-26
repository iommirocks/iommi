import re
import traceback
from unittest.mock import patch

import pytest
from django.db import (
    connections,
    transaction,
)
from django.http import HttpResponse

from iommi import (
    iommi_render,
    middleware,
    Page,
    render_part,
)
from iommi.fragment import (
    Fragment,
    html,
)
from tests.helpers import (
    call_view_through_middleware,
    req,
)


def test_render_decorator():
    the_request = req('get')

    @iommi_render
    def my_view(request, *args, **kwargs):
        """docstring"""
        assert request is the_request
        assert args == ('foo',)
        assert kwargs == {'bar': 'baz'}
        return Fragment('The content')

    result = my_view(the_request, 'foo', bar='baz')

    assert my_view.__doc__ == 'docstring'
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


def test_render_part():
    assert render_part(request=req('get'), part=Page()).status_code == 200

    class CrashyPage(Page):
        def render_to_response(self, **kwargs):
            raise FileNotFoundError()

    part = CrashyPage()
    filename, line_no = part._instantiated_at_info
    assert filename == __file__
    assert line_no not in (0, None)

    try:
        render_part(request=req('get'), part=part)
        assert False
    except FileNotFoundError:
        t = traceback.format_exc()

    assert f'{filename}", line {line_no}, in <iommi declaration>\n' in str(t)


def test_middleware_fall_through_non_iommi_objects():
    response = object()
    m = middleware(get_response=lambda request: response)
    r = m(req('get'))
    assert r is response


def test_middleware_iommi_object():
    response = Page(
        parts__div=html.div('hello world'),
        iommi_style='base',
    )
    m = middleware(get_response=lambda request: response)
    r = m(req('get'))
    assert r is not response
    assert '<div>hello world</div>' in r.content.decode()
