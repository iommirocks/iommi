import csv
from datetime import datetime
from enum import (
    auto,
    Enum,
)
from functools import total_ordering
from io import StringIO
from itertools import groupby
from typing import (
    Any,
    Dict,
    Iterable,
    Optional,
    Type,
    Union,
)
from urllib.parse import quote_plus

from django.conf import settings
from django.core.paginator import (
    InvalidPage,
    Paginator as DjangoPaginator,
)
from django.db.models import (
    BooleanField,
    ManyToManyField,
    Model,
    QuerySet,
)
from django.http import (
    FileResponse,
    Http404,
    HttpResponseRedirect,
)
from django.utils.encoding import (
    force_str,
)
from django.utils.html import (
    conditional_escape,
    format_html,
)
from django.utils.safestring import mark_safe
from tri_declarative import (
    class_shortcut,
    declarative,
    dispatch,
    EMPTY,
    evaluate,
    evaluate_strict,
    getattr_path,
    LAST,
    Namespace,
    Refinable,
    refinable,
    RefinableObject,
    setdefaults_path,
    Shortcut,
    with_meta,
)
from tri_struct import (
    Struct,
)

from iommi._web_compat import (
    render_template,
    smart_text,
    Template,
)
from iommi.action import (
    Action,
    group_actions,
)
from iommi.base import (
    apply_style,
    bind_members,
    collect_members,
    DISPATCH_PREFIX,
    evaluate_attrs,
    evaluate_member,
    evaluate_strict_container,
    evaluated_refinable,
    EvaluatedRefinable,
    MISSING,
    model_and_rows,
    no_copy_on_bind,
    Part,
    path_join,
    Traversable,
    create_as_view_from_as_page,
    render_attrs,
)
from iommi.form import (
    Field,
    Form,
)
from iommi.from_model import (
    AutoConfig,
    create_members_from_model,
    get_fields,
    member_from_model,
)
from iommi.query import (
    Q_OPERATOR_BY_QUERY_OPERATOR,
    Query,
    QueryException,
)

LAST = LAST

_column_factory_by_field_type = {}


def register_column_factory(django_field_class, *, shortcut_name=MISSING, factory=MISSING):
    assert shortcut_name is not MISSING or factory is not MISSING
    if factory is MISSING:
        factory = Shortcut(call_target__attribute=shortcut_name)

    _column_factory_by_field_type[django_field_class] = factory


DESCENDING = 'descending'
ASCENDING = 'ascending'

DEFAULT_PAGE_SIZE = 40


def prepare_headers(table):
    request = table.get_request()
    if request is None:
        return

    for name, column in table.rendered_columns.items():
        if column.sortable:
            params = request.GET.copy()
            param_path = path_join(table.iommi_path, 'order')
            order = request.GET.get(param_path, None)
            start_sort_desc = column.sort_default_desc
            params[param_path] = name if not start_sort_desc else '-' + name
            column.is_sorting = False
            if order is not None:
                is_desc = order.startswith('-')
                order_field = order if not is_desc else order[1:]
                if order_field == name:
                    new_order = order_field if is_desc else ('-' + order_field)
                    params[param_path] = new_order
                    column.sort_direction = DESCENDING if is_desc else ASCENDING
                    column.is_sorting = True

            column.url = "?" + params.urlencode()
        else:
            column.is_sorting = False


@total_ordering
class MinType(object):
    def __le__(self, other):
        return True

    def __eq__(self, other):
        return self is other


MIN = MinType()


def order_by_on_list(objects, order_field, is_desc=False):
    """
    Utility function to sort objects django-style even for non-query set collections

    :param objects: list of objects to sort
    :param order_field: field name, follows django conventions, so `foo__bar` means `foo.bar`, can be a callable.
    :param is_desc: reverse the sorting
    :return:
    """
    if callable(order_field):
        objects.sort(key=order_field, reverse=is_desc)
        return

    def order_key(x):
        v = getattr_path(x, order_field)
        if v is None:
            return MIN
        return v

    objects.sort(key=order_key, reverse=is_desc)


def yes_no_formatter(value, **_):
    """ Handle True/False from Django model and 1/0 from raw sql """
    if value is None:
        return ''
    if value == 1:  # boolean True is equal to 1
        return 'Yes'
    if value == 0:  # boolean False is equal to 0
        return 'No'
    assert False, f"Unable to convert {value} to Yes/No"


def list_formatter(value, **_):
    return ', '.join([conditional_escape(x) for x in value])


_cell_formatters = {
    bool: yes_no_formatter,
    tuple: list_formatter,
    list: list_formatter,
    set: list_formatter,
    QuerySet: lambda value, **_: list_formatter(list(value))
}


def register_cell_formatter(type_or_class, formatter):
    """
    Register a default formatter for a type. A formatter is a function that takes four keyword arguments: table, column, row, value
    """
    global _cell_formatters
    _cell_formatters[type_or_class] = formatter


def default_cell_formatter(table: 'Table', column: 'Column', row, value, **_):
    formatter = _cell_formatters.get(type(value))
    if formatter:
        value = formatter(table=table, column=column, row=row, value=value)

    if value is None:
        return ''

    return conditional_escape(value)


SELECT_DISPLAY_NAME = '<i class="fa fa-check-square-o" onclick="iommi_table_js_select_all(this)"></i>'


class DataRetrievalMethods(Enum):
    attribute_access = auto()
    prefetch = auto()
    select = auto()


