import functools
from traceback import print_stack
from typing import Type
from urllib.parse import urlencode

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib import (
    messages,
)
from django.db.models import Model
from django.http import (
    Http404,
    HttpResponseRedirect,
)
from django.urls import (
    path,
    reverse,
)
from django.utils.translation import gettext_lazy

from iommi import (
    EditTable,
    Form,
    Fragment,
    html,
    LAST,
    Menu,
    MenuItem,
    Page,
    Table,
)
from iommi._web_compat import format_html
from iommi.base import (
    build_as_view_wrapper,
    capitalize,
    items,
    values,
)
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    flatten,
    Namespace,
    setdefaults_path,
)
from iommi.refinable import Refinable
from iommi.shortcut import with_defaults
from iommi.struct import Struct
from iommi.views import (
    auth_views,
    change_password,
    login,
    logout,
)

app_verbose_name_by_label = {
    config.label: config.verbose_name.replace('_', ' ') for config in values(django_apps.app_configs)
}

joined_app_name_and_model = {
    f'{app_name}_{model_name}'
    for app_name, models in items(django_apps.all_models)
    for model_name, model in items(models)
}


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



class Admin(Page):
    class Meta:
        table_class = EditTable
        form_class = Form

    model: Type[Model] = Refinable()
    instance: Model = Refinable()
    app_name: str = Refinable()
    model_name: str = Refinable()
    operation: str = Refinable()
    table_class: Type[Table] = Refinable()
    form_class: Type[Form] = Refinable()

    # Global configuration on apps level
    apps: Namespace = Refinable()

    menu = Menu(
        include=lambda request, **_: getattr(request, 'iommi_main_menu', None) is None,
        sub_menu=dict(
            root=MenuItem(
                url=lambda admin, **_: reverse('iommi.Admin.all_models', current_app=admin.app_name),
                display_name=gettext_lazy('iommi administration'),
            ),
            change_password=MenuItem(
                url=lambda admin, **_: reverse(change_password, current_app=admin.app_name),
                display_name=gettext_lazy('Change password'),
            ),
            logout=MenuItem(
                url=lambda admin, **_: reverse(logout, current_app=admin.app_name),
                display_name=gettext_lazy('Logout'),
            ),
        ),
    )

    @read_config
    @with_defaults(
        apps__auth_user__include=True,
        parts__edit_auth_user__fields__password__write_to_instance=lambda instance, value, **_: instance.set_password(value),
        parts__edit_auth_user__fields__password__read_from_instance=lambda **_: '',
        apps__auth_group__include=True,
        parts__messages=Messages(),
        parts__list_auth_user=dict(
            auto__include=['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_superuser'],
            columns=dict(
                username__filter=dict(
                    include=True,
                    freetext=True,
                ),
                email__filter=dict(
                    include=True,
                    freetext=True,
                ),
                first_name__filter=dict(
                    include=True,
                    freetext=True,
                ),
                last_name__filter=dict(
                    include=True,
                    freetext=True,
                ),
                is_staff__filter__include=True,
                is_active__filter__include=True,
                is_superuser__filter__include=True,
            ),
        ),
    )
    @dispatch(
        apps=EMPTY,
        parts=EMPTY,
    )
    def __init__(self, apps, parts, **kwargs):
        # Validate apps params
        for k in apps.keys():
            assert k in joined_app_name_and_model, (
                f'{k} is not a valid app/model key.\n\n'
                f'Valid keys:\n    ' + '\n    '.join(sorted(joined_app_name_and_model))
            )
        super(Admin, self).__init__(parts=parts, apps=apps, **kwargs)

    def refine_with_params(self, app_name: str = None, model_name: str = None, pk: str = None):
        refined_admin = self.refine(app_name=app_name, model_name=model_name)

        model = django_apps.all_models[app_name][model_name] if app_name and model_name else None
        try:
            instance = model.objects.get(pk=pk) if pk is not None else None
        except model.DoesNotExist:
            raise Http404()

        if model is not None and instance is None:
            refined_admin = refined_admin.refine(model=model, parts__table__auto__model=model)

        if instance is not None:
            refined_admin = refined_admin.refine(instance=instance, parts__form__auto__instance=instance)

        return refined_admin

    def as_view(self):
        def admin_view(request, *args, **kwargs):
            app_name = kwargs.pop('app_name', None)

            if not getattr(request, 'user', None) or not request.user.is_authenticated:
                return HttpResponseRedirect(
                    f'{reverse(login, current_app=app_name)}?{urlencode(dict(next=request.path))}'
                )

            final_page = self.refine_with_params(
                app_name=app_name,
                model_name=kwargs.pop('model_name', None),
                pk=kwargs.pop('pk', None),
            ).refine_done()

            if not self.has_permission(
                request, instance=final_page.instance, model=final_page.model, operation=final_page.operation
            ):
                raise Http404()

            view = build_as_view_wrapper(final_page)

            return view(request, *args, **kwargs)

        return admin_view

    def on_refine_done(self):
        part_name = ''
        assert self.operation
        part_name += self.operation
        if self.app_name:
            part_name += '_' + self.app_name
        if self.model_name:
            part_name += '_' + self.model_name

        table = self.parts.get('table')
        if table is not None:
            setdefaults_path(self.parts, **{part_name: flatten(table)})
            self.parts.table = None

        form = self.parts.get('form')
        if form is not None:
            setdefaults_path(self.parts, **{part_name: flatten(form)})
            self.parts.form = None

        def should_throw_away(k, v):
            if k == part_name:
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

        self.parts = {
            # Arguments that are not for us needs to be thrown on the ground
            k: None if should_throw_away(k, v) else v
            for k, v in items(self.parts)
        }

        super(Admin, self).on_refine_done()

    @staticmethod
    def has_permission(request, operation, model=None, instance=None):
        if request.user.is_superuser:
            return True

        if not request.user.is_staff:
            return False

        if model is None:
            return True

        action = {
            'create': 'add',
            'edit': 'change',
            'list': 'view',
        }.get(operation, operation)

        return request.user.has_perm(f'{model._meta.app_label}.{action}_{model._meta.model_name}')

    def own_evaluate_parameters(self):
        return dict(admin=self, **super(Admin, self).own_evaluate_parameters())

    @classmethod
    @with_defaults(
        operation='all_models',
    )
    def all_models(cls, table=None, **kwargs):
        def rows_raw(admin, request, included_filter=False, **_):
            for app_name, models in items(django_apps.all_models):
                for model_name, model in sorted(items(models), key=lambda x: x[1]._meta.verbose_name_plural):
                    key = f'{app_name}_{model_name}'
                    conf = admin.apps.get(key, {})
                    included = conf.get('include', False)
                    if included == included_filter:
                        continue

                    if not cls.has_permission(request, instance=None, model=model, operation='view'):
                        continue

                    group = conf.get('group', app_verbose_name_by_label[app_name])

                    yield Struct(
                        name=conf.get('name', model._meta.verbose_name_plural.capitalize()),
                        group=group,
                        app_name=app_name,
                        model_name=model_name,
                        url='{}/{}/'.format(app_name, model_name),
                        format=lambda row, **_: row.name,
                        key=key,
                    )

        def rows(admin, request, included_filter=False, **_):
            last_group = None
            for row in sorted(rows_raw(admin=admin, request=request, included_filter=included_filter), key=lambda row: (row.group, row.name)):
                if last_group != row.group:
                    yield Struct(
                        name=row.group,
                        url=None,
                        format=lambda row, table, **_: (
                            html.h1(row.name, _name='invalid_name').bind(parent=table).__html__()
                        ),
                        key=None,
                    )
                    last_group = row.group
                yield row

        table = setdefaults_path(
            Namespace(),
            table if table is not None else {},
            title='',
            call_target__cls=cls.get_meta().table_class,
            call_target__attribute='div',
            sortable=False,
            rows=rows,
            page_size=None,
            columns__name=dict(
                cell__url=lambda row, **_: row.url if getattr(row, 'pk', None) != '#sentinel#' else None,
                display_name='',
                cell__format=lambda row, **format_kwargs: (
                    row.format(row=row, **format_kwargs) if getattr(row, 'pk', None) != '#sentinel#' else ''
                ),
            ),
            edit_actions__add_row__include=False,
            edit_actions__save__include=False,
            attrs__class__table=False,
        )

        add_models = setdefaults_path(
            Namespace(),
            include=settings.DEBUG,
            call_target__cls=cls.get_meta().table_class,
            sortable=False,
            create_form=None,
            rows=functools.partial(rows_raw, included_filter=True),
            page_size=None,
            columns__app_name=cls.get_meta().table_class.get_meta().member_class(auto_rowspan=True),
            columns__conf=(
                cls.get_meta()
                .table_class.get_meta()
                .member_class(
                    cell__value=lambda row, **_: f'apps__{row.key}__include = True' if row.key else '',
                    cell__format=lambda value, **_: (
                        format_html(
                            '''
                                {}
                                <span style="margin-left: 1rem" onclick="navigator.clipboard.writeText('{}')">
                                    <i class="fa fa-copy"></i>
                                </span>
                            ''',
                            value,
                            value,
                        )
                        if value
                        else ''
                    ),
                    # cell__url=lambda row, **_: f'{row.url}add_model/' if row.key else None,
                    after=LAST,
                )
            ),
            columns__name=dict(
                display_name='',
                cell__format=lambda row, **format_kwargs: (
                    row.format(row=row, **format_kwargs) if getattr(row, 'pk', None) != '#sentinel#' else ''
                ),
            ),
            edit_actions__add_row__include=False,
            edit_actions__save__include=False,
        )

        return cls(
            parts=dict(
                all_models=table,
                add_models_title=html.h1(gettext_lazy('Add models to admin'), include=settings.DEBUG),
                add_models_help_text=html.p(
                    format_html(
                        '''
                            Copy the conf value to the `Meta` class of an `iommi_admin.py` file.

                            Read <a href="https://docs.iommi.rocks//admin.html#customization">the docs for admin customization</a> for more information.
                        ''',
                    ),
                    include=settings.DEBUG,
                ),
                add_models=add_models,
            ),
            **kwargs,
        )

    @classmethod
    @dispatch(
        operation='list',
    )
    def list(cls, table=None, **kwargs):
        table = setdefaults_path(
            Namespace(),
            table if table is not None else {},
            call_target__cls=cls.get_meta().table_class,
            columns=dict(
                edit=dict(
                    call_target__attribute='edit',
                    after=0,
                    cell__url=lambda row, **_: '%s/edit/' % row.pk,
                ),
                delete=dict(
                    call_target__attribute='delete',
                    after=LAST,
                    include=lambda request, table, **_: (
                        cls.has_permission(request, instance=None, model=table.model, operation='delete')
                    ),
                ),
            ),
            actions=dict(
                create=dict(
                    display_name=lambda page, **_: (
                        gettext_lazy('Create %(model_name)s') % dict(model_name=page.model._meta.verbose_name)
                    ),
                    attrs__href='create/',
                ),
            ),
            query_from_indexes=True,
        )

        return cls(
            parts__header__children__link__attrs__href='../..',
            parts__table=table,
            **kwargs,
        )

    @classmethod
    @with_defaults
    def crud(cls, operation, form=None, **kwargs):
        def on_save(request, form, instance, **_):
            message = f'{form.model._meta.verbose_name.capitalize()} {instance} was ' + (
                'created' if form.extra.is_create else 'updated'
            )
            messages.add_message(request, messages.INFO, message, fail_silently=True)

        def on_delete(request, form, instance, **_):
            message = f'{form.model._meta.verbose_name.capitalize()} {instance} was deleted'
            messages.add_message(request, messages.INFO, message, fail_silently=True)

        form = setdefaults_path(
            Namespace(),
            form if form is not None else {},
            call_target__cls=cls.get_meta().form_class,
            call_target__attribute=operation,
            extra__on_save=on_save,
            extra__on_delete=on_delete,
            actions__submit__include=lambda request, form, **_: cls.has_permission(
                request, instance=None, model=form.model, operation=operation
            ),
            editable=lambda request, form, **_: (
                False
                if operation == 'delete'
                else cls.has_permission(request, instance=None, model=form.model, operation=operation)
            ),
        )

        return cls(
            parts__form=form,
            operation=operation,
            **kwargs,
        )

    @classmethod
    @with_defaults(
        parts__header__children__link__attrs__href='../../..',
    )
    def create(cls, **kwargs):
        return cls.crud(
            operation='create',
            **kwargs,
        )

    @classmethod
    @with_defaults(
        parts__header__children__link__attrs__href='../../../..',
    )
    def edit(cls, **kwargs):
        return cls.crud(
            operation='edit',
            **kwargs,
        )

    @classmethod
    @with_defaults(
        parts__header__children__link__attrs__href='../../../..',
    )
    def delete(cls, **kwargs):
        return cls.crud(
            operation='delete',
            **kwargs,
        )

    @classmethod
    def urls(cls):
        return Struct(
            urlpatterns=[
                path('', cls.all_models().as_view(), name='iommi.Admin.all_models'),
                path('<app_name>/<model_name>/', cls.list().as_view(), name='iommi.Admin.list'),
                path('<app_name>/<model_name>/create/', cls.create().as_view(), name='iommi.Admin.create'),
                path('<app_name>/<model_name>/<int:pk>/edit/', cls.edit().as_view(), name='iommi.Admin.edit'),
                path('<app_name>/<model_name>/<int:pk>/delete/', cls.delete().as_view(), name='iommi.Admin.delete'),
                path('', auth_views()),
            ]
        )

    @classmethod
    def m(cls):
        from iommi.experimental.main_menu import M
        return M(
            view=cls.all_models(),
            display_name=capitalize(gettext_lazy('admin')),
            paths=cls.urls().urlpatterns,
        )
