import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from iommi.views import ChangePasswordForm
from tests.helpers import req


def _change_password_form(user, **data):
    request = req('post', **{'-submit': '', **data})
    request.user = user
    return ChangePasswordForm().bind(request=request)


@pytest.mark.django_db
def test_change_password_confirm_must_match_new():
    user = User.objects.create(username='u')
    user.set_password('current-pw-123')
    user.save()

    form = _change_password_form(
        user,
        current_password='current-pw-123',
        new_password='a-brand-new-password',
        confirm_password='something-else',
    )

    assert not form.is_valid()
    assert str(form.fields.confirm_password.errors) == '<ul><li>New passwords do not match</li></ul>'


@pytest.mark.django_db
def test_change_password_requires_correct_current_password():
    user = User.objects.create(username='u')
    user.set_password('current-pw-123')
    user.save()

    form = _change_password_form(
        user,
        current_password='wrong-password',
        new_password='a-brand-new-password',
        confirm_password='a-brand-new-password',
    )

    assert not form.is_valid()
    assert str(form.fields.current_password.errors) == '<ul><li>Incorrect password</li></ul>'


@pytest.mark.django_db
@override_settings(
    AUTH_PASSWORD_VALIDATORS=[
        {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 20}},
    ]
)
def test_change_password_runs_django_password_validators_on_new_password():
    user = User.objects.create(username='u')
    user.set_password('current-pw-123')
    user.save()

    form = _change_password_form(
        user,
        current_password='current-pw-123',
        new_password='short',
        confirm_password='short',
    )

    assert not form.is_valid()
    assert 'too short' in str(form.fields.new_password.errors)


@pytest.mark.django_db
def test_change_password_valid_when_all_fields_correct():
    user = User.objects.create(username='u')
    user.set_password('current-pw-123')
    user.save()

    form = _change_password_form(
        user,
        current_password='current-pw-123',
        new_password='a-brand-new-password',
        confirm_password='a-brand-new-password',
    )

    assert form.is_valid()


def test_auth_views_url_patterns():
    from iommi.views import auth_views

    module = auth_views()[0]
    urlpatterns = module.urlpatterns if hasattr(module, 'urlpatterns') else module

    assert [str(p.pattern) for p in urlpatterns] == ['login/', 'logout/', 'change_password/']
