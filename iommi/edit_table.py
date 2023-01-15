from collections import defaultdict
from typing import (
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

from iommi.action import Action
from iommi.asset import Asset
from iommi.base import (
    items,
    keys,
    MISSING,
    NOT_BOUND_MESSAGE,
    values,
)
from iommi.declarative.namespace import (
    EMPTY,
    Namespace,
    setdefaults_path,
)
from iommi.endpoint import (
    DISPATCH_PATH_SEPARATOR,
    path_join,
)
from iommi.form import (
    Field,
    Form,
)
from iommi.fragment import (
    Fragment,
)
from iommi.refinable import (
    Refinable,
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
            field.input = field.iommi_namespace.input(_name='input')
            field.bind_from_instance()

            input_html = field.input.__html__()

            field.attr = orig_attr

            if self.table.edit_errors:
                errors = self.table.edit_errors.get(path)
                if errors:
                    return Template(
                        '{{ input_html }}<br><span class="text-danger"><ul class="errors">{% for error in errors %}<li>{{ error }}</li>{% endfor %}</ul></a>'
                    ).render(context=Context(dict(input_html=input_html, errors=errors)))

            return input_html
        else:
            return super().render_cell_contents()

    def on_refine_done(self):
        if self.cells.is_create_template:
            self.value = None
        super(EditCell, self).on_refine_done()


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
            if not column.render_column:
                continue

            field = self.get_field(column)
            if not field:
                continue
            yield self.cell_class(cells=self, column=column)


class EditColumn(Column):
    # language=rst
    """
    The column class for `EditTable`.
    """


    edit: Field = Refinable()

    def on_refine_done(self):
        super(EditColumn, self).on_refine_done()
        self.edit = None

    @classmethod
    @with_defaults(
        header__template='iommi/table/header.html',
        sortable=False,
        filter__is_valid_filter=lambda **_: (True, ''),
        filter__field__include=False,
        attr=None,
        display_name=gettext_lazy('Delete'),
        cell__attrs__class__delete=True,
        # language=js
        assets__fancy_delete=Asset(
            mark_safe(
                '''
                    $(document).ready(() => {
                        $('.edit_table_delete').click((event) => {
                            const checked = $(event.target).closest('tr').find('input')[0].checked;
                            $(event.target).closest('tr').find('input').prop("checked", !checked);
                            $(event.target).closest('tr')[0].style.opacity = checked ? "1.0" : "0.3";
                            event.preventDefault();
                            return false;
                        });
                    });
                '''
            ),
            tag='script',
        ),
    )
    def delete(cls, **kwargs):
        def cell__value(row, table, cells, column, **_):
            if isinstance(table.rows, QuerySet):
                row_id = row.pk
            else:
                # row_index is the visible row number
                # See selection() for the code that does the lookup
                row_id = cells.row_index
            button = Action.delete(display_name=column.display_name, attrs__class__edit_table_delete=True).bind()
            path = path_join(table.iommi_path, f'pk_delete_{row_id}')
            return mark_safe(f'{button.__html__()}<input style="display: none" type="checkbox" name="{path}" />')

        setdefaults_path(kwargs, dict(cell__value=cell__value))
        return cls(**kwargs)


def edit_table__post_handler(table, request, **_):
    # 1. Validate all the fields
    table.edit_errors = defaultdict(set)
    table.create_errors = defaultdict(set)
    parsed_data = {}

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
                field.input = field.iommi_namespace.input(_name='input')
                field.bind_from_instance()
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
        for cells in cells_iterator:
            if not isinstance(cells, EditCells):
                continue
            instance = cells.row
            form.instance = instance
            attrs_to_save = []
            for cell in cells.iter_editable_cells():
                path = cell.get_path()
                value = parsed_data[path]
                field = form.fields[cell.column.iommi_name()]
                field._iommi_path_override = path
                if cells.is_create_template or field.read_from_instance(field=field, instance=instance) != value:
                    field.write_to_instance(field=field, instance=instance, value=value)
                    if not field.extra.get('django_related_field', False):
                        attrs_to_save.append(field.attr)

            if instance.pk is not None and instance.pk < 0:
                instance.pk = None
            if instance.pk is None:
                attrs_to_save = None
            instance.save(update_fields=attrs_to_save)

    save(table.cells_for_rows(), table.edit_form)
    save(table.cells_for_rows_for_create(), table.create_form)

    if 'post_save' in table.extra:
        table.invoke_callback(table.extra.post_save)

    return HttpResponseRedirect(request.META['HTTP_REFERER'])


class EditTable(Table):
    # language=rst
    """
    Describe an editable table. Example:

    .. code-block:: python

        table = EditTable(
            auto__model=Album,
            columns__name__edit__include=True,
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

    class Meta:
        form_class = Form
        member_class = EditColumn
        outer__tag = 'form'
        outer__attrs__enctype = 'multipart/form-data'
        outer__attrs__method = 'post'
        cells_class = EditCells
        actions__submit = dict(
            call_target__attribute='primary',
            display_name=gettext_lazy('Save'),
            post_handler=edit_table__post_handler,
            template=lambda table, **_: 'iommi/blank.html' if table.parent_form is not None else None,
        )
        actions__csrf = Action(
            tag='div',
            children__csrf=Fragment(
                template=lambda **_: Template('{% csrf_token %}'),
            ),
            attrs__style__display='none',
        )
        actions__add_row = Action.button(
            display_name=gettext_lazy('Add row'),
            attrs__onclick='iommi_add_row(this); return false',
        )
        actions_below = True
        edit_form = EMPTY
        create_form = EMPTY

        attrs = {
            'data-next-virtual-pk': '-1',
        }

        # language=js
        assets__edit_table_js = Asset.js(
            mark_safe(
                '''
                    function iommi_add_row(element) {
                        function find_for_siblings(s) {
                            while (s) {
                                let t = s.querySelector('table');
                                if (t) {
                                    return t;
                                }
                                s = s.previousElementSibling;
                            }
                            return null;
                        }

                        let table = null;
                        while (element.tagName !== 'FORM') {
                            element = element.parentNode;
                            let s = find_for_siblings(element);
                            if (s) {
                                table = s;
                                break;
                            }
                        }
                        if (!table) {
                            console.error('iommi: failed to find table!');
                            return;
                        }

                        let virtual_pk = parseInt(table.getAttribute('data-next-virtual-pk'), 10);
                        virtual_pk -= 1;
                        virtual_pk = virtual_pk.toString();
                        table.setAttribute('data-next-virtual-pk', virtual_pk);

                        let tmp = document.createElement('table');
                        tmp.innerHTML = table.getAttribute('data-add-template').replaceAll('#sentinel#', virtual_pk);
                        let y = tmp.querySelector('tr');
                        y.setAttribute('data-pk', virtual_pk)
                        table.querySelector('tbody').appendChild(y);
                        if (y.querySelector('.select2_enhance')) {
                            iommi_init_all_select2();
                        }
                    }
                '''
            )
        )

    def on_refine_done(self):
        super(EditTable, self).on_refine_done()

        fields = Struct()

        for name, column in items(self.iommi_namespace.columns):
            if not isinstance(column, EditColumn):
                continue
            if getattr(column, 'include', None) is False:
                continue

            edit_conf = column.iommi_namespace.get('edit', None)

            if not edit_conf:
                continue
            if getattr(column.edit, 'include', None) is False:
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
                field = column.iommi_namespace.edit

            fields[name] = field

        auto = Namespace(self.auto)

        auto.pop('rows', None)
        if 'model' not in auto and 'rows' in auto:
            auto['model'] = auto.rows.model

        self.create_form = self.get_meta().form_class(
            **setdefaults_path(
                Namespace(),
                self.create_form,
                fields=fields,
                _name='create_form',
                auto=auto,
            )
        )

        if auto:
            auto.default_included = False

        self.edit_form = self.get_meta().form_class(
            **setdefaults_path(
                Namespace(),
                self.edit_form,
                fields=fields,
                _name='edit_form',
                auto=auto,
            )
        )

        declared_fields = self.edit_form.iommi_namespace.fields
        self.edit_form = self.edit_form.refine_defaults(fields=declared_fields).refine_done()
        self.create_form = self.create_form.refine_defaults(fields=declared_fields).refine_done()

    def on_bind(self) -> None:
        super(EditTable, self).on_bind()
        self.edit_form = self.edit_form.bind(parent=self)
        self._bound_members.edit_form = self.edit_form
        self.create_form = self.create_form.bind(parent=self)
        self._bound_members.create_form = self.create_form

        # If this is a nested form register it with the parent, need
        # to do this early because is_target needs self.parent_form
        if self.iommi_parent() is not None:
            self.parent_form = self.iommi_parent().iommi_evaluate_parameters().get('form', None)
            if self.parent_form is not None:
                self.parent_form.nested_forms[self._name] = self
                self.outer.tag = None

        if self.model is not None:
            sentinel_row = self.model(pk='#sentinel#')
        else:
            sentinel_row = Struct(pk='#sentinel#', **{k: '' for k in keys(self.create_form.fields)})
        self.attrs['data-add-template'] = (
            self.cells_class(row=sentinel_row, row_index=-1, is_create_template=True, **self.row.as_dict())
            .bind(parent=self.create_form)
            .__html__()
        )

    def is_valid(self):
        return not self.edit_errors and not self.create_errors

    def cells_for_rows_for_create(self):
        """Yield a Cells instance for each create row sent from the client."""
        assert self._is_bound, NOT_BOUND_MESSAGE

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

        pks = {parse_virtual_pk(k) for k in keys(self.get_request().POST)}

        virtual_pks = {k for k in pks if k is not None and k < 0}

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
