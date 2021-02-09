import functools
from functools import wraps
from typing import Type
from urllib.parse import urlencode

from django.apps import apps as django_apps
from django.contrib import (
    auth,
    messages,
)
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import (
    Http404,
    HttpResponseRedirect,
)
from django.urls import (
    path,
    reverse,
)
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from tri_declarative import (
    class_shortcut,
    dispatch,
    EMPTY,
    LAST,
    Namespace,
    Refinable,
    setdefaults_path,
    with_meta,
)
from tri_struct import Struct

from iommi import (
    Field,
    Form,
    Fragment,
    Header,
    html,
    Menu,
    MenuItem,
    Page,
    Table,
)
from iommi.base import (
    items,
    values,
)
from iommi.reinvokable import reinvokable

app_verbose_name_by_label = {
    config.label: config.verbose_name.replace('_', ' ')
    for config in values(django_apps.app_configs)
}

joined_app_name_and_model = {
    f'{app_name}_{model_name}'
    for app_name, models in items(django_apps.all_models)
    for model_name, model in items(models)
}


def require_login(view):
    @wraps(view)
    def wrapper(cls, request, *args, **kwargs):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return HttpResponseRedirect(f'{reverse(Auth.login)}?{urlencode(dict(next=request.path))}')

        return view(cls, request, *args, **kwargs)

    return wrapper


@with_meta
class Messages(Fragment):
    class Meta:
        tag = 'div'

    def on_bind(self) -> None:
        super().on_bind()
        ms = messages.get_messages(self.get_request())
        if ms:
            self.children.update(
                {
                    f'message{i}': Fragment(
                        tag='div',
                        text=f'{m}',
                    ).bind(parent=self)
                    for i, m in enumerate(ms)
                }
            )


def collect_config(module):
    try:
        __import__(module.__name__ + '.iommi_admin')
        config_module = module.iommi_admin
    except ImportError:
        return None

    try:
        meta = config_module.Meta
    except AttributeError:
        return None

    return {k: v for k, v in meta.__dict__.items() if not k.startswith('_')}


def read_config(f):
    @functools.wraps(f)
    def read_config_wrapper(self, *args, **kwargs):
        from django.apps import apps

        configs = []
        for app_name, app in apps.app_configs.items():
            c = collect_config(app.module)
            if c is not None:
                configs.append(c)

        return f(self, *args, **Namespace(*configs, kwargs))

    return read_config_wrapper


