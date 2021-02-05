from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.http import (
    Http404,
    HttpResponseRedirect,
)
from django.urls import (
    include,
    path,
)
from tri_struct import Struct

from iommi.admin import (
    Admin,
    collect_config,
    Messages,
)
from iommi.base import values
from tests.helpers import (
    req,
    staff_req,
    user_req,
)
from tests.models import Foo

urlpatterns = [
    path('', include(Admin.urls())),
]


@pytest.mark.django_db
def test_bulk_edit_for_non_unique(settings):
    settings.ROOT_URLCONF = __name__
    request = staff_req('get')
    p = Admin.list(
        request=request,
        app_name='tests',
        model_name='adminunique',
        parts__list_tests_adminunique__columns__foo__bulk__include=True,
    )
    p = p.bind(request=request)
    assert [x._name for x in values(p.parts.list_tests_adminunique.columns) if x.bulk.include] == ['foo']


@pytest.mark.django_db
@mock.patch('iommi.admin.messages')
def test_create(mock_messages, settings):
    settings.ROOT_URLCONF = __name__

    request = staff_req('get')
    c = Admin.create(request=request, app_name='tests', model_name='foo')
    p = c.bind(request=request)
    assert list(p.parts.create_tests_foo.fields.keys()) == ['foo']

    assert Foo.objects.count() == 0

    # Check access control for not logged in
    request = req('post', foo=7, **{'-submit': ''})
    assert isinstance(Admin.create(request=request, app_name='tests', model_name='foo'), HttpResponseRedirect)
    assert Foo.objects.count() == 0

    # Check access control for not staff
    request = user_req('post', foo=7, **{'-submit': ''})
    with pytest.raises(Http404):
        Admin.create(request=request, app_name='tests', model_name='foo')

    # Now for real
    request = staff_req('post', foo=7, **{'-submit': ''})
    c = Admin.create(request=request, app_name='tests', model_name='foo')
    p = c.bind(request=staff_req('post', foo=7, **{'-submit': ''}))
    assert p.parts.create_tests_foo.is_valid()
    p.render_to_response()

    assert Foo.objects.count() == 1
    f = Foo.objects.get()
    assert f.foo == 7

    mock_messages.add_message.assert_called_with(
        request, mock_messages.INFO, f'Foo {f} was created', fail_silently=True
    )


@pytest.mark.django_db
@mock.patch('iommi.admin.messages')
def test_edit(mock_messages, settings):
    settings.ROOT_URLCONF = __name__
    request = staff_req('get')
    assert Foo.objects.count() == 0
    f = Foo.objects.create(foo=7)

    c = Admin.edit(request=request, app_name='tests', model_name='foo', pk=f.pk)
    p = c.bind(request=req('post', foo=11, **{'-submit': ''}))
    assert p.parts.edit_tests_foo.is_valid()
    p.render_to_response()
    assert Foo.objects.get().foo == 11

    mock_messages.add_message.assert_called_with(
        request, mock_messages.INFO, f'Foo {f} was updated', fail_silently=True
    )


@pytest.mark.django_db
@mock.patch('iommi.admin.messages')
def test_delete(mock_messages, settings):
    settings.ROOT_URLCONF = __name__
    request = staff_req('get')
    assert Foo.objects.count() == 0
    f = Foo.objects.create(foo=7)

    c = Admin.delete(request=request, app_name='tests', model_name='foo', pk=f.pk)
    p = c.bind(request=req('post', **{'-submit': ''}))
    assert p.parts.delete_tests_foo.is_valid()
    p.render_to_response()
    assert Foo.objects.count() == 0

    mock_messages.add_message.assert_called_with(
        request, mock_messages.INFO, f'Foo {f} was deleted', fail_silently=True
    )


