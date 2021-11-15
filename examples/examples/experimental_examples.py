from collections import defaultdict
from typing import (
    Any,
    Type,
)

from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.template import (
    Context,
    Template,
)
from django.urls import path
from django.utils.translation import gettext
from tri_declarative import (
    EMPTY,
    Namespace,
    Refinable,
    refinable,
    setattr_path,
    setdefaults_path,
)
from tri_struct import Struct

from examples.models import (
    Album,
)
from iommi import (
    Action,
    Column,
    Fragment,
    Table,
)
from iommi.base import (
    items,
    MISSING,
    values,
)
from iommi.endpoint import path_join
from iommi.form import (
    Field,
    float_parse,
    Form,
)
from iommi.table import (
    Cell,
    Cells,
)


class FormsetCell(Cell):
    def get_path(self):
        return path_join(self.column.iommi_path, str(self.row.pk))

    def render_cell_contents(self):
        if self.column.edit:
            path = self.get_path()

            field = self.table.edit_form.fields[self.column.iommi_name()]
            field.initial = MISSING
            field.form.instance = self.row
            field.bind_instance(field=field)
            field.input.attrs.name += f'/{self.row.pk}'
            field.input.attrs.id += f'__{self.row.pk}'

            input_html = field.input.__html__()

            if self.table.formset_errors:
                errors = self.table.formset_errors.get(path)
                if errors:
                    return Template('{{ input_html }}<br><span class="text-danger"><ul class="errors">{% for error in errors %}<li>{{ error }}</li>{% endfor %}</ul></a>').render(context=Context(dict(input_html=input_html, errors=errors)))

            return input_html
        else:
            return super().render_cell_contents()


class FormsetCells(Cells):
    class Meta:
        cell_class = FormsetCell

    def iter_editable_cells(self):
        for column in values(self.iommi_parent().columns):
            if not column.render_column:
                continue
            if not column.edit:
                continue
            yield self.cell_class(cells=self, column=column)


class FormsetColumn(Column):
    edit: Field = Refinable()

    class Meta:
        edit = EMPTY


def formset_table__post_handler(table, request, **_):
    # 1. Validate all the fields
    errors = defaultdict(set)
    parsed_data = {}
    for cells in table.cells_for_rows():
        instance = cells.row
        table.edit_form.instance = instance
        for cell in cells.iter_editable_cells():
            path = table.edit_form.fields[cell.column.iommi_name()].iommi_path + '/' + str(instance.pk)
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

    # 2. If invalid
    #   2.1 render back with validation errors
    if errors:
        table.formset_errors = errors
        return None

    # 3. If valid
    #   3.1 Save all fields
    for cells in table.cells_for_rows():
        instance = cells.row
        table.edit_form.instance = instance
        for cell in cells.iter_editable_cells():
            path = table.edit_form.fields[cell.column.iommi_name()].iommi_path + '/' + str(instance.pk)
            value = parsed_data[path]
            field = table.edit_form.fields[cell.column.iommi_name()]
            field.write_to_instance(field=field, instance=instance, value=value)
        instance.save()

    if 'post_save' in table.extra:
        table.extra.post_save(**table.iommi_evaluate_parameters())

    #   3.2 Redirect back to .
    return redirect('.')


class FormsetTable(Table):
    formset_errors = None
    edit_form: Form = Refinable()
    form_class: Type[Form] = Refinable()

    class Meta:
        form_class = Form
        member_class = FormsetColumn
        outer__tag = 'form'
        outer__attrs__enctype = 'multipart/form-data'
        outer__attrs__method = 'post'
        cells_class = FormsetCells
        actions__submit = dict(
            call_target__attribute='primary',
            display_name=gettext('Save'),
            post_handler=formset_table__post_handler,
        )
        actions__csrf = Action(children__csrf=Fragment(template=Template('{% csrf_token %}')), attrs__style__display='none')
        actions_below = True
        edit_form = EMPTY

    def on_refine_done(self):
        super(FormsetTable, self).on_refine_done()

        fields = Struct()

        field_class = self.get_meta().form_class.get_meta().member_class

        for name, column in items(self.iommi_namespace.columns):
            if getattr(column, 'include', None) is False:
                continue
            if getattr(column.edit, 'include', None) is False:
                continue
            field = setdefaults_path(
                Namespace(),
                column.edit,
                call_target__cls=field_class,
                model=self.model,
                model_field_name=column.model_field_name,
                attr=name if column.attr is MISSING else column.attr,
            )

            fields[name] = field

        self.edit_form = self.get_meta().form_class(**setdefaults_path(
            Namespace(),
            self.edit_form,
            fields=fields,
            _name='edit_form',
            auto=self.auto,
        ))

        declared_fields = self.edit_form.iommi_namespace.fields
        self.edit_form = self.edit_form.refine_defaults(fields=declared_fields).refine_done()

    def on_bind(self) -> None:
        super(FormsetTable, self).on_bind()
        self.edit_form = self.edit_form.bind(parent=self)
        self._bound_members.edit_form = self.edit_form


urlpatterns = [
    path(
        '',
        FormsetTable(
            auto__model=Album,
            # columns__name__edit__include=True,
            columns__artist__edit__include=True,
        ).as_view(),
    ),
]
