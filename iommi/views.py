from django.conf import settings
from django.contrib import auth
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.urls import (
    include,
    path,
)
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from iommi import (
    Column,
    Field,
    Form,
    html,
    Page,
    Table,
)
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    setdefaults_path,
)


def auth_views():
    return include([
        path('login/', login),
        path('logout/', logout),
        path('change_password/', change_password),
    ])


@dispatch(
    table=EMPTY,
    create=EMPTY,
    edit=EMPTY,
    delete=EMPTY,
    detail=EMPTY,
)
def crud_views(*, model, table, create, edit, delete, detail):
    table = setdefaults_path(
        table,
        auto__model=model,
        columns__edit=Column.edit(
            after=0,
            cell__url=lambda row, **_: f'{row.pk}/edit/',
        ),
        columns__delete=Column.delete(
            cell__url=lambda row, **_: f'{row.pk}/delete/',
        ),
    )
    detail = setdefaults_path(
        detail,
        auto__model=model,
        editable=False,
        instance=lambda params, **_: model.objects.get(pk=params.pk),
        title=lambda form, **_: (form.model or form.instance)._meta.verbose_name,
    )
    create = setdefaults_path(
        create,
        auto__model=model,
    )
    edit = setdefaults_path(
        edit,
        auto__model=model,
        instance=lambda params, **_: model.objects.get(pk=params.pk),
    )
    delete = setdefaults_path(
        delete,
        auto__model=model,
        instance=lambda params, **_: model.objects.get(pk=params.pk),
    )

    return include([
        path('', Table(**table).as_view()),
        path('create/', Form.create(**create).as_view()),
        path('<pk>/', Form(**detail).as_view()),
        path('<pk>/edit/', Form.edit(**edit).as_view()),
        path('<pk>/delete/', Form.delete(**delete).as_view()),
    ])


class LogoutForm(Form):
    class Meta:
        title = gettext_lazy('Confirm log out')

        actions__submit__display_name = 'Log out'

        @staticmethod
        def actions__submit__post_handler(request, **_):
            auth.logout(request)
            return HttpResponseRedirect(resolve_url(settings.LOGOUT_REDIRECT_URL or '/'))


logout = LogoutForm().as_view()


class LoginForm(Form):
    username = Field(display_name=gettext_lazy('Username'))
    password = Field.password(display_name=gettext_lazy('Password'))

    class Meta:
        title = gettext_lazy('Login')

        @staticmethod
        def actions__submit__post_handler(form, **_):
            if form.is_valid():
                user = auth.authenticate(
                    username=form.fields.username.value,
                    password=form.fields.password.value,
                )

                if user is not None:
                    request = form.get_request()
                    auth.login(request, user)
                    return HttpResponseRedirect(request.GET.get('next', '/'))

                form.add_error(gettext_lazy('Unknown username or password'))


class LoginPage(Page):
    form = LoginForm()
    set_focus = html.script(
        mark_safe(
            'document.getElementById("id_username").focus();',
        )
    )


login = LoginPage().as_view()


def current_password__is_valid(form, parsed_data, **_):
    return (
        (True, None)
        if check_password(parsed_data, form.get_request().user.password)
        else (False, gettext_lazy('Incorrect password'))
    )


def new_password__is_valid(form, parsed_data, **_):
    try:
        validate_password(parsed_data, form.get_request().user)
        return True, None
    except ValidationError as e:
        return False, ','.join(e)


def confirm_password__is_valid(form, parsed_data, **_):
    return (
        (True, None)
        if parsed_data == form.fields.new_password.value
        else (False, gettext_lazy('New passwords does not match'))
    )


class ChangePasswordForm(Form):
    class Meta:
        title = gettext_lazy('Change password')

        @staticmethod
        def actions__submit__post_handler(form, request, **_):
            if form.is_valid():
                user = request.user
                user.set_password(form.fields.new_password.value)
                user.save()
                return HttpResponseRedirect('..')

    current_password = Field.password(is_valid=current_password__is_valid, display_name=gettext_lazy('Current password'))
    new_password = Field.password(is_valid=new_password__is_valid, display_name=gettext_lazy('New password'))
    confirm_password = Field.password(is_valid=confirm_password__is_valid, display_name=gettext_lazy('Confirm password'))


class ChangePasswordPage(Page):
    form = ChangePasswordForm()
    set_focus = html.script(
        mark_safe(
            'document.getElementById("id_current_password").focus();',
        )
    )


change_password = ChangePasswordPage().as_view()
