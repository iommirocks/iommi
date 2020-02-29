from typing import Type

from django.apps import apps
from django.conf.urls import url
from tri_declarative import (
    class_shortcut,
    EMPTY,
    LAST,
    Namespace,
    Refinable,
    setdefaults_path,
)
from tri_struct import Struct

from iommi import (
    Form,
    html,
    Page,
    Table,
)
from iommi.from_model import get_fields

model_by_app_and_name = {
    (app_name, model_name): model
    for app_name, models in apps.all_models.items()
    for model_name, model in models.items()
}

app_and_name_by_model = {
    v: k
    for k, v in model_by_app_and_name.items()
}


class Admin(Page):

    class Meta:
        table_class = Table
        form_class = Form

    table_class: Type[Table] = Refinable()
    form_class: Type[Form] = Refinable()

    header = html.h1(children__link=html.a(children__text='Admin'), after=0)

    @classmethod
    @class_shortcut(
        app=EMPTY,
        table=EMPTY,
    )
    def all_models(cls, request, app, table, call_target=None, **kwargs):

        def app_data():
            for app_name, models in apps.all_models.items():
                for name, model_cls in models.items():
                    if app.get(app_name, {}).get(name, {}).get('include', True):
                        yield Struct(app_name=app_name, model_name=name, model=model_cls)

        table = setdefaults_path(
            Namespace(),
            table,
            call_target__cls=cls.get_meta().table_class,
            sortable=False,
            rows=app_data(),
            columns=dict(
                app_name__auto_rowspan=True,
                model_name__cell__url=lambda row, **_: '%s/%s/' % (row.app_name, row.model_name),
            )
        )

        return call_target(
            parts__title=html.h2('All models'),
            parts__table=table,
            **kwargs
        )

    @classmethod
    @class_shortcut(
        app=EMPTY,
        table=EMPTY,
    )
    def list(cls, request, app_name, model_name, app, table, call_target=None, **kwargs):
        model = apps.all_models[app_name][model_name]
        app_name, model_name = app_and_name_by_model[model]

        table = setdefaults_path(
            Namespace(),
            table,
            call_target__cls=cls.get_meta().table_class,
            title=f'{model._meta.verbose_name}',
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
            parts__table=table,
            parts__header__children__link__attrs__href='../..',
            **app.get(app_name, {}).get(model_name, {}),
            **kwargs,
        )

    @classmethod
    @class_shortcut(
        form=EMPTY,
    )
    def crud(cls, request, form, app_name, model_name, pk=None, call_target=None, **kwargs):
        del request
        model = apps.all_models[app_name][model_name]
        instance = model.objects.get(pk=pk) if pk is not None else None

        form = setdefaults_path(
            Namespace(),
            form,
            call_target__cls=cls.get_meta().form_class,
            auto__instance=instance,
            auto__model=model,
        )

        return call_target(
            parts__form=form,
            **kwargs,
        )

    @classmethod
    @class_shortcut(
        call_target__attribute='crud',
        form__call_target__attribute='create',
        parts__header__children__link__attrs__href='../../..',
    )
    def create(cls, request, call_target, **kwargs):
        return call_target(request=request, **kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='crud',
        form__call_target__attribute='edit',
        parts__header__children__link__attrs__href='../../../..',
    )
    def edit(cls, request, call_target, **kwargs):
        return call_target(request=request, **kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='crud',
        form__call_target__attribute='delete',
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
