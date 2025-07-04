from collections import defaultdict
from typing import (
    Dict,
    Optional,
    Type,
)

from django.db.models import QuerySet
from django.http import HttpResponseRedirect
from django.template import (
    Context,
    Template,
)
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from iommi._web_compat import render_template
from iommi.action import (
    Action,
    Actions,
    group_actions,
)
from iommi.asset import Asset
from iommi.base import (
    MISSING,
    NOT_BOUND_MESSAGE,
    items,
    keys,
    values,
)
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    getattr_path,
    Namespace,
    setdefaults_path,
)
from iommi.declarative.util import strip_prefix
from iommi.endpoint import (
    DISPATCH_PATH_SEPARATOR,
    path_join,
)
from iommi.form import (
    find_unique_prefixes,
    FULL_FORM_FROM_REQUEST,
    Field,
    Form,
)
from iommi.member import (
    bind_member,
    bind_members,
    refine_done_members,
)
from iommi.refinable import (
    Refinable,
    RefinableMembers,
    refinable,
)
from iommi.shortcut import with_defaults
from iommi.struct import Struct
from iommi.table import (
    Cell,
    Cells,
    Column,
    Table,
)


class EditCell(Cell):
    def get_path(self):
        return path_join(self.column.iommi_path, str(self.row.pk))

    def render_cell_contents(self):
        field = self.cells.get_field(self.column)

        if field:
            orig_attr = field.attr
            if self.cells.is_create_template:
                field.attr = None

            path = self.get_path()

            field.initial = MISSING
            field.raw_data = None
            field.value = None
            field.parsed_data = None
            field._errors = set()
            field.form.instance = self.row
            field._iommi_path_override = path

            bind_field_from_instance(field, self.row)

            input_html = field.input.__html__()

            field.attr = orig_attr

            # Check both edit_errors and create_errors
            errors = None
            if self.table.edit_errors:
                errors = self.table.edit_errors.get(path)
            if not errors and self.table.create_errors:
                errors = self.table.create_errors.get(path)

            if errors:
                return Template(
                    '{{ input_html }}<br><span class="text-danger"><ul class="errors">{% for error in errors %}<li>{{ error }}</li>{% endfor %}</ul></span>'
                ).render(context=Context(dict(input_html=input_html, errors=errors)))

            return input_html
        else:
            return super().render_cell_contents()

    def on_refine_done(self):
        if self.cells.is_create_template:
            self.value = None
        super(EditCell, self).on_refine_done()

def bind_field_from_instance(field, instance):
    field.input = field.iommi_namespace.input(_name='input')
    field.non_editable_input = field.iommi_namespace.non_editable_input(_name='non_editable_input')
    field.editable = field.iommi_namespace.editable
    field.initial = field.iommi_namespace.initial
    field._evaluate_parameters['instance'] = instance

    field.bind_from_instance()


class EditCells(Cells):
    is_create_template = Refinable()

    class Meta:
        cell_class = EditCell
        is_create_template = False

    def get_field(self, column):
        table = self.iommi_evaluate_parameters()['table']
        if self.is_create_template:
            return table.create_form.fields.get(column.iommi_name(), None)
        else:
            return table.edit_form.fields.get(column.iommi_name(), None)

    def iter_editable_cells(self):
        table = self.iommi_evaluate_parameters()['table']
        for column in values(table.columns):
            field = self.get_field(column)
            if not field:
                continue
            yield self.cell_class(cells=self, column=column, parent=self)