@pytest.mark.django_db
@pytest.mark.parametrize('is_authenticated', [True, False])
@pytest.mark.parametrize(
    'view,kwargs',
    [
        (Admin.all_models, dict()),
        (Admin.list, dict(app_name='tests', model_name='foo')),
        (Admin.edit, dict(app_name='tests', model_name='foo', pk=0)),
        (Admin.delete, dict(app_name='tests', model_name='foo', pk=0)),
    ],
)
def test_redirect_to_login(settings, is_authenticated, view, kwargs):
    settings.ROOT_URLCONF = __name__
    if 'pk' in kwargs:
        Foo.objects.create(pk=kwargs['pk'], foo=1)
    request = req('get')
    request.user = Struct(is_staff=True, is_authenticated=is_authenticated)

    result = view(request=request, **kwargs)

    if not is_authenticated:
        assert isinstance(result, HttpResponseRedirect)
        assert result.url == '/login/?next=%2F'
    else:
        assert isinstance(result, Admin)


@pytest.mark.django_db
@pytest.mark.parametrize(
    'view,kwargs',
    [
        (Admin.all_models, dict()),
        (Admin.list, dict(app_name='tests', model_name='foo')),
        (Admin.edit, dict(app_name='tests', model_name='foo', pk=0)),
        (Admin.delete, dict(app_name='tests', model_name='foo', pk=0)),
    ],
)
def test_404_for_non_staff(settings, view, kwargs):
    settings.ROOT_URLCONF = __name__
    if 'pk' in kwargs:
        Foo.objects.create(pk=kwargs['pk'], foo=1)
    request = user_req('get')

    with pytest.raises(Http404):
        view(request=request, **kwargs)


def test_messages():
    request = req('get')
    message = 'test message'
    request._messages = [message]
    assert message in Messages().bind(request=request).__html__()


def test_all_models(settings):
    settings.ROOT_URLCONF = __name__
    request = staff_req('get')
    assert (
        'Authentication'
        in Admin.all_models(request=request).bind(request=request).render_to_response().content.decode()
    )


@pytest.mark.django_db
def test_login_to_admin(settings, client):
    settings.ROOT_URLCONF = __name__
    response = client.get('/')
    assert isinstance(response, HttpResponseRedirect)
    assert '/login/' in response.url

    User.objects.create_user(username='staff', password='password', is_staff=True)

    response = client.post(response.url, data={'username': 'staff', 'password': 'bad password', '-submit': ''})
    assert 'Unknown username or password' in response.content.decode()

    response = client.post('/login/', data={'username': 'staff', 'password': 'password', '-submit': ''})
    assert isinstance(response, HttpResponseRedirect)
    assert 'All models' in client.get('/').content.decode()

    client.get('/logout/')
    assert client.get('/').status_code == 302


@pytest.mark.django_db
def test_change_password(settings, admin_client, admin_user):
    settings.ROOT_URLCONF = __name__
    settings.AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
            'OPTIONS': {
                'min_length': 3,
            },
        },
    ]

    old_password = 'password'
    assert admin_user.check_password(old_password)

    response = admin_client.get('/change_password/')
    assert response.status_code == 200

    new_password = 'new_password'

    def data(p=new_password):
        return {
            '-submit': '',
            'new_password': p,
            'confirm_password': p,
        }

    # Try to change without knowing the old password
    response = admin_client.post('/change_password/', data={'current_password': 'incorrect old password', **data()})
    admin_user.refresh_from_db()
    assert 'Incorrect password' in response.content.decode()
    assert admin_user.check_password('password')

    # Try to change the password to something super weak
    response = admin_client.post('/change_password/', data={'current_password': old_password, **data('q')})
    assert 'This password is too short' in response.content.decode()
    admin_user.refresh_from_db()
    assert admin_user.check_password(old_password)

    # Now change the password
    admin_client.post('/change_password/', data={'current_password': old_password, **data()})
    admin_user.refresh_from_db()
    assert admin_user.check_password(new_password)


def test_collect_config_returns_none_on_missing():
    import os

    assert collect_config(os) is None
    from tests import empty_iommi_admin

    assert collect_config(empty_iommi_admin) is None
