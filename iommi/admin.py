from django.apps import apps
from tri_declarative import (
    dispatch,
    Namespace,
    setdefaults_path,
    EMPTY,
    LAST,
)
from tri_struct import Struct

from iommi import (
    Page,
    html,
    Table,
    Form,
)
from iommi.from_model import (
    get_fields,
)

model_by_app_and_name = {
    (app_name, model_name): model
    for app_name, models in apps.all_models.items()
    for model_name, model in models.items()
}

app_and_name_by_model = {
    v: k
    for k, v in model_by_app_and_name.items()
}

admin_h1 = html.h1(html.a('Admin', attrs__href='/iommi-admin/'), after=0)


@dispatch(
    app=EMPTY,
    table=EMPTY,
)
def all_models(app, table, **kwargs):
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
)
def list_model(model, app, table):
    app_name, model_name = app_and_name_by_model[model]
    kwargs = setdefaults_path(
        Namespace(),
        app.get(app_name, {}).get(model_name, {}),
        table=table,
        table__auto=dict(
            model=model,
            additional=dict(
                edit=dict(call_target__attribute='edit', after=0, cell__url=lambda row, **_: '%s/edit/' % row.pk),
                delete=dict(call_target__attribute='delete', after=LAST, cell__url=lambda row, **_: '%s/delete/' % row.pk),
            ),
        ),
        table__actions=dict(
            create=dict(
                display_name=f'Create {model._meta.verbose_name}',
                attrs__href='create/',
            ),
        ),
        table__query_from_indexes=True,
        table__columns__select__include=True,
        table__bulk__actions__delete__include=True,
    )
    for field in get_fields(model):
        if getattr(field, 'unique', False):
            continue
        setdefaults_path(
            kwargs,
            **{'table__columns__' + field.name + '__bulk__include': True},
        )

    return kwargs.table().as_page(
        title=f'{model._meta.verbose_name}',
        parts__header=admin_h1,
    )


@dispatch(
    all_models__call_target=all_models,
    list_model__call_target=list_model,
    create_object__call_target__attribute='as_create_page',
    delete_object__call_target__attribute='as_delete_page',
    edit_object__call_target__attribute='as_edit_page',
    table__call_target__cls=Table,
    form__call_target__cls=Form,
    form__parts__header=admin_h1,
)
def admin(app_name, model_name, pk, command, all_models, list_model, create_object, edit_object, delete_object, table, form):

    def check_kwargs(kw):
        if not kw:
            return

        for app_name, model_names in kw.items():
            assert app_name in apps.all_models
            for model_name in model_names:
                assert (app_name, model_name) in model_by_app_and_name, f"You supplied a config for {app_name, model_name}, but it doesn't exist!"

    check_kwargs(all_models.get('app'))
    check_kwargs(list_model.get('app'))
    check_kwargs(create_object.get('app'))
    check_kwargs(edit_object.get('app'))
    check_kwargs(delete_object.get('app'))

    if app_name is None and model_name is None:
        return all_models(table=table)

    model = apps.all_models[app_name][model_name]

    if command is None:
        assert pk is None
        return list_model(model=model, table=table)

    if command == 'create':
        assert pk is None
        return Namespace(create_object, form)(model=model)

    instance = model.objects.get(pk=pk)

    if command == 'edit':
        return Namespace(edit_object, form)(model=model, instance=instance)

    if command == 'delete':
        return Namespace(delete_object, form)(model=model, instance=instance)

    assert False, 'unknown command %s' % command