@with_meta  # we need @with_meta again here to make sure this constructor gets all the meta arguments first
class Admin(Page):
    class Meta:
        iommi_style = 'bootstrap'
        table_class = Table
        form_class = Form
        apps__auth_user__include = True
        apps__auth_group__include = True
        parts__messages = Messages()
        parts__list_auth_user = dict(
            auto__include=['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_superuser'],
            columns=dict(
                username__filter__freetext=True,
                email__filter__freetext=True,
                first_name__filter__freetext=True,
                last_name__filter__freetext=True,
                is_staff__filter__include=True,
                is_active__filter__include=True,
                is_superuser__filter__include=True,
            ),
        )

    table_class: Type[Table] = Refinable()
    form_class: Type[Form] = Refinable()

    apps: Namespace = Refinable()  # Global configuration on apps level

    menu = Menu(
        sub_menu=dict(
            root=MenuItem(
                url=lambda admin, **_: reverse(admin.__class__.all_models), display_name=gettext('iommi administration')
            ),
            change_password=MenuItem(
                url=lambda **_: reverse(Auth.change_password), display_name=gettext('Change password')
            ),
            logout=MenuItem(url=lambda **_: reverse(Auth.logout), display_name=gettext('Logout')),
        ),
    )

    @read_config
    @reinvokable
    @dispatch(
        apps=EMPTY,
        parts=EMPTY,
    )
    def __init__(self, parts, apps, **kwargs):
        # Validate apps params
        for k in apps.keys():
            assert (
                k in joined_app_name_and_model
            ), f'{k} is not a valid app/model key.\n\nValid keys:\n    ' + '\n    '.join(joined_app_name_and_model)

        def should_throw_away(k, v):
            if isinstance(v, Namespace) and 'call_target' in v:
                return False

            if k == 'all_models':
                return True

            prefix_blacklist = [
                'list_',
                'delete_',
                'create_',
                'edit_',
            ]
            for prefix in prefix_blacklist:
                if k.startswith(prefix):
                    return True

            return False

        parts = {
            # Arguments that are not for us needs to be thrown on the ground
            k: None if should_throw_away(k, v) else v
            for k, v in items(parts)
        }

        super(Admin, self).__init__(parts=parts, apps=apps, **kwargs)

    @staticmethod
    def has_permission(request, operation, model=None, instance=None):
        return request.user.is_staff

    def own_evaluate_parameters(self):
        return dict(admin=self, **super(Admin, self).own_evaluate_parameters())

    @classmethod
    @class_shortcut(
        table=EMPTY,
        table__call_target__attribute='div',
    )
    @require_login
    def all_models(cls, request, table, call_target=None, **kwargs):
        if not cls.has_permission(request, operation='all_models'):
            raise Http404()

        def rows(admin, **_):

            for app_name, models in items(django_apps.all_models):
                has_yielded_header = False

                for model_name, model in sorted(items(models), key=lambda x: x[1]._meta.verbose_name_plural):
                    if not admin.apps.get(f'{app_name}_{model_name}', {}).get('include', False):
                        continue

                    if not has_yielded_header:
                        yield Struct(
                            name=app_verbose_name_by_label[app_name],
                            verbose_app_name=app_verbose_name_by_label[app_name],
                            url=None,
                            format=lambda row, table, **_: Header(row.name, _name='invalid_name')
                            .bind(parent=table)
                            .__html__(),
                        )
                        has_yielded_header = True

                    yield Struct(
                        verbose_app_name=app_verbose_name_by_label[app_name],
                        app_name=app_name,
                        name=model._meta.verbose_name_plural.capitalize(),
                        url='%s/%s/' % (app_name, model_name),
                        format=lambda row, **_: row.name,
                    )

        table = setdefaults_path(
            Namespace(),
            table,
            title=gettext('All models'),
            call_target__cls=cls.get_meta().table_class,
            sortable=False,
            rows=rows,
            header__template=None,
            page_size=None,
            columns__name=dict(
                cell__url=lambda row, **_: row.url,
                display_name='',
                cell__format=lambda row, **kwargs: row.format(row=row, **kwargs),
            ),
        )

        return call_target(parts__all_models=table, **kwargs)

    @classmethod
    @class_shortcut(
        table=EMPTY,
    )
    @require_login
    def list(cls, request, app_name, model_name, table, call_target=None, **kwargs):
        model = django_apps.all_models[app_name][model_name]

        if not cls.has_permission(request, operation='list', model=model):
            raise Http404()

        table = setdefaults_path(
            Namespace(),
            table,
            call_target__cls=cls.get_meta().table_class,
            auto__model=model,
            columns=dict(
                select__include=True,
                edit=dict(
                    call_target__attribute='edit',
                    after=0,
                    cell__url=lambda row, **_: '%s/edit/' % row.pk,
                ),
                delete=dict(
                    call_target__attribute='delete',
                    after=LAST,
                    cell__url=lambda row, **_: '%s/delete/' % row.pk,
                ),
            ),
            actions=dict(
                create=dict(
                    display_name=gettext('Create %(model_name)s') % dict(model_name=model._meta.verbose_name),
                    attrs__href='create/',
                ),
            ),
            query_from_indexes=True,
            bulk__actions__delete__include=True,
        )

        return call_target(
            parts__header__children__link__attrs__href='../..',
            **{f'parts__list_{app_name}_{model_name}': table},
            **kwargs,
        )

    @classmethod
    @class_shortcut(
        form=EMPTY,
    )
    @require_login
    def crud(cls, request, operation, form, app_name, model_name, pk=None, call_target=None, **kwargs):
        model = django_apps.all_models[app_name][model_name]
        instance = model.objects.get(pk=pk) if pk is not None else None

        if not cls.has_permission(request, operation=operation, model=model, instance=instance):
            raise Http404()

        def on_save(form, instance, **_):
            message = f'{form.model._meta.verbose_name.capitalize()} {instance} was ' + (
                'created' if form.extra.is_create else 'updated'
            )
            messages.add_message(request, messages.INFO, message, fail_silently=True)

        def on_delete(form, instance, **_):
            message = f'{form.model._meta.verbose_name.capitalize()} {instance} was deleted'
            messages.add_message(request, messages.INFO, message, fail_silently=True)

        form = setdefaults_path(
            Namespace(),
            form,
            call_target__cls=cls.get_meta().form_class,
            auto__instance=instance,
            auto__model=model,
            call_target__attribute=operation,
            extra__on_save=on_save,
            extra__on_delete=on_delete,
        )

        return call_target(
            **{f'parts__{operation}_{app_name}_{model_name}': form},
            **kwargs,
        )

    @classmethod
    @class_shortcut(
        call_target__attribute='crud',
        operation='create',
        parts__header__children__link__attrs__href='../../..',
    )
    def create(cls, request, call_target, **kwargs):
        return call_target(request=request, **kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='crud',
        operation='edit',
        parts__header__children__link__attrs__href='../../../..',
    )
    def edit(cls, request, call_target, **kwargs):
        return call_target(request=request, **kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='crud',
        operation='delete',
        parts__header__children__link__attrs__href='../../../..',
    )
    def delete(cls, request, call_target, **kwargs):
        return call_target(request=request, **kwargs)

    @classmethod
    def urls(cls):
        return Struct(
            urlpatterns=[
                path('', cls.all_models),
                path('<app_name>/<model_name>/', cls.list),
                path('<app_name>/<model_name>/create/', cls.create),
                path('<app_name>/<model_name>/<int:pk>/edit/', cls.edit),
                path('<app_name>/<model_name>/<int:pk>/delete/', cls.delete),
            ]
            + Auth.urls().urlpatterns
        )