class EditColumn(Column):
    # language=rst
    """
    The column class for `EditTable`.
    """

    field: Field = Refinable()

    def on_refine_done(self):
        super(EditColumn, self).on_refine_done()
        self.field = None

    @classmethod
    @with_defaults(
        header__template='iommi/table/header.html',
        sortable=False,
        filter__is_valid_filter=lambda **_: (True, ''),
        filter__field__include=False,
        attr=None,
        display_name=gettext_lazy('Delete'),
        cell__attrs__class__delete=True,
        **{
            "cell__attrs__data-iommi-edit-table-delete-row-cell": True,
        },
    )
    def delete(cls, **kwargs):
        def cell__value(row, table, cells, column, **_):
            if isinstance(table.rows, QuerySet):
                row_id = row.pk
            else:
                # row_index is the visible row number
                # See selection() for the code that does the lookup
                row_id = cells.row_index
            button = Action.delete(
                display_name=column.display_name,
                attrs__type="button",
                attrs__accesskey=None,
                **{
                    "attrs__data-iommi-edit-table-delete-row-button": True,
                },
            ).bind()
            path = path_join(table.iommi_path, f'pk_delete_{row_id}')
            checkbox = (
                f'<input type="checkbox" name="{path}" id="id_{path}" data-iommi-edit-table-delete-row-checkbox="" />'
                f'<label for="id_{path}"> {column.display_name}</label>'
            )
            return mark_safe(f'{button.__html__()}{checkbox}')

        setdefaults_path(kwargs, dict(cell__value=cell__value))
        return cls(**kwargs)

    @classmethod
    @dispatch(
        field=EMPTY,
    )
    def hardcoded(cls, **kwargs):
        assert (
            'parsed_data' in kwargs['field']
        ), 'Specify a hardcoded value by specifying `field__parsed_data` as a callable'
        return cls(**kwargs)


def edit_table__post_handler(table, request, **_):
    # 1. Validate all the fields
    table.edit_errors = defaultdict(set)
    table.create_errors = defaultdict(set)
    parsed_data = {}

    assert table.edit_form._is_bound
    assert table.create_form._is_bound
    table.edit_form.mode = FULL_FORM_FROM_REQUEST
    table.create_form.mode = FULL_FORM_FROM_REQUEST

    def validate(cells_iterator, form, errors):
        for cells in cells_iterator:
            if not isinstance(cells, EditCells):
                continue
            instance = cells.row
            form.instance = instance
            for cell in cells.iter_editable_cells():
                path = cell.get_path()
                field = form.fields[cell.column.iommi_name()]
                field._iommi_path_override = path

                bind_field_from_instance(field, instance)
                if not field.editable:
                    field.value = field.initial

                field_errors = field.get_errors()
                if field_errors:
                    errors[path] |= set(field_errors)
                else:
                    parsed_data[path] = field.value

    validate(table.cells_for_rows(), table.edit_form, table.edit_errors)
    validate(table.cells_for_rows_for_create(), table.create_form, table.create_errors)

    if table.edit_errors or table.create_errors:
        return None

    if isinstance(table.initial_rows, QuerySet):
        prefix = path_join(table.iommi_path, 'pk_delete_')
        table.bulk_queryset(prefix=prefix).delete()

    def save(cells_iterator, form):
        to_save = []
        for cells in cells_iterator:
            if not isinstance(cells, EditCells):
                continue
            instance = cells.row
            form.instance = instance
            attrs_to_save = []
            for cell in cells.iter_editable_cells():
                path = cell.get_path()
                if path not in parsed_data:
                    continue
                value = parsed_data[path]
                field = form.fields[cell.column.iommi_name()]
                field._iommi_path_override = path
                if cells.is_create_template or (
                    field.invoke_callback(field.read_from_instance, instance=instance) != value
                ):
                    field.invoke_callback(field.write_to_instance, instance=instance, value=value)
                    if not field.extra.get('django_related_field', False):
                        attrs_to_save.append(field.attr)

            to_save.append((instance, attrs_to_save))

        to_save.sort(key=lambda x: abs(x[0].pk))
        for instance, attrs_to_save in to_save:
            if not to_save:
                pass
            if instance.pk is not None and instance.pk < 0:
                instance.pk = None
            if instance.pk is None:
                attrs_to_save = None

            if attrs_to_save is None:
                instance.save()
            else:
                for prefix in find_unique_prefixes(attrs_to_save):
                    model_object = instance
                    if prefix:  # Might be ''
                        model_object = getattr_path(model_object, prefix)
                    model_object.save(update_fields=[strip_prefix(x, prefix=f'{prefix}__') for x in attrs_to_save if x.startswith(prefix)])

    save(table.cells_for_rows(), table.edit_form)
    save(table.cells_for_rows_for_create(), table.create_form)

    if 'post_save' in table.extra:
        table.invoke_callback(table.extra.post_save)

    return HttpResponseRedirect(request.META['HTTP_REFERER'])


