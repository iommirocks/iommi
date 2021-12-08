from collections import defaultdict
from typing import (
    Optional,
    Type,
)

from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.template import (
    Context,
    Template,
)
from django.utils.translation import gettext
from tri_declarative import (
    EMPTY,
    getattr_path,
    Namespace,
    Refinable,
    setdefaults_path,
)
from tri_struct import Struct

from iommi import (
    Action,
    Column,
    Field,
    Form,
    Fragment,
    MISSING,
    Table,
)
from iommi.base import (
    items,
    values,
)
from iommi.endpoint import path_join
from iommi.table import (
    Cell,
    Cells,
)


class EditCell(Cell):
    def get_path(self):
        return path_join(self.column.iommi_path, str(self.row.pk))

    def render_cell_contents(self):
        field = self.table.edit_form.fields.get(self.column.iommi_name(), None)
        if field:
            path = self.get_path()

            field.initial = MISSING
            field.raw_data = None
            field.value = None
            field.parsed_data = None
            field._errors = set()
            field.form.instance = self.row
            field._iommi_path_override = path
            del field.input.attrs['value']
            field.bind_from_instance()

            input_html = field.input.__html__()

            if self.table.edit_errors:
                errors = self.table.edit_errors.get(path)
                if errors:
                    return Template('{{ input_html }}<br><span class="text-danger"><ul class="errors">{% for error in errors %}<li>{{ error }}</li>{% endfor %}</ul></a>').render(context=Context(dict(input_html=input_html, errors=errors)))

            return input_html
        else:
            return super().render_cell_contents()


class EditCells(Cells):
    class Meta:
        cell_class = EditCell

    def iter_editable_cells(self):
        for column in values(self.iommi_parent().columns):
            if not column.render_column:
                continue

            field = self.iommi_parent().edit_form.fields.get(column.iommi_name(), None)
            if not field:
                continue
            yield self.cell_class(cells=self, column=column)


class EditColumn(Column):
    edit: Field = Refinable()

    def on_refine_done(self):
        super(EditColumn, self).on_refine_done()
        self.edit = None


def edit_table__post_handler(table, request, **_):
    # 1. Validate all the fields
    errors = defaultdict(set)
    parsed_data = {}
    for cells in table.cells_for_rows():
        instance = cells.row
        table.edit_form.instance = instance
        for cell in cells.iter_editable_cells():
            path = cell.get_path()
            field = table.edit_form.fields[cell.column.iommi_name()]
            try:
                parsed_data[path] = field.parse(
                    string_value=request.POST.get(path),
                    **field.iommi_evaluate_parameters(),
                )
            except ValidationError as e:
                errors[path] |= set(e.messages)
            except ValueError as e:
                errors[path] = {str(e)}
            except TypeError as e:
                errors[path] = {str(e)}

    if errors:
        table.edit_errors = errors
        return None

    for cells in table.cells_for_rows():
        instance = cells.row
        table.edit_form.instance = instance
        attrs_to_save = []
        for cell in cells.iter_editable_cells():
            path = cell.get_path()
            value = parsed_data[path]
            field = table.edit_form.fields[cell.column.iommi_name()]
            if getattr_path(instance, field.attr) != value:
                field.write_to_instance(field=field, instance=instance, value=value)
                attrs_to_save.append(field.attr)

        if instance.pk is not None and instance.pk < 0:
            instance.pk = None
        if instance.pk is None:
            attrs_to_save = None
        instance.save(update_fields=attrs_to_save)

    if 'post_save' in table.extra:
        table.extra.post_save(**table.iommi_evaluate_parameters())

    return HttpResponseRedirect(request.META['HTTP_REFERER'])


class EditTable(Table):
    edit_errors = None
    edit_form: Form = Refinable()
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
            display_name=gettext('Save'),
            post_handler=edit_table__post_handler,
        )
        actions__csrf = Action(tag='div', children__csrf=Fragment(template=Template('{% csrf_token %}')), attrs__style__display='none')
        actions_below = True
        edit_form = EMPTY

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
        if auto:
            auto.default_included = False

        if 'model' not in auto and 'rows' in auto:
            auto['model'] = auto.rows.model

        auto.pop('rows', None)

        self.edit_form = self.get_meta().form_class(**setdefaults_path(
            Namespace(),
            self.edit_form,
            fields=fields,
            _name='edit_form',
            auto=auto,
        ))

        declared_fields = self.edit_form.iommi_namespace.fields
        self.edit_form = self.edit_form.refine_defaults(fields=declared_fields).refine_done()

    def on_bind(self) -> None:
        super(EditTable, self).on_bind()
        self.edit_form = self.edit_form.bind(parent=self)
        self._bound_members.edit_form = self.edit_form

        # If this is a nested form register it with the parent, need
        # to do this early because is_target needs self.parent_form
        if self.iommi_parent() is not None:
            self.parent_form = self.iommi_parent().iommi_evaluate_parameters().get('form', None)
            if self.parent_form is not None:
                self.parent_form.nested_forms[self._name] = self
                self.outer.tag = None

    def is_valid(self):
        return self.edit_form.is_valid()

    @property
    def render_actions(self):
        # For now we do not support actions in child forms. This mirrors the behavior in Form
        if self.parent_form:
            return ''

        return super().render_actions
