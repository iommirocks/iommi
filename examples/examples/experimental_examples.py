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
        if self.column.editable:
            path = self.get_path()
            cell_contents = self.get_request().POST.get(path) or self.render_formatted()

            input_html = Fragment(
                **Namespace(
                    self.column.edit_input,
                    attrs__name=path,
                    attrs__value=cell_contents,
                    _name=str(self.row.pk),
                )
            ).bind(parent=self.cells).__html__()

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
            if not column.editable:
                continue
            yield self.cell_class(cells=self, column=column)


class FormsetColumn(Column):
    edit: Field = Refinable()


def formset_table__post_handler(table, request, **_):
    # 1. Validate all the fields
    errors = defaultdict(set)
    parsed_data = {}
    for cells in table.cells_for_rows():
        for cell in cells.iter_editable_cells():
            path = cell.get_path()
            try:
                parsed_data[path] = cell.column.field.parse(
                    string_value=request.POST.get(path),
                    **cell.iommi_evaluate_parameters(),
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
        for cell in cells.iter_editable_cells():
            path = cell.get_path()
            value = parsed_data[path]
            cell.column.field.write_to_instance(field=cell.column.field, instance=instance, value=value)
        instance.save()

    if 'post_save' in table.extra:
        table.extra.post_save(**table.iommi_evaluate_parameters())

    #   3.2 Redirect back to .
    return redirect('.')


class FormsetTable(Table):
    formset_errors = None
    form: Form = Refinable()
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

    def on_refine_done(self):
        super(FormsetTable, self).on_refine_done()

        fields = Struct()

        field_class = self.get_meta().form_class.get_meta().member_class

        for name, column in items(self.iommi_namespace.columns):
            if getattr(column, 'include', None) is False:
                continue
            if getattr(column.field, 'include', None) is False:
                continue
            field = setdefaults_path(
                Namespace(),
                column.field,
                call_target__cls=field_class,
                model=self.model,
                model_field_name=column.model_field_name,
                _name=name,
                attr=name if column.attr is MISSING else column.attr,
            )

            fields[name] = field()

        self.form = self.get_meta().form_class(**setdefaults_path(
            Namespace(),
            self.form,
            fields=fields,
            _name='form',
            model=self.model,
        ))

        declared_fields = self.form.iommi_namespace.fields
        self.form = self.form.refine_defaults(fields=declared_fields)


urlpatterns = [
    path(
        '',
        FormsetTable(
            auto__model=Album,
            fields__artist__editable=True,
        ).as_view(),
    ),
]