class _EditTable_Lazy_tbody:
    """Custom tbody for EditTable that includes new rows when there are validation errors."""
    def __init__(self, table):
        self.table = table

    def __html__(self):
        rows = []

        for cells in self.table.cells_for_rows():
            rows.append(cells.__html__())

        if (self.table.create_errors or self.table.edit_errors) and self.table._has_new_rows():
            for cells in self.table.cells_for_rows_for_create():
                rows.append(cells.__html__())

        return mark_safe('\n'.join(rows))


class EditTable(Table):
    # language=rst
    """
    Describe an editable table. Example:

    .. code-block:: python

        table = EditTable(
            auto__model=Album,
            columns__name__field__include=True,
            columns__delete=EditColumn.delete(),
        )

        # @test
        show_output(table)
        # @end
    """

    edit_errors = None
    create_errors = None
    edit_form: Form = Refinable()
    create_form: Form = Refinable()
    form_class: Type[Form] = Refinable()
    parent_form: Optional[Form] = Refinable()
    edit_actions: Dict[str, Action] = RefinableMembers()

    class Meta:
        form_class = Form
        member_class = EditColumn
        cells_class = EditCells
        edit_actions = EMPTY
        edit_actions__save = dict(
            call_target__attribute='primary',
            display_name=gettext_lazy('Save'),
            post_handler=edit_table__post_handler,
            template=lambda table, **_: 'iommi/blank.html' if table.parent_form is not None else None,
        )
        edit_actions__add_row = Action.button(
            display_name=gettext_lazy('Add row'),
            attrs__type="button",
            **{
                "attrs__data-iommi-edit-table-add-row-button": True,
                "attrs__data-iommi-edit-table-path": lambda table, **_: table.iommi_dunder_path,
            }
        )
        edit_form = EMPTY
        create_form = EMPTY
        container__children__text__template = 'iommi/table/edit_table_container.html'

        bulk__include = True

        attrs = {
            'data-next-virtual-pk': '-1',
            'data-new-row-endpoint': lambda table, **_: table.endpoints.new_row.endpoint_path,
        }

        @staticmethod
        def endpoints__new_row__func(table, **kwargs):
            if table.model is not None:
                sentinel_row = table.model(pk='#sentinel#')
            else:
                sentinel_row = Struct(pk='#sentinel#', **{k: '' for k in keys(table.create_form.fields)})
            return {
                'html': table.cells_class(
                    row=sentinel_row,
                    row_index=-1,
                    is_create_template=True,
                    **table.row.as_dict()
                ).bind(parent=table.create_form).__html__()
            }

    def on_refine_done(self):
        super(EditTable, self).on_refine_done()

        if self.bulk is None:
            self.bulk = self.form_class(
                _name='bulk',
                attrs__method='post',
            ).refine_done(parent=self)

        fields = Struct()

        for name, column in items(self.iommi_namespace.columns):
            if not isinstance(column, EditColumn):
                continue
            if getattr(column, 'include', None) is False:
                continue

            edit_conf = column.iommi_namespace.get('field', None)

            if not edit_conf:
                continue
            if getattr(column.field, 'include', None) is False:
                continue

            if isinstance(edit_conf, dict):
                field = setdefaults_path(
                    Namespace(),
                    edit_conf,
                    model=self.model,
                    model_field_name=column.model_field_name,
                    attr=name if column.attr is MISSING else column.attr,
                )
            else:
                field = column.iommi_namespace.field

            fields[name] = field

        auto = Namespace(self.auto)

        if 'model' not in auto and 'rows' in auto:
            auto['model'] = auto.rows.model
        auto.pop('rows', None)

        if self.create_form is not None:
            form_params = setdefaults_path(
                Namespace(),
                self.create_form,
                fields=fields,
                _name='create_form',
                auto=auto,
            )
            self.create_form = self.form_class(**form_params)

        if auto:
            auto.default_included = False

        form_params = setdefaults_path(
            Namespace(),
            self.edit_form,
            fields=fields,
            _name='edit_form',
            auto=auto,
        )
        self.edit_form = self.form_class(**form_params)

        refine_done_members(
            self,
            name='edit_actions',
            members_from_namespace=self.edit_actions,
            cls=self.action_class,
            members_cls=Actions,
        )

        declared_fields = self.edit_form.iommi_namespace.fields
        self.edit_form = self.edit_form.refine_defaults(fields=declared_fields).refine_done()
        if self.create_form is not None:
            self.create_form = self.create_form.refine_defaults(fields=declared_fields).refine_done()

    def on_bind(self) -> None:
        super(EditTable, self).on_bind()
        bind_members(self, name='edit_actions')
        bind_member(self, name='edit_form')
        if self.create_form is not None:
            bind_member(self, name='create_form')

        # If this is a nested form register it with the parent, need
        # to do this early because is_target needs self.parent_form
        self.parent_form = None
        if self.iommi_parent() is not None:
            self.parent_form = self.iommi_parent().iommi_evaluate_parameters().get('form', None)
            if self.parent_form is not None:
                self.parent_form.nested_forms[self._name] = self
                self.outer.tag = None

        if self.create_form is not None:
            # Set next virtual PK to avoid conflicts with existing virtual rows
            virtual_pks = self._get_virtual_pks_from_post()
            if virtual_pks:
                self.attrs['data-next-virtual-pk'] = str(min(virtual_pks) - 1)

        self.tbody.children.text = _EditTable_Lazy_tbody(self)

    def is_valid(self):
        return not self.edit_errors and not self.create_errors

    def _get_virtual_pks_from_post(self):
        """Extract virtual PKs from POST data."""
        request = self.get_request()
        if not request or request.method != 'POST':
            return []

        prefix = self.iommi_path + DISPATCH_PATH_SEPARATOR if self.iommi_path else ''
        delete_prefix = prefix + 'pk_delete_'

        def parse_virtual_pk(k):
            if not k.startswith(prefix) or k.startswith(delete_prefix):
                return None
            parts = k[len(prefix) :].split(DISPATCH_PATH_SEPARATOR)
            if len(parts) < 2:
                return None
            try:
                return int(parts[-1])
            except ValueError:
                return None

        post_data = self.get_request().POST
        pks = {parse_virtual_pk(k) for k in keys(post_data)}
        virtual_pks = [
            k for k in pks
            if k is not None and k < 0 and f'{delete_prefix}{k}' not in post_data
        ]

        return sorted(virtual_pks, reverse=True)

    def _has_new_rows(self):
        virtual_pks = self._get_virtual_pks_from_post()
        return bool(virtual_pks)

    def cells_for_rows_for_create(self):
        """Yield a Cells instance for each create row sent from the client."""
        assert self._is_bound, NOT_BOUND_MESSAGE

        virtual_pks = self._get_virtual_pks_from_post()
        if not virtual_pks:
            return

        rows = [self.model(pk=pk) for pk in virtual_pks]

        for i, row in enumerate(rows):
            row = self.preprocess_row_for_create(table=self, row=row)
            assert row is not None, 'preprocess_row must return the row'
            yield self.cells_class(
                is_create_template=True,
                row=row,
                row_index=i,
                **self.row.as_dict(),
            ).bind(parent=self)

    def get_errors(self):
        return set()

    @staticmethod
    @refinable
    def preprocess_row_for_create(row, **_):
        return row

    @property
    def render_edit_actions(self):
        assert self._is_bound, NOT_BOUND_MESSAGE
        non_grouped_actions, grouped_actions = group_actions(self.edit_actions)
        return render_template(
            self.get_request(),
            self.actions_template,
            dict(
                actions=self.iommi_bound_members().edit_actions,
                non_grouped_actions=non_grouped_actions,
                grouped_actions=grouped_actions,
                table=self,
            ),
        )

    def should_render_form_tag(self):
        return self.parent_form is None
