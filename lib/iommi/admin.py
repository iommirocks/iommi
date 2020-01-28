from iommi import (
    Page,
    html,
    Table,
    Form,
)
from tri_declarative import (
    dispatch,
    Namespace,
    setdefaults_path,
    EMPTY,
)
from django.apps import apps
from tri_struct import Struct


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
        page_size=None,
        columns=dict(
            app_name=column_cls(auto_rowspan=True),
            model_name=column_cls(cell__url=lambda row, **_: '%s/%s/' % (row.app_name, row.model_name)),
        )
    )

    return Page(
        parts__header=admin_h1,
        parts__title=html.h2('All models'),
        parts__table=table(),
        **kwargs
    )


@dispatch(
    app=EMPTY,
)
def list_model(model, app, table):
    app_name, model_name = app_and_name_by_model[model]
    kwargs = setdefaults_path(
        Namespace(),
        app.get(app_name, {}).get(model_name, {}),
        table=table,
        table__rows=model.objects.all(),
        table__extra_columns=dict(
            select=dict(call_target__attribute='select', after=0),
            edit=dict(call_target__attribute='edit', after=0, cell__url=lambda row, **_: '%s/edit/' % row.pk),
            delete=dict(call_target__attribute='delete', after='select', cell__url=lambda row, **_: '%s/delete/' % row.pk),
        ),
        table__actions=dict(
            # TODO: bulk delete
            # bulk_delete=dict(call_target__attribute='submit', display_name='Delete', on_post=lambda table, **_: table.bulk_queryset().delete()),
            create=dict(
                display_name=f'Create {model._meta.verbose_name}',
                attrs__href='create/',
            ),
        ),
        table__call_target__attribute='from_model',
        table__query_from_indexes=True,
    )
    return kwargs.table().as_page(parts__header=admin_h1)


@dispatch(
    form__call_target__attribute='as_create_page',
)
def create_object(*, model, form, **kwargs):
    return form(
        model=model,
        parts__header=admin_h1,
        **kwargs
    )


@dispatch(
    form__call_target__attribute='as_delete_page',
)
def delete_object(*, pk, model, form, **kwargs):
    assert pk
    return form(
        instance=model.objects.get(pk=pk),
        parts__header=admin_h1,
        **kwargs
    )


@dispatch(
    form__call_target__attribute='as_edit_page',
)
def edit_object(*, pk, model, form, **kwargs):
    assert pk
    return form(
        instance=model.objects.get(pk=pk),
        parts__header=admin_h1,
        **kwargs
    )

# TODO: name, description, display_name field should be freetext searchable by default
# TODO: bulk edit?


@dispatch(
    all_models__call_target=all_models,
    list_model__call_target=list_model,
    create_object__call_target=create_object,
    delete_object__call_target=delete_object,
    edit_object__call_target=edit_object,
    table__call_target__cls=Table,
    form__call_target__cls=Form,
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

    elif command is None:
        assert pk is None
        return list_model(model=apps.all_models[app_name][model_name], table=table)

    elif command == 'create':
        assert pk is None
        return create_object(model=apps.all_models[app_name][model_name], form=form)

    elif command == 'edit':
        return edit_object(model=apps.all_models[app_name][model_name], pk=pk, form=form)

    elif command == 'delete':
        return delete_object(model=apps.all_models[app_name][model_name], pk=pk, form=form)

    else:
        assert False, 'unknown command %s' % command
