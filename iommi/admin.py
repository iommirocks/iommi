from django.apps import apps
from django.conf.urls import url
from tri_declarative import (
    dispatch,
    EMPTY,
    LAST,
    Namespace,
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

admin_h1 = html.h1(html.a('Admin', attrs__href='/iommi-admin/'), after=0, _name='admin_h1')


@dispatch(
    app=EMPTY,
    table__call_target__cls=Table,
)
def all_models(request, app, table, **kwargs):
    column_cls = table.call_target.cls.get_meta().member_class

    def app_data():
        for app_name, models in apps.all_models.items():
            for name, cls in models.items():
                if app.get(app_name, {}).get(name, {}).get('include', True):
                    yield Struct(app_name=app_name, model_name=name, model=cls)

    table = setdefaults_path(
        table,
        sortable=False,
        rows=app_data(),
        columns=dict(
            app_name=column_cls(auto_rowspan=True),
            model_name=column_cls(cell__url=lambda row, **_: '%s/%s/' % (row.app_name, row.model_name)),
        )
    )

    return Page(
        title='Admin',
        parts__header=admin_h1,
        parts__title=html.h2('All models'),
        parts__table=table(),
        **kwargs
    )


@dispatch(
    app=EMPTY,
    table__call_target__cls=Table,
    auto=EMPTY,
)
def list_model(request, app_name, model_name, app, table, auto):
    model = apps.all_models[app_name][model_name]

    app_name, model_name = app_and_name_by_model[model]
    kwargs = setdefaults_path(
        Namespace(),
        app.get(app_name, {}).get(model_name, {}),
        table=table,
        table__auto=dict(
            model=model,
            **auto,
        ),
        table__columns__select__include=True,
        table__columns__edit=dict(call_target__attribute='edit', after=0, cell__url=lambda row, **_: '%s/edit/' % row.pk),
        table__columns__delete=dict(call_target__attribute='delete', after=LAST, cell__url=lambda row, **_: '%s/delete/' % row.pk),
        table__actions=dict(
            create=dict(
                display_name=f'Create {model._meta.verbose_name}',
                attrs__href='create/',
            ),
        ),
        table__query_from_indexes=True,
        table__bulk__actions__delete__include=True,
        table__h_tag=admin_h1,
    )
    for field in get_fields(model):
        if getattr(field, 'unique', False):
            continue
        setdefaults_path(
            kwargs,
            **{'table__columns__' + field.name + '__bulk__include': True},
        )

    return kwargs.table(title=f'{model._meta.verbose_name}')


def edit(request, app_name, model_name, pk):
    model = apps.all_models[app_name][model_name]
    instance = model.objects.get(pk=pk)
    return Form.edit(auto__instance=instance, h_tag=admin_h1)


def create(request, app_name, model_name):
    model = apps.all_models[app_name][model_name]
    return Form.edit(auto__model=model, h_tag=admin_h1)


def delete(request, app_name, model_name, pk):
    model = apps.all_models[app_name][model_name]
    instance = model.objects.get(pk=pk)
    return Form.delete(auto__instance=instance, h_tag=admin_h1)


urls = Struct(
    urlpatterns=[
        url(r'^$', all_models),
        url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/$', list_model),
        url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/create/$', create),
        url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/(?P<pk>\d+)/edit/$', edit),
        url(r'^(?P<app_name>\w+)/(?P<model_name>\w+)/(?P<pk>\d+)/delete/$', delete),
    ]
)