@with_meta
class Column(Part):
    """
    Class that describes a column, i.e. the text of the header, how to get and display the data in the cell, etc.

    See :doc:`Table` for more complete examples.

    """
    url: str = EvaluatedRefinable()
    attr: str = EvaluatedRefinable()
    sort_default_desc: bool = EvaluatedRefinable()
    sortable: bool = EvaluatedRefinable()
    group: Optional[str] = EvaluatedRefinable()
    auto_rowspan: bool = EvaluatedRefinable()
    cell: Namespace = Refinable()
    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    model_field = Refinable()
    choices: Iterable = EvaluatedRefinable()
    bulk: Namespace = Refinable()
    query: Namespace = Refinable()
    superheader = EvaluatedRefinable()
    header: Namespace = EvaluatedRefinable()
    data_retrieval_method = EvaluatedRefinable()
    render_column: bool = EvaluatedRefinable()

    @dispatch(
        attr=MISSING,
        sort_default_desc=False,
        sortable=True,
        auto_rowspan=False,
        bulk__include=False,
        query__include=False,
        query__form__include=False,
        data_retrieval_method=DataRetrievalMethods.attribute_access,
        cell__template=None,
        cell__attrs=EMPTY,
        cell__value=lambda column, row, **kwargs: getattr_path(row, evaluate_strict(column.attr, row=row, column=column, **kwargs)),
        cell__format=default_cell_formatter,
        cell__url=None,
        cell__url_title=None,
        cell__contents__attrs=EMPTY,
        header__attrs__class__sorted=lambda column, **_: column.is_sorting,
        header__attrs__class__descending=lambda column, **_: column.sort_direction == DESCENDING,
        header__attrs__class__ascending=lambda column, **_: column.sort_direction == ASCENDING,
        header__attrs__class__first_column=lambda header, **_: header.index_in_group == 0,
        header__attrs__class__subheader=True,
        header__template='iommi/table/header.html',
        render_column=True,
    )
    def __init__(self, **kwargs):
        """
        :param name: the name of the column
        :param attr: What attribute to use, defaults to same as name. Follows django conventions to access properties of properties, so `foo__bar` is equivalent to the python code `foo.bar`. This parameter is based on the variable name of the Column if you use the declarative style of creating tables.
        :param display_name: the text of the header for this column. By default this is based on the `name` parameter so normally you won't need to specify it.
        :param url: URL of the header. This should only be used if sorting is off.
        :param include: set this to `False` to hide the column
        :param sortable: set this to `False` to disable sorting on this column
        :param sort_key: string denoting what value to use as sort key when this column is selected for sorting. (Or callable when rendering a table from list.)
        :param sort_default_desc: Set to `True` to make table sort link to sort descending first.
        :param group: string describing the group of the header. If this parameter is used the header of the table now has two rows. Consecutive identical groups on the first level of the header are joined in a nice way.
        :param auto_rowspan: enable automatic rowspan for this column. To join two cells with rowspan, just set this `auto_rowspan` to `True` and make those two cells output the same text and we'll handle the rest.
        :param cell__template: name of a template file, or `Template` instance. Gets arguments: `table`, `column`, `bound_row`, `row` and `value`. Your own arguments should be sent in the 'extra' parameter.
        :param cell__value: string or callable that receives kw arguments: `table`, `column` and `row`. This is used to extract which data to display from the object.
        :param cell__format: string or callable that receives kw arguments: `table`, `column`, `row` and `value`. This is used to convert the extracted data to html output (use `mark_safe`) or a string.
        :param cell__attrs: dict of attr name to callables that receive kw arguments: `table`, `column`, `row` and `value`.
        :param cell__url: callable that receives kw arguments: `table`, `column`, `row` and `value`.
        :param cell__url_title: callable that receives kw arguments: `table`, `column`, `row` and `value`.
        :param render_column: If set to `False` the column won't be rendered in the table, but still be available in `table.columns`. This can be useful if you want some other feature from a column like filtering.
        """

        super(Column, self).__init__(**kwargs)

        self.is_sorting: bool = None
        self.sort_direction: str = None
        self.table = None

    @staticmethod
    @evaluated_refinable
    def sort_key(table, column, **_):
        return column.attr

    @staticmethod
    @evaluated_refinable
    def display_name(table, column, **_):
        return force_str(column._name).rsplit('__', 1)[-1].replace("_", " ").capitalize()

    def on_bind(self) -> None:

        self.table = self._parent._parent

        # TODO: why don't we do this centrally?
        if self.attr is MISSING:
            self.attr = self._name

        self.bulk = setdefaults_path(
            Struct(),
            self.bulk,
            attr=self.attr,
        )
        self.query = setdefaults_path(
            Struct(),
            self.query,
            attr=self.attr,
        )
        self.declared_column = self._declared

        # Not strict evaluate on purpose
        self.model = evaluate(self.model, **self.evaluate_parameters)

    def own_evaluate_parameters(self):
        return dict(table=self._parent._parent, column=self)

    @classmethod
    @dispatch(
        query__call_target__attribute='from_model',
        bulk__call_target__attribute='from_model',
    )
    def from_model(cls, model, field_name=None, model_field=None, **kwargs):
        return member_from_model(
            cls=cls,
            model=model,
            factory_lookup=_column_factory_by_field_type,
            factory_lookup_register_function=register_column_factory,
            field_name=field_name,
            model_field=model_field,
            defaults_factory=lambda model_field: {},
            **kwargs)

    @classmethod
    @class_shortcut(
        display_name='',
        sortable=False,
        # TODO: remove this class and similar in the codebase
        header__attrs__class__thin=True,
        cell__value=lambda table, **_: True,
        extra__icon_attrs__class=EMPTY,
    )
    def icon(cls, *args, include=True, call_target=None, **kwargs):
        """
        Shortcut to create font awesome-style icons.

        :param extra__icon: the font awesome name of the icon
        """
        assert len(args) in (0, 1), "You can only pass 1 positional argument: icon, or you can pass no arguments."

        if args:
            setdefaults_path(kwargs, dict(extra__icon=args[0]))

        def icon_format(column, value, **_):
            if not value or not column.extra.get('icon', None):
                return column.display_name

            attrs = column.extra.icon_attrs
            attrs['class'][column.extra.icon_prefix + column.extra.icon] = True

            return format_html('<i{}></i> {}', render_attrs(attrs), column.display_name)

        setdefaults_path(kwargs, dict(
            # TODO: what?
            include=lambda table, **rest: evaluate_strict(include, table=table, **rest),
            cell__format=icon_format,
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='icon',
        cell__url=lambda row, **_: row.get_absolute_url() + 'edit/',
        display_name='Edit'
    )
    def edit(cls, call_target=None, **kwargs):
        """
        Shortcut for creating a clickable edit icon. The URL defaults to `your_object.get_absolute_url() + 'edit/'`. Specify the option cell__url to override.
        """
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='icon',
        cell__url=lambda row, **_: row.get_absolute_url() + 'delete/',
        display_name='Delete'
    )
    def delete(cls, call_target=None, **kwargs):
        """
        Shortcut for creating a clickable delete icon. The URL defaults to `your_object.get_absolute_url() + 'delete/'`. Specify the option cell__url to override.
        """
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='icon',
        cell__url=lambda row, **_: row.get_absolute_url() + 'download/',
        cell__value=lambda row, **_: getattr(row, 'pk', False),
        display_name='Download'
    )
    def download(cls, call_target=None, **kwargs):
        """
        Shortcut for creating a clickable download icon. The URL defaults to `your_object.get_absolute_url() + 'download/'`. Specify the option cell__url to override.
        """
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='icon',
        cell__url=lambda row, **_: row.get_absolute_url() + 'run/',
        display_name='Run',
    )
    def run(cls, call_target=None, **kwargs):
        """
        Shortcut for creating a clickable run icon. The URL defaults to `your_object.get_absolute_url() + 'run/'`. Specify the option cell__url to override.
        """
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        display_name=mark_safe(SELECT_DISPLAY_NAME),
        sortable=False,
    )
    def select(cls, checkbox_name='pk', include=True, checked=lambda row, **_: False, call_target=None, **kwargs):
        """
        Shortcut for a column of checkboxes to select rows. This is useful for implementing bulk operations.

        :param checkbox_name: the name of the checkbox. Default is `"pk"`, resulting in checkboxes like `"pk_1234"`.
        :param checked: callable to specify if the checkbox should be checked initially. Defaults to `False`.
        """
        setdefaults_path(kwargs, dict(
            include=lambda table, **rest: evaluate_strict(include, table=table, **rest),
            cell__value=lambda row, **kwargs: mark_safe('<input type="checkbox"%s class="checkbox" name="%s_%s" />' % (' checked' if evaluate_strict(checked, row=row, **kwargs) else '', checkbox_name, row.pk)),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        query__call_target__attribute='boolean',
        bulk__call_target__attribute='boolean',
    )
    def boolean(cls, call_target=None, **kwargs):
        """
        Shortcut to render booleans as a check mark if true or blank if false.
        """

        def render_icon(value):
            # TODO: fugly evaluate
            if callable(value):
                value = value()
            return mark_safe('<i class="fa fa-check" title="Yes"></i>') if value else ''

        setdefaults_path(kwargs, dict(
            cell__format=lambda value, **rest: render_icon(value),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='boolean',
        query__call_target__attribute='boolean_tristate',
    )
    def boolean_tristate(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        bulk__call_target__attribute='choice',
        query__call_target__attribute='choice',
    )
    def choice(cls, call_target=None, **kwargs):
        choices = kwargs['choices']
        setdefaults_path(kwargs, dict(
            bulk__choices=choices,
            query__choices=choices,
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice',
        bulk__call_target__attribute='choice_queryset',
        query__call_target__attribute='choice_queryset',
    )
    def choice_queryset(cls, call_target=None, **kwargs):
        setdefaults_path(kwargs, dict(
            bulk__model=kwargs.get('model'),
            query__model=kwargs.get('model'),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice_queryset',
        bulk__call_target__attribute='multi_choice_queryset',
        query__call_target__attribute='multi_choice_queryset',
    )
    def multi_choice_queryset(cls, call_target, **kwargs):
        setdefaults_path(kwargs, dict(
            bulk__model=kwargs.get('model'),
            query__model=kwargs.get('model'),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice',
        bulk__call_target__attribute='multi_choice',
        query__call_target__attribute='multi_choice',
    )
    def multi_choice(cls, call_target, **kwargs):
        setdefaults_path(kwargs, dict(
            bulk__model=kwargs.get('model'),
            query__model=kwargs.get('model'),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        bulk__call_target__attribute='text',
        query__call_target__attribute='text',
    )
    def text(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut
    def link(cls, call_target, **kwargs):
        # TODO: this can be simplified
        # Shortcut for creating a cell that is a link. The URL is the result of calling `get_absolute_url()` on the object.
        def link_cell_url(table, column, row, value):
            del table, value
            r = getattr_path(row, column.attr)
            return r.get_absolute_url() if r else ''

        setdefaults_path(kwargs, dict(
            cell__url=link_cell_url,
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut
    def number(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='number',
        query__call_target__attribute='float',
        bulk__call_target__attribute='float',
    )
    def float(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='number',
        query__call_target__attribute='integer',
        bulk__call_target__attribute='integer',
    )
    def integer(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        query__query_operator_for_form=':',
    )
    def substring(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        query__call_target__attribute='date',
        query__query_operator_to_q_operator=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OPERATOR_BY_QUERY_OPERATOR[op],
        bulk__call_target__attribute='date',
    )
    def date(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        query__call_target__attribute='datetime',
        query__query_operator_to_q_operator=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OPERATOR_BY_QUERY_OPERATOR[op],
        bulk__call_target__attribute='datetime',
    )
    def datetime(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        query__call_target__attribute='time',
        query__query_operator_to_q_operator=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OPERATOR_BY_QUERY_OPERATOR[op],
        bulk__call_target__attribute='time',
    )
    def time(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        query__call_target__attribute='email',
        bulk__call_target__attribute='email',
    )
    def email(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        bulk__call_target__attribute='decimal',
        query__call_target__attribute='decimal',
    )
    def decimal(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='multi_choice_queryset',
        bulk__call_target__attribute='many_to_many',
        query__call_target__attribute='many_to_many',
        cell__format=lambda value, **_: ', '.join(['%s' % x for x in value.all()]),
        data_retrieval_method=DataRetrievalMethods.prefetch,
        sortable=False,
        extra__django_related_field=True,
    )
    def many_to_many(cls, call_target, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.remote_field.model.objects.all(),
            model_field=model_field.remote_field,
        )
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice_queryset',
        bulk__call_target__attribute='foreign_key',
        query__call_target__attribute='foreign_key',
        data_retrieval_method=DataRetrievalMethods.select,
    )
    def foreign_key(cls, call_target, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.foreign_related_fields[0].model.objects.all(),
            model_field=model_field.foreign_related_fields[0].model,
        )
        return call_target(**kwargs)


# TODO: why isn't this Part?
class BoundRow(object):
    """
    Internal class used in row rendering
    """

    def __init__(self, table, row, row_index):
        self.table: Table = table
        self.row: Any = row
        assert not isinstance(self.row, BoundRow)
        self.row_index = row_index
        self._parent = table
        self._name = 'row'
        self.template = evaluate(table.row.template, row=self.row, **table.evaluate_parameters)
        self.extra = table.row.extra
        self.extra_evaluated = evaluate_strict_container(table.row.extra_evaluated, row=self.row, **table.evaluate_parameters)
        self.attrs = table.row.attrs
        self.attrs = evaluate_attrs(self, table=table, row=row, bound_row=self)

    def __html__(self):
        if self.template:
            context = dict(bound_row=self, row=self.row, **self.table.context)
            return render_template(self.table.get_request(), self.template, context)

        return format_html('<tr{}>{}</tr>', self.attrs, self.render_cells())

    def render_cells(self):
        return mark_safe('\n'.join(bound_cell.__html__() for bound_cell in self))

    def __iter__(self):
        for column in self.table.rendered_columns.values():
            yield BoundCell(bound_row=self, column=column)

    def __getitem__(self, name):
        column = self.table.rendered_columns[name]
        return BoundCell(bound_row=self, column=column)

    @property
    def iommi_dunder_path(self):
        return path_join(self._parent.iommi_dunder_path, 'row', separator='__')


# TODO: make this a Part?
class BoundCell(object):

    def __init__(self, bound_row, column):
        assert column.include
        # TODO: is this really right?
        self._name = 'cell'

        self.column = column
        self.bound_row = bound_row
        self.table = bound_row.table
        self.row = bound_row.row

        # TODO: clean up these evaluates.. why are the kwargs so different?
        self.value = evaluate_strict(
            self.column.cell.value,
            table=self.bound_row.table,
            declared_column=self.column.declared_column,
            row=self.bound_row.row,
            bound_row=self.bound_row,
            column=self.column,
        )
        self.url = evaluate_strict(
            self.column.cell.url,
            table=self.table,
            column=self.column,
            row=self.row,
            value=self.value,
        )
        self.attrs = self.column.cell.attrs
        self.attrs = evaluate_attrs(
            self,
            table=self.table,
            column=self.column,
            row=self.row,
            value=self.value,
        )
        self.url_title = evaluate_strict(
            self.column.cell.url_title,
            table=self.table,
            column=self.column,
            row=self.row,
            value=self.value,
        )

    @property
    def iommi_dunder_path(self):
        return path_join(self.column.iommi_dunder_path, 'cell', separator='__')

    def __html__(self):
        cell__template = self.column.cell.template
        if cell__template:
            context = dict(table=self.table, column=self.column, bound_row=self.bound_row, row=self.row, value=self.value, bound_cell=self)
            return render_template(self.table.get_request(), cell__template, context)

        return format_html('<td{}>{}</td>', self.attrs, self.render_cell_contents())

    def render_cell_contents(self):
        cell_contents = self.render_formatted()

        url = self.url
        if url:
            url_title = self.url_title
            # TODO: we should be able to set attrs here and style
            cell_contents = format_html('<a{}{}>{}</a>',
                                        format_html(' href="{}"', url),
                                        format_html(' title="{}"', url_title) if url_title else '',
                                        cell_contents)
        return cell_contents

    def render_formatted(self):
        return evaluate_strict(self.column.cell.format, table=self.table, column=self.column, row=self.row, value=self.value)

    def __str__(self):
        return self.__html__()

    def __repr__(self):
        return f"<{type(self).__name__} column={self.column.declared_column} row={self.bound_row.row}>"  # pragma: no cover


class TemplateConfig(RefinableObject):
    template: str = Refinable()


class HeaderConfig(Traversable):
    attrs: Dict[str, Any] = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = Refinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[str, Any] = Refinable()

    def __html__(self):
        return render_template(self.get_request(), self.template, self._parent.context)

    def __str__(self):
        return self.__html__()


class RowConfig(RefinableObject):
    attrs: Dict[str, Any] = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = Refinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[str, Any] = Refinable()


# TODO: make this a Part?
class Header(object):
    @dispatch(
    )
    def __init__(self, *, display_name, attrs, template, table, url=None, column=None, number_of_columns_in_group=None, index_in_group=None):
        self.table = table
        self.display_name = mark_safe(display_name)
        self.template = template
        self.url = url
        self.column = column
        self.number_of_columns_in_group = number_of_columns_in_group
        self.index_in_group = index_in_group
        self.attrs = attrs
        self._name = 'header'
        self.attrs = evaluate_attrs(self, table=table, column=column, header=self)

    @property
    def rendered(self):
        return render_template(self.table.get_request(), self.template, dict(header=self))

    def __repr__(self):
        return '<Header: %s>' % ('superheader' if self.column is None else self.column._name)

    @property
    def iommi_dunder_path(self):
        if self.column is None:
            return None
        return path_join(self.column.iommi_dunder_path, self._name, separator='__')


def bulk__post_handler(table, form, **_):
    if not form.is_valid():
        return

    queryset = table.bulk_queryset()

    simple_updates = []
    m2m_updates = []
    for field in form.fields.values():
        if field.value is None:
            continue
        if field.value in ['', []]:
            continue
        if field.attr is None:
            continue

        if isinstance(field.model_field, ManyToManyField):
            m2m_updates.append(field)
        else:
            simple_updates.append(field)

    updates = {
        field.attr: field.value
        for field in simple_updates
    }
    queryset.update(**updates)

    if m2m_updates:
        for obj in queryset:
            for field in m2m_updates:
                assert '__' not in field.attr, "Nested m2m relations is currently not supported for bulk editing"
                getattr(obj, field.attr).set(field.value)
            obj.save()

    table.post_bulk_edit(table=table, queryset=queryset, updates=updates)

    return HttpResponseRedirect(form.get_request().META['HTTP_REFERER'])


def bulk_delete__post_handler(table, form, **_):
    if not form.is_valid():
        return

    queryset = table.bulk_queryset()

    from iommi.page import Page, html

    class ConfirmPage(Page):
        title = html.h1(f'Are you sure you want to delete these {queryset.count()} items?')
        confirm = Table(
            auto__rows=queryset,
            columns__select=dict(
                include=True,
                checked=True,
                bulk__include=True,
                bulk__attrs__style__display='none',
            ),
            bulk=dict(
                fields__confirmed=Field.hidden(initial='confirmed'),
                actions__submit__include=False,
                actions__delete=dict(
                    call_target__attribute='delete',
                    attrs__value='Yes, delete all!',
                    include=True,
                ),
            ),
        )

    request = form.get_request()
    # We need to remove the target for the old delete button that we pressed to get here,
    # otherwise ConfirmPage will give an error saying it can't find that button
    request.POST = request.POST.copy()
    del request.POST[form.actions.delete.own_target_marker()]

    p = ConfirmPage().bind(request=request)

    if request.POST.get(p.parts.confirm.bulk_form.fields.confirmed.iommi_path) == 'confirmed':
        queryset.delete()
        return HttpResponseRedirect(form.get_request().META['HTTP_REFERER'])

    return p.render_to_response()


# TODO: full Part?
class Paginator:
    def __init__(self, *, django_paginator, table, adjacent_pages=6):
        self.iommi_style = None
        self._parent = table
        self.paginator = django_paginator
        self.table: Table = table
        self.adjacent_pages = adjacent_pages

        request = self.table.get_request()
        self.page_param_path = path_join(self.table.iommi_path, 'page')
        page = request.GET.get(self.page_param_path) if request else None
        self.current_page = int(page) if page else 1
        self.attrs = Namespace()
        self.container = Namespace(attrs=EMPTY)
        self.page = Namespace(attrs=EMPTY)
        self.active_item = Namespace(attrs=EMPTY)
        self.item = Namespace(attrs=EMPTY)
        self.link = Namespace(attrs=EMPTY)
        self.template = None

        apply_style(self)
        self.attrs = evaluate_attrs(self)
        self.container.attrs = evaluate_attrs(self.container)
        self.page.attrs = evaluate_attrs(self.page)
        self.active_item.attrs = evaluate_attrs(self.active_item)
        self.item.attrs = evaluate_attrs(self.item)
        self.link.attrs = evaluate_attrs(self.link)

    def get_paginated_rows(self):
        if self.paginator is None:
            return self.table.rows

        return self.paginator.get_page(self.current_page).object_list

    def __html__(self):
        if self.paginator is None:
            return ''

        request = self.table.get_request()

        assert self.current_page != 0  # pages are 1-indexed!
        num_pages = self.paginator.num_pages
        foo = self.current_page
        if foo <= self.adjacent_pages:
            foo = self.adjacent_pages + 1
        elif foo > num_pages - self.adjacent_pages:
            foo = num_pages - self.adjacent_pages
        page_numbers = [
            n for n in
            range(self.current_page - self.adjacent_pages, foo + self.adjacent_pages + 1)
            if 0 < n <= num_pages
        ]

        get = request.GET.copy() if request is not None else {}

        if self.page_param_path in get:
            del get[self.page_param_path]

        context = dict(
            extra=get and (get.urlencode() + "&") or "",
            page_numbers=page_numbers,
            show_first=1 not in page_numbers,
            show_last=num_pages not in page_numbers,
        )

        page_obj = self.paginator.get_page(self.current_page)

        if self.paginator.num_pages > 1:
            context.update({
                'page_param_path': self.page_param_path,
                'is_paginated': self.paginator.num_pages > 1,
                'results_per_page': self.table.page_size,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next': page_obj.next_page_number() if page_obj.has_next() else None,
                'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'page': page_obj.number,
                'pages': self.paginator.num_pages,
                'hits': self.paginator.count,
                'paginator': self,
            })
        else:
            return ''

        return render_template(
            request=self.table.get_request(),
            template=self.template,
            context=context,
        )

    def __str__(self):
        return self.__html__()


class TableAutoConfig(AutoConfig):
    rows = Refinable()


def endpoint__csv(table, **_):
    columns = [c for c in table.columns.values() if c.extra_evaluated.get('report_name')]
    csv_safe_column_indexes = {i for i, c in enumerate(table.columns.values()) if 'csv_whitelist' in c.extra}
    assert columns, 'To get CSV output you must specify at least one column with extra_evaluated__report_name'
    assert 'report_name' in table.extra_evaluated, 'To get CSV output you must specify extra_evaluated__report_name on the table'
    filename = table.extra_evaluated.report_name + '.csv'

    header = [c.extra_evaluated.report_name for c in columns]

    def smart_text2(s):
        if s is None:
            return ''
        elif isinstance(s, float):
            result = ('%f' % s).strip('0')
            if result[-1] == '.':
                result += '0'
            return result
        else:
            assert not isinstance(s, bytes)
            return str(s).strip()

    def safe_csv_value(value):
        # CSV formula injection protection: http://georgemauer.net/2017/10/07/csv-injection.html
        if value and value[0] in ('+', '-', '@', '='):
            return '\t' + value
        else:
            return value

    def cell_value(bound_row, bound_column):
        value = BoundCell(bound_row, bound_column).value
        return bound_column.extra_evaluated.get('report_value', value)

    def rows():
        for bound_row in table.bound_rows():
            yield [cell_value(bound_row, bound_column) for bound_column in columns]

    def write_csv_row(writer, row):
        row_strings = [smart_text2(value) for value in row]
        safe_row = [
            v if i in csv_safe_column_indexes else safe_csv_value(v)
            for i, v in enumerate(row_strings)
        ]
        writer.writerow(safe_row)

    f = StringIO()
    writer = csv.writer(f)
    writer.writerow(header)
    for row in rows():
        write_csv_row(writer, row)

    response = FileResponse(f.getvalue(), 'text/csv')

    # RFC 2183, RFC 2184
    response['Content-Disposition'] = smart_text("attachment; filename*=UTF-8''{value}".format(value=quote_plus(filename)))
    response['Last-Modified'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response


@no_copy_on_bind
@declarative(Column, '_columns_dict')
@with_meta
class Table(Part):
    """
    Describe a table. Example:

    .. code:: python

        class FooTable(Table):
            a = Column()
            b = Column()

            class Meta:
                sortable = False
                attrs__style = 'background: green'

    """
    # TODO: seems like a bunch more of these fields should be EvaluatedRefinable

    bulk_filter: Namespace = EvaluatedRefinable()
    bulk_exclude: Namespace = EvaluatedRefinable()
    sortable: bool = EvaluatedRefinable()
    query_from_indexes: bool = Refinable()
    default_sort_order = Refinable()
    attrs: Dict[str, Any] = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = Refinable()
    row = EvaluatedRefinable()
    header = Refinable()
    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    rows = Refinable()
    columns = Refinable()
    bulk: Namespace = EvaluatedRefinable()
    superheader: Namespace = Refinable()
    paginator: Paginator = Refinable()
    page_size: int = Refinable()
    actions_template: Union[str, Template] = Refinable()
    member_class = Refinable()
    form_class: Type[Form] = Refinable()
    query_class: Type[Query] = Refinable()
    action_class: Type[Action] = Refinable()

    class Meta:
        member_class = Column
        form_class = Form
        query_class = Query
        action_class = Action
        endpoints__tbody__func = (lambda table, **_: {'html': table.__html__(template='tri_table/table_container.html')})
        endpoints__csv__func = endpoint__csv

        attrs = {'data-endpoint': lambda table, **_: DISPATCH_PREFIX + path_join(table.iommi_path, 'tbody')}

    @staticmethod
    @refinable
    def preprocess_rows(rows, **_):
        return rows

    @staticmethod
    @refinable
    def preprocess_row(table, row, **_):
        del table
        return row

    @staticmethod
    @refinable
    def post_bulk_edit(table, queryset, updates):
        pass

    @dispatch(
        columns=EMPTY,
        bulk_filter={},
        bulk_exclude={},
        sortable=True,
        default_sort_order=None,
        template='iommi/table/table.html',
        row__attrs__class=EMPTY,
        row__attrs={'data-pk': lambda row, **_: getattr(row, 'pk', None)},
        row__template=None,
        row__extra=EMPTY,
        row__extra_evaluated=EMPTY,
        header__template='iommi/table/table_header_rows.html',
        paginator__call_target=Paginator,

        actions=EMPTY,
        actions_template='iommi/form/actions.html',
        query=EMPTY,
        bulk__fields=EMPTY,
        page_size=DEFAULT_PAGE_SIZE,

        endpoints=EMPTY,

        superheader__attrs__class__superheader=True,
        superheader__template='iommi/table/header.html',

        auto=EMPTY,
    )
    def __init__(self, *, columns: Namespace = None, _columns_dict=None, model=None, rows=None, bulk=None, header=None, query=None, row=None, actions: Namespace = None, auto, **kwargs):
        """
        :param rows: a list or QuerySet of objects
        :param columns: (use this only when not using the declarative style) a list of Column objects
        :param attrs: dict of strings to string/callable of HTML attributes to apply to the table
        :param row__attrs: dict of strings to string/callable of HTML attributes to apply to the row. Callables are passed the row as argument.
        :param row__template: name of template (or `Template` object) to use for rendering the row
        :param bulk_filter: filters to apply to the `QuerySet` before performing the bulk operation
        :param bulk_exclude: exclude filters to apply to the `QuerySet` before performing the bulk operation
        :param sortable: set this to `False` to turn off sorting for all columns
        """
        select_config = setdefaults_path(
            Namespace(),
            columns.get('select', {}),
            call_target__attribute='select',
            attr=None,
            _name='select',
            after=-1,
            include=lambda table, **_: table.bulk_form is not None,
        )

        select_column = select_config

        if auto:
            auto = TableAutoConfig(**auto)
            assert not _columns_dict, "You can't have an auto generated Table AND a declarative Table at the same time"
            assert not model, "You can't use the auto feature and explicitly pass model. Either pass auto__model, or we will set the model for you from auto__rows"
            assert not rows, "You can't use the auto feature and explicitly pass rows. Either pass auto__rows, or we will set rows for you from auto__model (.objects.all())"
            if 'select' not in auto.additional:
                auto.additional['select'] = select_column

            model, rows, columns = self._from_model(
                model=auto.model,
                rows=auto.rows,
                columns=columns,
                include=auto.include,
                exclude=auto.exclude,
                additional=auto.additional,
            )

        assert isinstance(columns, dict)

        model, rows = model_and_rows(model, rows)

        self.columns = None
        self.rendered_columns = None

        super(Table, self).__init__(
            model=model,
            rows=rows,
            header=HeaderConfig(**header),
            row=RowConfig(**row),
            bulk=bulk,
            **kwargs
        )

        collect_members(self, name='actions', items=actions, cls=self.get_meta().action_class)
        collect_members(self, name='columns', items=columns, items_dict=_columns_dict, cls=self.get_meta().member_class)

        self.query_args = query
        self.query: Query = None

        self.bulk_form: Form = None
        self.header_levels = None
        self.is_paginated = False

        if self.model:
            # Query
            def generate_variables():
                for name, column in self.declared_members.columns.items():
                    query_namespace = setdefaults_path(
                        Namespace(),
                        column.query,
                        call_target__cls=self.get_meta().query_class.get_meta().member_class,
                        model=self.model,
                        _name=name,
                        attr=name if column.attr is MISSING else column.attr,
                        form__call_target__cls=self.get_meta().query_class.get_meta().form_class.get_meta().member_class,
                    )
                    if 'call_target' not in query_namespace['call_target'] and query_namespace['call_target'].get(
                            'attribute') == 'from_model':
                        query_namespace['field_name'] = query_namespace.attr
                    # Special case for automatic query config
                    if self.query_from_indexes and column.model_field and getattr(column.model_field, 'db_index', False):
                        query_namespace.include = True
                        query_namespace.form.include = True
                    yield query_namespace()

            declared_variables = Struct({x._name: x for x in generate_variables()})

            self.query = self.get_meta().query_class(
                _variables_dict=declared_variables,
                _name='query',
                **self.query_args
            )
            self.declared_members.query = self.query

            # Bulk
            def generate_bulk_fields():
                field_class = self.get_meta().form_class.get_meta().member_class

                for name, column in self.declared_members.columns.items():
                    bulk_config = self.bulk.fields.pop(name, {})

                    if column.bulk.include:
                        bulk_namespace = setdefaults_path(
                            Namespace(),
                            column.bulk,
                            call_target__cls=field_class,
                            model=self.model,
                            _name=name,
                            attr=name if column.attr is MISSING else column.attr,
                            required=False,
                            empty_choice_tuple=(None, '', '---', True),
                            parse_empty_string_as_none=True,
                            **bulk_config
                        )
                        if isinstance(column.model_field, BooleanField):
                            bulk_namespace.call_target.attribute = 'boolean_tristate'
                        if 'call_target' not in bulk_namespace['call_target'] and bulk_namespace['call_target'].get('attribute') == 'from_model':
                            bulk_namespace['field_name'] = bulk_namespace.attr
                        yield bulk_namespace()

            declared_bulk_fields = Struct({x._name: x for x in generate_bulk_fields()})

            if declared_bulk_fields:
                form_class = self.get_meta().form_class
                declared_bulk_fields._all_pks_ = form_class.get_meta().member_class.hidden(
                    _name='_all_pks_',
                    attr=None,
                    initial='0',
                    required=False,
                    input__attrs__class__all_pks=True,
                )

                self.bulk_form = form_class(
                    _fields_dict=declared_bulk_fields,
                    _name='bulk',
                    actions__submit=dict(
                        post_handler=bulk__post_handler,
                        attrs__value='Bulk change',
                    ),
                    actions__delete=dict(
                        call_target__attribute='delete',
                        post_handler=bulk_delete__post_handler,
                        attrs__value='Bulk delete',
                        include=False,
                    ),
                    **bulk
                )

                self.declared_members.bulk = self.bulk_form

        # Columns need to be at the end to not steal the short names
        self.declared_members.columns = self.declared_members.pop('columns')

    def on_bind(self) -> None:
        bind_members(self, name='actions')
        bind_members(self, name='columns')
        bind_members(self, name='endpoints')

        self.header = self.header.bind(parent=self)

        evaluate_member(self, 'sortable', **self.evaluate_parameters)  # needs to be done first because _prepare_headers depends on it
        self._prepare_sorting()

        evaluate_member(self, 'model', strict=False, **self.evaluate_parameters)

        for column in self.columns.values():
            # Special case for entire table not sortable
            if not self.sortable:
                column.sortable = False

        self.rendered_columns = Struct({name: column for name, column in self.columns.items() if column.render_column})

        self._prepare_headers()

        if self.model:
            def generate_variables_unapplied_config():
                for name, column in self.columns.items():
                    query_namespace = setdefaults_path(
                        Namespace(),
                        _name=name,
                        form__display_name=column.display_name,
                    )
                    yield name, query_namespace


            self.query.unapplied_config.variables = Struct(generate_variables_unapplied_config())
            self.query.bind(parent=self)
            self.bound_members.query = self.query

            # TODO: why isn't this done inside Query?
            if self.query.form:
                try:
                    q = self.query.get_q()
                    if q:
                        self.rows = self.rows.filter(q)
                except QueryException as e:
                    self.query.extra.iommi_query_error = str(e)

            def generate_bulk_fields_unapplied_config():
                for name, column in self.columns.items():
                    bulk_namespace = setdefaults_path(
                        Namespace(),
                        column.bulk,
                        _name=name,
                        include=column.bulk.include,
                        display_name=column.display_name,
                    )
                    yield name, bulk_namespace

            if self.bulk_form is not None:
                self.bulk_form.unapplied_config.fields = Struct(generate_bulk_fields_unapplied_config())
                self.bulk_form.bind(parent=self)
                self.bound_members.bulk = self.bulk_form

        if isinstance(self.rows, QuerySet):
            prefetch = [x.attr for x in self.columns.values() if x.data_retrieval_method == DataRetrievalMethods.prefetch and x.attr]
            select = [x.attr for x in self.columns.values() if x.data_retrieval_method == DataRetrievalMethods.select and x.attr]
            if prefetch:
                self.rows = self.rows.prefetch_related(*prefetch)
            if select:
                self.rows = self.rows.select_related(*select)

        request = self.get_request()
        # TODO: I paginate only when I have a request... this is a bit weird, but matches old behavior and the tests assume this for now
        if self.page_size and request and isinstance(self.rows, QuerySet) and self.paginator is not None:
            try:
                self.page_size = int(request.GET.get('page_size', self.page_size)) if request else self.page_size
            except ValueError:
                pass

            if isinstance(self.paginator.call_target, type) and issubclass(self.paginator.call_target, DjangoPaginator):
                django_paginator = self.paginator(self.rows, self.page_size)
            elif isinstance(self.paginator.call_target, DjangoPaginator):
                django_paginator = self.paginator
            else:
                assert isinstance(self.paginator, Namespace)
                django_paginator = DjangoPaginator(self.rows, self.page_size)
            self.paginator = Paginator(table=self, django_paginator=django_paginator)

            try:
                self.rows = self.paginator.get_paginated_rows()
            except (InvalidPage, ValueError):
                raise Http404
        else:
            self.paginator = Paginator(table=self, django_paginator=None)

        self.is_paginated = self.paginator.paginator.num_pages > 1 if self.paginator.paginator else False

        self._prepare_auto_rowspan()

    def render_actions(self):
        actions, grouped_actions = group_actions(self.actions)
        return render_template(
            self.get_request(),
            self.actions_template,
            dict(
                actions=actions,
                grouped_actions=grouped_actions,
                table=self,
            ))

    def _prepare_auto_rowspan(self):
        auto_rowspan_columns = [column for column in self.columns.values() if column.auto_rowspan]

        if auto_rowspan_columns:
            self.rows = list(self.rows)
            no_value_set = object()
            for column in auto_rowspan_columns:
                rowspan_by_row = {}  # cells for rows in this dict are displayed, if they're not in here, they get style="display: none"
                prev_value = no_value_set
                prev_row = no_value_set
                for bound_row in self.bound_rows():
                    value = BoundCell(bound_row, column).value
                    if prev_value != value:
                        rowspan_by_row[id(bound_row.row)] = 1
                        prev_value = value
                        prev_row = bound_row.row
                    else:
                        rowspan_by_row[id(prev_row)] += 1

                def rowspan(row, **_):
                    return rowspan_by_row[id(row)] if id(row) in rowspan_by_row else None

                def auto_rowspan_style(row, **_):
                    return 'none' if id(row) not in rowspan_by_row else ''

                assert 'rowspan' not in column.cell.attrs
                column.cell.attrs['rowspan'] = rowspan
                if 'style' not in column.cell.attrs:
                    column.cell.attrs['style'] = {}
                column.cell.attrs['style']['display'] = auto_rowspan_style

    def _prepare_sorting(self):
        request = self.get_request()
        if request is None:
            return

        order = request.GET.get(path_join(self.iommi_path, 'order'), self.default_sort_order)
        if order is not None:
            is_desc = order[0] == '-'
            order_field = is_desc and order[1:] or order
            tmp = [x for x in self.columns.values() if x._name == order_field]
            if len(tmp) == 0:
                return  # Unidentified sort column
            sort_column = tmp[0]
            order_args = evaluate_strict(sort_column.sort_key, column=sort_column)
            order_args = isinstance(order_args, list) and order_args or [order_args]

            if sort_column.sortable:
                if isinstance(self.rows, list):
                    order_by_on_list(self.rows, order_args[0], is_desc)
                else:
                    if not settings.DEBUG:
                        # We should crash on invalid sort commands in DEV, but just ignore in PROD
                        # noinspection PyProtectedMember
                        valid_sort_fields = {x.name for x in get_fields(self.model)}
                        order_args = [order_arg for order_arg in order_args if order_arg.split('__', 1)[0] in valid_sort_fields]
                    order_args = ["%s%s" % (is_desc and '-' or '', x) for x in order_args]
                    self.rows = self.rows.order_by(*order_args)

    def _prepare_headers(self):
        prepare_headers(self)

        superheaders = []
        subheaders = []

        # The id(header) and stuff is to make None not be equal to None in the grouping
        for _, group_iterator in groupby(self.rendered_columns.values(), key=lambda header: header.group or id(header)):
            columns_in_group = list(group_iterator)
            group_name = columns_in_group[0].group

            number_of_columns_in_group = len(columns_in_group)

            superheaders.append(Header(
                display_name=group_name or '',
                table=self,
                attrs=self.superheader.attrs,
                attrs__colspan=number_of_columns_in_group,
                template=self.superheader.template,
            ))

            for i, column in enumerate(columns_in_group):
                subheaders.append(
                    Header(
                        display_name=column.display_name,
                        table=self,
                        attrs=column.header.attrs,
                        template=column.header.template,
                        url=column.url,
                        column=column,
                        number_of_columns_in_group=number_of_columns_in_group,
                        index_in_group=i,
                    )
                )

        if all(c.display_name == '' for c in superheaders):
            superheaders = None

        if superheaders is None:
            self.header_levels = [subheaders]
        else:
            self.header_levels = [superheaders, subheaders]

    def own_evaluate_parameters(self):
        return dict(table=self)

    def bound_rows(self):
        assert self._is_bound
        for i, row in enumerate(self.preprocess_rows(rows=self.rows, table=self)):
            row = self.preprocess_row(table=self, row=row)
            yield BoundRow(table=self, row=row, row_index=i)

    # TODO: would be nicer with a Fragment maybe?
    @property
    def tbody(self):
        return mark_safe('\n'.join([bound_row.__html__() for bound_row in self.bound_rows()]))

    @classmethod
    @dispatch(
        columns=EMPTY,
    )
    def columns_from_model(cls, columns, **kwargs):
        return create_members_from_model(
            member_params_by_member_name=columns,
            default_factory=cls.get_meta().member_class.from_model,
            **kwargs
        )

    @classmethod
    @dispatch(
        columns=EMPTY,
    )
    def _from_model(cls, *, rows=None, model=None, columns=None, include=None, exclude=None, additional=None):
        model, rows = model_and_rows(model, rows)
        assert model is not None or rows is not None, "model or rows must be specified"
        columns = cls.columns_from_model(model=model, include=include, exclude=exclude, additional=additional, columns=columns)
        return model, rows, columns

    def bulk_queryset(self):
        queryset = self.model.objects.all() \
            .filter(**self.bulk_filter) \
            .exclude(**self.bulk_exclude)

        if self.get_request().POST.get('_all_pks_') == '1':
            return queryset
        else:
            pks = [key[len('pk_'):] for key in self.get_request().POST if key.startswith('pk_')]
            return queryset.filter(pk__in=pks)

    @dispatch(
        render=render_template,
        context=EMPTY,
    )
    def __html__(self, *, context=None, render=None):
        assert self._is_bound

        if not context:
            context = {}
        else:
            context = context.copy()

        context['table'] = self
        context['bulk_form'] = self.bulk_form
        context['query'] = self.query

        request = self.get_request()

        assert self.rows is not None
        context['paginator'] = self.paginator

        self.context = context

        if self.query and self.query.form and not self.query.form.is_valid():
            self.rows = None
            self.context['invalid_form_message'] = mark_safe('<i class="fa fa-meh-o fa-5x" aria-hidden="true"></i>')

        return render(request=request, template=self.template, context=self.context)

    @dispatch(
        parts=EMPTY,
    )
    def as_page(self, *, title=None, parts=None):
        from iommi.page import (
            Page,
            html,
        )
        return Page(
            title=title,
            # TODO: do I need to do this pop manually? Won't this be handled by collect_members/bind_members?
            parts__title=html.h1(title, **parts.pop('title', {})),
            # TODO: we should use the name given here, not hard code "table"
            parts__table=self,
            parts=parts,
        )

    @classmethod
    @dispatch(
        parts=EMPTY,
    )
    def as_view(cls, *, title=None, parts=None, **kwargs):
        return create_as_view_from_as_page(cls, 'as', kwargs=kwargs, title=title, parts=parts)

