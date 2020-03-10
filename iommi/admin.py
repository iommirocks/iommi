from typing import Type

from django.apps import apps as django_apps
from django.conf.urls import url
from django.http import Http404
from tri_declarative import (
    class_shortcut,
    EMPTY,
    LAST,
    Namespace,
    Refinable,
    setdefaults_path,
    dispatch,
    with_meta,
)
from tri_struct import Struct

from iommi import (
    Form,
    html,
    Page,
    Table,
)
from iommi.from_model import get_fields
from iommi.traversable import reinvokable

model_by_app_and_name = {
    (app_name, model_name): model
    for app_name, models in django_apps.all_models.items()
    for model_name, model in models.items()
}


@with_meta  # we need @with_meta again here to make sure this constructor gets all the meta arguments first
class Admin(Page):

    class Meta:
        table_class = Table
        form_class = Form
        apps__sessions_session__include = False
        parts__list_auth_user__columns__password__include = False

    table_class: Type[Table] = Refinable()
    form_class: Type[Form] = Refinable()

    apps: Namespace = Refinable()  # Global configuration on apps level

    @reinvokable
    @dispatch(
        apps=EMPTY,
        parts=EMPTY,
    )
    def __init__(self, parts, **kwargs):
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
            for k, v in parts.items()
        }

        super(Admin, self).__init__(parts=parts, **kwargs)

    @staticmethod
    def has_permission(request, operation, model=None, instance=None):
        return request.user.is_staff

    header = html.h1(children__link=html.a(children__text='Admin'), after=0)

    def own_evaluate_parameters(self):
        return dict(admin=self, **super(Admin, self).own_evaluate_parameters())

    @classmethod
    @class_shortcut(
        table=EMPTY,
    )
    def all_models(cls, request, table, call_target=None, **kwargs):
        if not cls.has_permission(request, operation='all_models'):
            raise Http404()

        def preprocess_rows(admin, rows, **_):
            return [
                row
                for row in rows
                if admin.apps.get(f'{row.app_name}_{row.model_name}', {}).get('include', True)
            ]

        table = setdefaults_path(
            Namespace(),
            table,
            title='All models',
            call_target__cls=cls.get_meta().table_class,
            sortable=False,
            rows=[
                Struct(app_name=app_name, model_name=model_name, model=model)
                for (app_name, model_name), model in model_by_app_and_name.items()
            ],
            preprocess_rows=preprocess_rows,
            columns=dict(
                app_name__auto_rowspan=True,
                app_name__after=0,
                model_name__cell__url=lambda row, **_: '%s/%s/' % (row.app_name, row.model_name),
            ),
        )

        return call_target(
            parts__all_models=table,
            **kwargs
        )

    @classmethod
    @class_shortcut(
        table=EMPTY,
    )
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
                    display_name=f'Create {model._meta.verbose_name}',
                    attrs__href='create/',
                ),
            ),
            query_from_indexes=True,
            bulk__actions__delete__include=True,
            **{
                'columns__' + field.name + '__bulk__include': True
                for field in get_fields(model)
                if not getattr(field, 'unique', False)
            },
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
    def crud(cls, request, operation, form, app_name, model_name, pk=None, call_target=None, **kwargs):
        model = django_apps.all_models[app_name][model_name]
        instance = model.objects.get(pk=pk) if pk is not None else None

        if not cls.has_permission(request, operation=operation, model=model, instance=instance):
            raise Http404()

        form = setdefaults_path(
            Namespace(),
            form,
            call_target__cls=cls.get_meta().form_class,
            auto__instance=instance,
            auto__model=model,
            call_target__attribute=operation,
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
                url(r'^$', cls.all_models),
                url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/$', cls.list),
                url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/create/$', cls.create),
                url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/(?P<pk>\d+)/edit/$', cls.edit),
                url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/(?P<pk>\d+)/delete/$', cls.delete),
            ]
        )