class Auth:
    @classmethod
    def login(cls, request):
        return LoginPage()

    @classmethod
    def logout(cls, request):
        auth.logout(request)
        return HttpResponseRedirect('/')

    @classmethod
    def change_password(cls, request):
        return ChangePasswordPage()

    @classmethod
    def urls(cls):
        return Struct(
            urlpatterns=[
                path('login/', cls.login),
                path('logout/', cls.logout),
                path('change_password/', cls.change_password),
            ]
        )


class LoginForm(Form):
    username = Field(display_name=gettext('Username'))
    password = Field.password(display_name=gettext('Password'))

    class Meta:
        title = gettext('Login')

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

                form.add_error(gettext('Unknown username or password'))


class LoginPage(Page):
    form = LoginForm()
    set_focus = html.script(
        mark_safe(
            'document.getElementById("id_username").focus();',
        )
    )


def current_password__is_valid(form, parsed_data, **_):
    return (
        (True, None)
        if check_password(parsed_data, form.get_request().user.password)
        else (False, gettext('Incorrect password'))
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
        else (False, gettext('New passwords does not match'))
    )


class ChangePasswordForm(Form):
    class Meta:
        title = gettext('Change password')

        @staticmethod
        def actions__submit__post_handler(form, request, **_):
            if form.is_valid():
                user = request.user
                user.set_password(form.fields.new_password.value)
                user.save()
                return HttpResponseRedirect('..')

    current_password = Field.password(is_valid=current_password__is_valid, display_name=gettext('Current password'))
    new_password = Field.password(is_valid=new_password__is_valid, display_name=gettext('New password'))
    confirm_password = Field.password(is_valid=confirm_password__is_valid, display_name=gettext('Confirm password'))


class ChangePasswordPage(Page):
    form = ChangePasswordForm()
    set_focus = html.script(
        mark_safe(
            'document.getElementById("id_current_password").focus();',
        )
    )
