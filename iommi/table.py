import csv
from datetime import datetime
from enum import (
    auto,
    Enum,
)
from functools import total_ordering
from io import StringIO
from itertools import groupby
from math import ceil
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    Type,
    Union,
)
from urllib.parse import quote_plus

from django.conf import settings
from django.db.models import (
    BooleanField,
    ManyToManyField,
    Model,
    QuerySet,
)
from django.http import (
    FileResponse,
)
from django.utils.encoding import (
    force_str,
)
from django.utils.html import (
    conditional_escape,
)
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
from tri_struct import Struct

from iommi._web_compat import (
    format_html,
    HttpResponseRedirect,
    mark_safe,
    render_template,
    smart_str,
    Template,
)
from iommi.action import (
    Action,
    Actions,
    group_actions,
)
from iommi.attrs import (
    Attrs,
    evaluate_attrs,
    render_attrs,
)
from iommi.base import (
    build_as_view_wrapper,
    capitalize,
    MISSING,
    model_and_rows,
)
from iommi.endpoint import (
    DISPATCH_PREFIX,
    path_join,
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
from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.page import (
    Fragment,
    Header,
    Page,
    Part,
)
from iommi.query import (
    Q_OPERATOR_BY_QUERY_OPERATOR,
    Query,
    QueryException,
)
from iommi.traversable import (
    bound_members,
    declared_members,
    evaluate_member,
    evaluated_refinable,
    EvaluatedRefinable,
    reinvokable,
    set_declared_member,
    Traversable,
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


def params_of_request(request):
    if request is None:
        return {}

    params = request.GET.copy()

    # There can be one dispatch parameter present, we need to filter out that
    for param in params.keys():
        if param.startswith(DISPATCH_PREFIX):
            del params[param]
            break

    return params


def prepare_headers(table):
    request = table.get_request()
    if request is None:
        return

    for name, column in table.rendered_columns.items():
        if column.sortable:
            params = params_of_request(request)
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

            column.header.url = "?" + params.urlencode()
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


def default_cell__value(column, row, **kwargs):
    if column.attr is None:
        return None
    else:
        return getattr_path(row, evaluate_strict(column.attr, row=row, column=column, **kwargs))


SELECT_DISPLAY_NAME = '<i class="fa fa-check-square-o" onclick="iommi_table_js_select_all(this)"></i>'


class DataRetrievalMethods(Enum):
    attribute_access = auto()
    prefetch = auto()
    select = auto()


def default_icon__cell__format(column, value, **_):
    if not value or not column.extra.get('icon', None):
        return column.display_name

    attrs = column.extra.icon_attrs
    attrs['class'][column.extra.icon_prefix + column.extra.icon] = True

    return format_html('<i{}></i> {}', render_attrs(attrs), column.display_name)


@with_meta
class Column(Part):
    """
    Class that describes a column, i.e. the text of the header, how to get and display the data in the cell, etc.

    See :doc:`Table` for more complete examples.

    """
    attr: str = EvaluatedRefinable()
    sort_default_desc: bool = EvaluatedRefinable()
    sortable: bool = EvaluatedRefinable()
    group: Optional[str] = EvaluatedRefinable()
    auto_rowspan: bool = EvaluatedRefinable()
    cell: Namespace = Refinable()
    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    model_field = Refinable()
    field_name = Refinable()
    choices: Iterable = EvaluatedRefinable()
    bulk: Namespace = Refinable()
    filter: Namespace = Refinable()
    superheader = EvaluatedRefinable()
    header: Namespace = EvaluatedRefinable()
    data_retrieval_method = EvaluatedRefinable()
    render_column: bool = EvaluatedRefinable()

    @reinvokable
    @dispatch(
        attr=MISSING,
        sort_default_desc=False,
        sortable=lambda column, **_: column.attr is not None,
        auto_rowspan=False,
        bulk__include=False,
        filter__include=False,
        data_retrieval_method=DataRetrievalMethods.attribute_access,
        cell__template=None,
        cell__attrs=EMPTY,
        cell__value=default_cell__value,
        cell__format=default_cell_formatter,
        cell__url=None,
        cell__url_title=None,
        cell__contents__attrs=EMPTY,
        cell__link=EMPTY,
        header__attrs__class__sorted=lambda column, **_: column.is_sorting,
        header__attrs__class__descending=lambda column, **_: column.sort_direction == DESCENDING,
        header__attrs__class__ascending=lambda column, **_: column.sort_direction == ASCENDING,
        header__attrs__class__first_column=lambda header, **_: header.index_in_group == 0,
        header__attrs__class__subheader=True,
        header__template='iommi/table/header.html',
        header__url=None,
        render_column=True,
    )
    def __init__(self, header, **kwargs):
        """
        Parameters with the prefix `filter__` will be passed along downstream to the `Filter` instance if applicable. This can be used to tweak the filtering of a column.

        :param after: Set the order of columns, see the `howto on ordering <https://docs.iommi.rocks/en/latest/howto.html#how-do-i-reorder-columns>`_ for an example.
        :param attr: What attribute to use, defaults to same as name. Follows django conventions to access properties of properties, so `foo__bar` is equivalent to the python code `foo.bar`. This parameter is based on the filter name of the Column if you use the declarative style of creating tables.
        :param bulk: Namespace to configure bulk actions. See `howto on bulk editing <https://docs.iommi.rocks/en/latest/howto.html#how-do-i-enable-bulk-editing>`_ for an example and more information.
        :param cell: Customize the cell, see See `howto on rendering <https://docs.iommi.rocks/en/latest/howto.html#how-do-i-customize-the-rendering-of-a-cell>`_ and `howto on links <https://docs.iommi.rocks/en/latest/howto.html#how-do-i-make-a-link-in-a-cell>`_
        :param display_name: the text of the header for this column. By default this is based on the `_name` so normally you won't need to specify it.
        :param url: URL of the header. This should only be used if sorting is off.
        :param include: set this to `False` to hide the column
        :param sortable: set this to `False` to disable sorting on this column
        :param sort_key: string denoting what value to use as sort key when this column is selected for sorting. (Or callable when rendering a table from list.)
        :param sort_default_desc: Set to `True` to make table sort link to sort descending first.
        :param group: string describing the group of the header. If this parameter is used the header of the table now has two rows. Consecutive identical groups on the first level of the header are joined in a nice way.
        :param auto_rowspan: enable automatic rowspan for this column. To join two cells with rowspan, just set this `auto_rowspan` to `True` and make those two cells output the same text and we'll handle the rest.
        :param cell__template: name of a template file, or `Template` instance. Gets arguments: `table`, `column`, `cells`, `row` and `value`. Your own arguments should be sent in the 'extra' parameter.
        :param cell__value: string or callable that receives kw arguments: `table`, `column` and `row`. This is used to extract which data to display from the object.
        :param cell__format: string or callable that receives kw arguments: `table`, `column`, `row` and `value`. This is used to convert the extracted data to html output (use `mark_safe`) or a string.
        :param cell__attrs: dict of attr name to callables that receive kw arguments: `table`, `column`, `row` and `value`.
        :param cell__url: callable that receives kw arguments: `table`, `column`, `row` and `value`.
        :param cell__url_title: callable that receives kw arguments: `table`, `column`, `row` and `value`.
        :param render_column: If set to `False` the column won't be rendered in the table, but still be available in `table.columns`. This can be useful if you want some other feature from a column like filtering.
        """

        super(Column, self).__init__(header=HeaderColumnConfig(**header), **kwargs)

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
        return capitalize(force_str(column._name).rsplit('__', 1)[-1].replace("_", " "))

    def on_bind(self) -> None:

        self.table = self._parent._parent

        if self.attr is MISSING:
            self.attr = self._name

        self.bulk = setdefaults_path(
            Struct(),
            self.bulk,
            attr=self.attr,
        )
        self.filter = setdefaults_path(
            Struct(),
            self.filter,
            attr=self.attr,
        )
        self.declared_column = self._declared

        # Not strict evaluate on purpose
        self.model = evaluate(self.model, **self._evaluate_parameters)

    def own_evaluate_parameters(self):
        return dict(column=self)

    @classmethod
    @dispatch(
        filter__call_target__attribute='from_model',
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
        cell__value=lambda table, **_: True,
        cell__format=default_icon__cell__format,
        extra__icon_attrs__class=EMPTY,
        extra__icon_attrs__style=EMPTY,
        attr=None,
    )
    def icon(cls, *args, call_target=None, **kwargs):
        """
        Shortcut to create font awesome-style icons.

        :param extra__icon: the font awesome name of the icon
        """
        assert len(args) in (0, 1), "You can only pass 1 positional argument: icon, or you can pass no arguments."

        if args:
            setdefaults_path(kwargs, dict(extra__icon=args[0]))

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
    def select(cls, checkbox_name='pk', checked=lambda row, **_: False, call_target=None, **kwargs):
        """
        Shortcut for a column of checkboxes to select rows. This is useful for implementing bulk operations.

        :param checkbox_name: the name of the checkbox. Default is `"pk"`, resulting in checkboxes like `"pk_1234"`.
        :param checked: callable to specify if the checkbox should be checked initially. Defaults to `False`.
        """
        setdefaults_path(kwargs, dict(
            cell__value=lambda row, **kwargs: mark_safe('<input type="checkbox"%s class="checkbox" name="%s_%s" />' % (' checked' if evaluate_strict(checked, row=row, **kwargs) else '', checkbox_name, row.pk)),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        filter__call_target__attribute='boolean',
        filter__field__call_target__attribute='boolean_tristate',
        bulk__call_target__attribute='boolean',
        cell__format=lambda value, **_: mark_safe('<i class="fa fa-check" title="Yes"></i>') if value else '',
    )
    def boolean(cls, call_target=None, **kwargs):
        """
        Shortcut to render booleans as a check mark if true or blank if false.
        """
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='boolean',
        filter__call_target__attribute='boolean_tristate',
    )
    def boolean_tristate(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        bulk__call_target__attribute='choice',
        filter__call_target__attribute='choice',
    )
    def choice(cls, call_target=None, **kwargs):
        choices = kwargs['choices']
        setdefaults_path(kwargs, dict(
            bulk__choices=choices,
            filter__choices=choices,
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice',
        bulk__call_target__attribute='choice_queryset',
        filter__call_target__attribute='choice_queryset',
    )
    def choice_queryset(cls, call_target=None, **kwargs):
        setdefaults_path(kwargs, dict(
            bulk__model=kwargs.get('model'),
            filter__model=kwargs.get('model'),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice_queryset',
        bulk__call_target__attribute='multi_choice_queryset',
        filter__call_target__attribute='multi_choice_queryset',
    )
    def multi_choice_queryset(cls, call_target, **kwargs):
        setdefaults_path(kwargs, dict(
            bulk__model=kwargs.get('model'),
            filter__model=kwargs.get('model'),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice',
        bulk__call_target__attribute='multi_choice',
        filter__call_target__attribute='multi_choice',
    )
    def multi_choice(cls, call_target, **kwargs):
        setdefaults_path(kwargs, dict(
            bulk__model=kwargs.get('model'),
            filter__model=kwargs.get('model'),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        bulk__call_target__attribute='text',
        filter__call_target__attribute='text',
    )
    def text(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut
    def link(cls, call_target, **kwargs):
        # Shortcut for creating a cell that is a link. The URL is the result of calling `get_absolute_url()` on the object.
        def link_cell_url(column, row, **_):
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
        filter__call_target__attribute='float',
        bulk__call_target__attribute='float',
    )
    def float(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='number',
        filter__call_target__attribute='integer',
        bulk__call_target__attribute='integer',
    )
    def integer(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        filter__query_operator_for_field=':',
    )
    def substring(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        filter__call_target__attribute='date',
        filter__query_operator_to_q_operator=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OPERATOR_BY_QUERY_OPERATOR[op],
        bulk__call_target__attribute='date',
    )
    def date(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        filter__call_target__attribute='datetime',
        filter__query_operator_to_q_operator=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OPERATOR_BY_QUERY_OPERATOR[op],
        bulk__call_target__attribute='datetime',
    )
    def datetime(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        filter__call_target__attribute='time',
        filter__query_operator_to_q_operator=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OPERATOR_BY_QUERY_OPERATOR[op],
        bulk__call_target__attribute='time',
    )
    def time(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        filter__call_target__attribute='email',
        bulk__call_target__attribute='email',
    )
    def email(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        bulk__call_target__attribute='decimal',
        filter__call_target__attribute='decimal',
    )
    def decimal(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        bulk__call_target__attribute='file',
        filter__call_target__attribute='file',
        cell__format=lambda value, **_: str(value)
    )
    def file(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='multi_choice_queryset',
        bulk__call_target__attribute='many_to_many',
        filter__call_target__attribute='many_to_many',
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
        filter__call_target__attribute='foreign_key',
        data_retrieval_method=DataRetrievalMethods.select,
    )
    def foreign_key(cls, call_target, model_field, **kwargs):
        model = model_field.foreign_related_fields[0].model
        if hasattr(model, 'get_absolute_url'):
            setdefaults_path(
                kwargs,
                cell__url=lambda value, **_: value.get_absolute_url() if value is not None else None,
            )
        setdefaults_path(
            kwargs,
            choices=model.objects.all(),
            model_field=model,
        )
        return call_target(**kwargs)


class Cells(Traversable):
    """
    Internal class used in row rendering
    """
    template: Union[str, Template] = EvaluatedRefinable()
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    tag: str = EvaluatedRefinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[str, Any] = Refinable()  # not EvaluatedRefinable because this is an evaluated container so is special

    def __init__(self, row, row_index, **kwargs):
        super(Cells, self).__init__(_name='row', **kwargs)
        assert not isinstance(row, Cells)
        self.row: Any = row
        self.row_index = row_index

    def own_evaluate_parameters(self):
        return dict(cells=self, row=self.row)

    def __html__(self):
        if self.template:
            return render_template(self._parent.get_request(), self.template, self._evaluate_parameters)

        return Fragment(
            tag=self.tag,
            attrs=self.attrs,
            children__text=mark_safe('\n'.join(
                bound_cell.__html__()
                for bound_cell in self
            ))
        ).bind(parent=self).__html__()

    def __str__(self):
        return self.__html__()

    def __iter__(self):
        for column in self._parent.rendered_columns.values():
            yield Cell(cells=self, column=column)

    def __getitem__(self, name):
        column = self._parent.rendered_columns[name]
        return Cell(cells=self, column=column)


class CellConfig(RefinableObject):
    url: str = Refinable()
    url_title: str = Refinable()
    attrs: Attrs = Refinable()
    tag: str = Refinable()
    template: Union[str, Template] = Refinable()
    value = Refinable()
    contents = Refinable()
    format: Callable = Refinable()
    link = Refinable()


class Cell(CellConfig):

    @dispatch
    def __init__(self, cells: Cells, column):
        kwargs = setdefaults_path(
            Namespace(),
            column.cell,
            column.table.cell,
        )
        super(Cell, self).__init__(**kwargs)
        self._name = 'cell'
        self._parent = cells
        self._is_bound = True
        self.iommi_style = None
        self._unapplied_config = {}

        self.column = column
        self.cells = cells
        self.table = cells._parent
        self.row = cells.row

        self._evaluate_parameters = {**self._parent._evaluate_parameters, 'column': column}

        self.value = evaluate_strict(self.value, **self._evaluate_parameters)
        self._evaluate_parameters['value'] = self.value
        self.url = evaluate_strict(self.url, **self._evaluate_parameters)
        self.attrs = evaluate_attrs(self, **self._evaluate_parameters)
        self.url_title = evaluate_strict(self.url_title, **self._evaluate_parameters)

    @property
    def iommi_dunder_path(self):
        return path_join(self.column.iommi_dunder_path, 'cell', separator='__')

    def __html__(self):
        cell__template = self.column.cell.template
        if cell__template:
            context = dict(table=self.table, column=self.column, cells=self.cells, row=self.row, value=self.value, bound_cell=self)
            return render_template(self.table.get_request(), cell__template, context)

        return Fragment(
            tag=self.tag,
            attrs=self.attrs,
            children__content=self.render_cell_contents()
        ).bind(parent=self).__html__()

    def render_cell_contents(self):
        cell_contents = self.render_formatted()

        url = self.url
        if url:
            url_title = self.url_title
            # TODO: `url`, `url_title` and `link` is overly complex
            cell_contents = Fragment(
                tag='a',
                attrs__title=url_title,
                attrs__href=url,
                children__content=cell_contents,
                **self.link
            ).bind(parent=self.table).__html__()
        return cell_contents

    def render_formatted(self):
        return evaluate_strict(self.column.cell.format, table=self.table, column=self.column, row=self.row, value=self.value)

    def __str__(self):
        return self.__html__()

    def __repr__(self):
        return f"<{type(self).__name__} column={self.column.declared_column!r} row={self.cells.row}!r>"  # pragma: no cover


class TemplateConfig(RefinableObject):
    template: str = Refinable()


class HeaderConfig(Traversable):
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = EvaluatedRefinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[str, Any] = Refinable()
    url = EvaluatedRefinable()

    def __html__(self):
        return render_template(self.get_request(), self.template, self._parent._evaluate_parameters)

    def __str__(self):
        return self.__html__()


class HeaderColumnConfig(Traversable):
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = EvaluatedRefinable()
    url = EvaluatedRefinable()


class RowConfig(RefinableObject):
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    tag = Refinable()
    template: Union[str, Template] = Refinable()
    extra: Dict[str, Any] = Refinable()
    extra_evaluated: Dict[str, Any] = Refinable()

    def as_dict(self):
        return {k: getattr(self, k) for k in self.get_declared('refinable_members').keys()}


class ColumnHeader(object):
    """
    Internal class implementing a column header. For configuration options
    read the docs for :doc:`HeaderConfig`.
    """

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
        return f'<Header: {"superheader" if self.column is None else self.column._name}>'

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

    from iommi.page import (
        Page,
        html,
    )

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
                    attrs__name=table.bulk_form.actions.delete.attrs.name,
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


class Paginator(Traversable):
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = EvaluatedRefinable()
    container = Refinable()
    page: int = Refinable()  # page is evaluated, but in a special way so gets no EvaluatedRefinable type
    active_item = Refinable()
    item = Refinable()
    link = Refinable()
    adjacent_pages: int = Refinable()
    min_page_size: int = Refinable()
    number_of_pages: int = Refinable()  # number_of_pages is evaluated, but in a special way so gets no EvaluatedRefinable type
    count: int = Refinable()  # count is evaluated, but in a special way so gets no EvaluatedRefinable type
    slice = Refinable()
    show_always = Refinable()

    @dispatch(
        adjacent_pages=6,
        min_page_size=1,

        attrs__class=EMPTY,
        attrs__style=EMPTY,

        container__attrs__class=EMPTY,
        container__attrs__style=EMPTY,

        active_item__attrs__class=EMPTY,
        active_item__attrs__style=EMPTY,

        item__attrs__class=EMPTY,
        item__attrs__style=EMPTY,

        link__attrs__class=EMPTY,
        link__attrs__style=EMPTY,

        page=1,

        count=lambda rows, **_: rows.count() if isinstance(rows, QuerySet) else len(rows),
        number_of_pages=lambda paginator, rows, **_: ceil(max(1, (paginator.count - (paginator.min_page_size - 1))) / paginator.page_size),
        slice=lambda top, bottom, rows, **_: rows[bottom:top],
    )
    def __init__(self, **kwargs):
        super(Paginator, self).__init__(**kwargs)
        self._name = 'page'
        self.context = None
        self.page_size = None
        self.rows = None

    def on_bind(self) -> None:
        request = self.get_request()
        page_size = request.GET.get(self.iommi_path + '_size') if request else None
        self.page_size = self._parent.page_size if page_size is None else int(page_size)

        self.attrs = evaluate_attrs(self)
        self.container.attrs = evaluate_attrs(self.container)
        self.active_item.attrs = evaluate_attrs(self.active_item)
        self.item.attrs = evaluate_attrs(self.item)
        self.link.attrs = evaluate_attrs(self.link)

        rows = self._parent.rows
        evaluate_parameters = dict(
            page_size=self.page_size,
            rows=rows,
            **self._evaluate_parameters,
        )

        if self.page_size is None:
            self.number_of_pages = 1
        else:
            self.count = evaluate_strict(self.count, **evaluate_parameters) if rows is not None else 0
            self.number_of_pages = evaluate_strict(self.number_of_pages, **evaluate_parameters)

        page = request.GET.get(self.iommi_path) if request else None
        page = evaluate_strict(self.page, **evaluate_parameters) if page is None else int(page)
        self.page = page

        if self.page > self.number_of_pages:
            self.page = self.number_of_pages
        elif self.page < 1:
            self.page = 1

        self.context = self._evaluate_parameters.copy()

        if self.number_of_pages != 1:
            bottom = (self.page - 1) * self.page_size
            top = bottom + self.page_size
            if top + self.min_page_size - 1 >= self.count:
                top = self.count
            paginated_rows = self.slice(**evaluate_parameters, bottom=bottom, top=top)
            self.rows = paginated_rows
        else:
            self.rows = evaluate_parameters['rows']

        foo = self.page
        if foo <= self.adjacent_pages:
            foo = self.adjacent_pages + 1
        elif foo > self.number_of_pages - self.adjacent_pages:
            foo = self.number_of_pages - self.adjacent_pages
        page_numbers = [
            n for n in
            range(self.page - self.adjacent_pages, foo + self.adjacent_pages + 1)
            if 0 < n <= self.number_of_pages
        ]

        get = params_of_request(request)

        if self.iommi_path in get:
            del get[self.iommi_path]

        self.context.update(dict(
            extra=get and (get.urlencode() + "&") or "",
            page_numbers=page_numbers,
            show_first=1 not in page_numbers,
            show_last=self.number_of_pages not in page_numbers,
        ))

        has_next = self.page < self.number_of_pages
        has_previous = self.page > 1
        self.context.update({
            'page_size': self._parent.page_size,
            'has_next': has_next,
            'has_previous': has_previous,
            'next': self.page + 1 if has_next else None,
            'previous': self.page - 1 if has_previous else None,
            'page': self.page,
            'pages': self.number_of_pages,
            'hits': self.count,
            'paginator': self,
        })

    def own_evaluate_parameters(self):
        return dict(paginator=self)

    def is_paginated(self):
        assert self._is_bound
        return self.number_of_pages == 1

    def __html__(self):
        assert self._is_bound
        if not self.show_always:
            if self.page_size is None:
                return ''

            if self.number_of_pages <= 1:
                return ''

        return render_template(
            request=self.get_request(),
            template=self.template,
            context=self.context,
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

    def cell_value(cells, bound_column):
        value = Cell(cells, bound_column).value
        return bound_column.extra_evaluated.get('report_value', value)

    def rows():
        for cells in table.cells_for_rows():
            yield [cell_value(cells, bound_column) for bound_column in columns]

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
    response['Content-Disposition'] = smart_str("attachment; filename*=UTF-8''{value}".format(value=quote_plus(filename)))
    response['Last-Modified'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response


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
    bulk_filter: Namespace = EvaluatedRefinable()
    bulk_exclude: Namespace = EvaluatedRefinable()
    sortable: bool = EvaluatedRefinable()
    query_from_indexes: bool = Refinable()
    default_sort_order = Refinable()
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = EvaluatedRefinable()
    tag: str = EvaluatedRefinable()
    h_tag: Fragment = Refinable()  # h_tag is evaluated, but in a special way so gets no EvaluatedRefinable type
    title: Fragment = Refinable()  # title is evaluated, but in a special way so gets no EvaluatedRefinable type
    row: RowConfig = EvaluatedRefinable()
    cell: CellConfig = EvaluatedRefinable()
    header = Refinable()
    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    rows = Refinable()  # rows is evaluated, but in a special way so gets no EvaluatedRefinable type
    columns = Refinable()
    bulk: Namespace = EvaluatedRefinable()
    superheader: Namespace = Refinable()
    paginator: Paginator = Refinable()
    page_size: int = EvaluatedRefinable()
    actions_template: Union[str, Template] = EvaluatedRefinable()

    member_class = Refinable()
    form_class: Type[Form] = Refinable()
    query_class: Type[Query] = Refinable()
    action_class: Type[Action] = Refinable()
    page_class: Type[Page] = Refinable()

    class Meta:
        member_class = Column
        form_class = Form
        query_class = Query
        action_class = Action
        page_class = Page
        endpoints__tbody__func = (lambda table, **_: {'html': table.__html__(template='iommi/table/table_tag.html')})
        endpoints__csv__func = endpoint__csv

        attrs = Namespace({
            'data-endpoint': lambda table, **_: DISPATCH_PREFIX + table.endpoints.tbody.iommi_path,
        })

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

    @reinvokable
    @dispatch(
        columns=EMPTY,
        bulk_filter={},
        bulk_exclude={},
        sortable=True,
        default_sort_order=None,
        template='iommi/table/table.html',
        row__tag='tr',
        row__attrs__class=EMPTY,
        row__attrs__style=EMPTY,
        row__attrs={'data-pk': lambda row, **_: getattr(row, 'pk', None)},
        row__template=None,
        row__extra=EMPTY,
        row__extra_evaluated=EMPTY,
        cell__tag='td',
        header__template='iommi/table/table_header_rows.html',
        h_tag__call_target=Header,

        actions=EMPTY,
        actions_template='iommi/form/actions.html',
        query=EMPTY,
        bulk__fields=EMPTY,
        bulk__title='Bulk change',
        page_size=DEFAULT_PAGE_SIZE,

        endpoints=EMPTY,

        superheader__attrs__class__superheader=True,
        superheader__template='iommi/table/header.html',

        auto=EMPTY,
        tag='table',
        attrs__class=EMPTY,
        attrs__style=EMPTY,

        paginator__call_target=Paginator,
    )
    def __init__(self, *, columns: Namespace = None, _columns_dict=None, model=None, rows=None, bulk=None, header=None, query=None, row=None, actions: Namespace = None, auto, title=MISSING, paginator, **kwargs):
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
        select_conf = columns.get('select', {})
        if 'select' not in _columns_dict and isinstance(select_conf, dict):
            columns['select'] = setdefaults_path(
                Namespace(),
                select_conf,
                call_target__attribute='select',
                attr=None,
                after=-1,
                include=False,
            )

        if auto:
            auto = TableAutoConfig(**auto)
            auto_model, auto_rows, columns = self._from_model(
                model=auto.model,
                rows=auto.rows,
                columns=columns,
                include=auto.include,
                exclude=auto.exclude,
            )

            assert model is None, "You can't use the auto feature and explicitly pass model. " \
                                  "Either pass auto__model, or we will set the model for you from auto__rows"
            model = auto_model

            if rows is None:
                rows = auto_rows

            if title is MISSING:
                title = f'{model._meta.verbose_name_plural.title()}'

        model, rows = model_and_rows(model, rows)

        assert isinstance(columns, dict)

        self.columns = None
        self.rendered_columns = None

        super(Table, self).__init__(
            model=model,
            rows=rows,
            header=HeaderConfig(**header),
            row=RowConfig(**row),
            bulk=bulk,
            title=title,
            **kwargs
        )

        collect_members(self, name='actions', items=actions, cls=self.get_meta().action_class)
        collect_members(self, name='columns', items=columns, items_dict=_columns_dict, cls=self.get_meta().member_class)

        self.query_args = query
        self.query: Query = None

        self.bulk_form: Form = None
        self.header_levels = None

        if self.model:
            # Query
            filters = Struct()
            for name, column in declared_members(self).columns.items():
                filter = setdefaults_path(
                    Namespace(),
                    column.filter,
                    call_target__cls=self.get_meta().query_class.get_meta().member_class,
                    model=self.model,
                    _name=name,
                    attr=name if column.attr is MISSING else column.attr,
                    field__call_target__cls=self.get_meta().query_class.get_meta().form_class.get_meta().member_class,
                )
                if 'call_target' not in filter['call_target'] and filter['call_target'].get(
                        'attribute') == 'from_model':
                    filter['field_name'] = filter.attr
                # Special case for automatic query config
                if self.query_from_indexes and column.model_field and getattr(column.model_field, 'db_index', False):
                    filter.include = True

                filters[name] = filter()

            self.query = self.get_meta().query_class(
                _filters_dict=filters,
                _name='query',
                **self.query_args
            )
            declared_members(self).query = self.query

            # Bulk
            field_class = self.get_meta().form_class.get_meta().member_class

            declared_bulk_fields = Struct()
            for name, column in declared_members(self).columns.items():
                field = self.bulk.fields.pop(name, {})

                if column.bulk.include:
                    field = setdefaults_path(
                        Namespace(),
                        column.bulk,
                        call_target__cls=field_class,
                        model=self.model,
                        _name=name,
                        attr=name if column.attr is MISSING else column.attr,
                        required=False,
                        empty_choice_tuple=(None, '', '---', True),
                        parse_empty_string_as_none=True,
                        **field
                    )
                    if isinstance(column.model_field, BooleanField):
                        field.call_target.attribute = 'boolean_tristate'
                    if 'call_target' not in field['call_target'] and field['call_target'].get('attribute') == 'from_model':
                        field['field_name'] = field.attr

                    declared_bulk_fields[name] = field()

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
                    display_name='Bulk change',
                    include=lambda table, **_: any(c.bulk.include for c in table.columns.values()),
                ),
                actions__delete=dict(
                    call_target__attribute='delete',
                    post_handler=bulk_delete__post_handler,
                    display_name='Bulk delete',
                    include=False,
                ),
                **bulk
            )

            declared_members(self).bulk = self.bulk_form

        # Columns need to be at the end to not steal the short names
        declared_members(self).columns = declared_members(self).pop('columns')

        self.paginator = paginator()
        self._declared_members['page'] = self.paginator

    def on_bind(self) -> None:
        bind_members(self, name='actions', cls=Actions)
        bind_members(self, name='columns')
        bind_members(self, name='endpoints')

        self.title = evaluate_strict(self.title, **self._evaluate_parameters)
        if isinstance(self.h_tag, Namespace):
            if self.title not in (None, MISSING):
                self.h_tag = self.h_tag(
                    _name='h_tag',
                    children__text=capitalize(self.title)
                ).bind(parent=self)
            else:
                self.h_tag = ''
        else:
            self.h_tag = self.h_tag.bind(parent=self)

        self.header = self.header.bind(parent=self)

        evaluate_member(self, 'sortable', **self._evaluate_parameters)  # needs to be done first because _prepare_headers depends on it

        evaluate_member(self, 'model', strict=False, **self._evaluate_parameters)
        evaluate_member(self, 'rows', **self._evaluate_parameters)
        self._prepare_sorting()

        for column in self.columns.values():
            # Special case for entire table not sortable
            if not self.sortable:
                column.sortable = False

        self._setup_bulk_form_and_query()

        self.rendered_columns = Struct({name: column for name, column in self.columns.items() if column.render_column})
        for c in self.rendered_columns.values():
            assert c.include

        self._prepare_headers()

        if isinstance(self.rows, QuerySet):
            prefetch = [x.attr for x in self.columns.values() if x.data_retrieval_method == DataRetrievalMethods.prefetch and x.attr]
            select = [x.attr for x in self.columns.values() if x.data_retrieval_method == DataRetrievalMethods.select and x.attr]
            if prefetch:
                self.rows = self.rows.prefetch_related(*prefetch)
            if select:
                self.rows = self.rows.select_related(*select)

        self.paginator = self.paginator.bind(parent=self)
        self.rows = self.paginator.rows
        self._prepare_auto_rowspan()

    def _setup_bulk_form_and_query(self):
        if not self.model:
            self.bulk_form = None
            self.query_form = None
            return

        declared_filters = declared_members(self.query)['filters']
        for name, column in self.columns.items():
            if name in declared_filters:
                filter = Namespace(
                    field__display_name=column.display_name,
                )
                declared_filters[name] = declared_filters[name].reinvoke(filter)
        set_declared_member(self.query, 'filters', declared_filters)

        self.query = self.query.bind(parent=self)
        self._bound_members.query = self.query

        if self.query.form:
            q = None
            try:
                q = self.query.get_q()
            except QueryException:
                pass
            if q:
                self.rows = self.rows.filter(q)

        declared_fields = declared_members(self.bulk_form)['fields']
        for name, column in self.columns.items():
            if name in declared_fields:
                field = setdefaults_path(
                    Namespace(),
                    column.bulk,
                    include=column.bulk.include,
                    display_name=column.display_name,
                )
                declared_fields[name] = declared_fields[name].reinvoke(field)
        set_declared_member(self.bulk_form, 'fields', declared_fields)

        self.bulk_form = self.bulk_form.bind(parent=self)
        if self.bulk_form.actions:
            self._bound_members.bulk = self.bulk_form
        else:
            self.bulk_form = None

    # property for jinja2 compatibility
    @property
    def render_actions(self):
        assert self._is_bound, 'The table has not been bound. You need to call bind() before you can render it.'
        non_grouped_actions, grouped_actions = group_actions(self.actions)
        return render_template(
            self.get_request(),
            self.actions_template,
            dict(
                actions=bound_members(self).actions,
                non_grouped_actions=non_grouped_actions,
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
                for cells in self.cells_for_rows():
                    value = Cell(cells, column).value
                    if prev_value != value:
                        rowspan_by_row[id(cells.row)] = 1
                        prev_value = value
                        prev_row = cells.row
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

            superheaders.append(ColumnHeader(
                display_name=group_name or '',
                table=self,
                attrs=self.superheader.attrs,
                attrs__colspan=number_of_columns_in_group,
                template=self.superheader.template,
            ))

            for i, column in enumerate(columns_in_group):
                subheaders.append(
                    ColumnHeader(
                        display_name=column.display_name,
                        table=self,
                        attrs=column.header.attrs,
                        template=column.header.template,
                        url=column.header.url,
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

    def cells_for_rows(self):
        assert self._is_bound
        for i, row in enumerate(self.preprocess_rows(rows=self.rows, **self._evaluate_parameters)):
            row = self.preprocess_row(table=self, row=row)
            yield Cells(row=row, row_index=i, **self.row.as_dict()).bind(parent=self)

    @property
    def tbody(self):
        return mark_safe('\n'.join([cells.__html__() for cells in self.cells_for_rows()]))

    @classmethod
    @dispatch(
        columns=EMPTY,
    )
    def columns_from_model(cls, columns, **kwargs):
        return create_members_from_model(
            member_class=cls.get_meta().member_class,
            member_params_by_member_name=columns,
            **kwargs
        )

    @classmethod
    @dispatch(
        columns=EMPTY,
    )
    def _from_model(cls, *, rows=None, model=None, columns=None, include=None, exclude=None):
        assert rows is None or isinstance(rows, QuerySet), \
            'auto__rows needs to be a QuerySet for column generation to work' \
            'If it needs to be a lambda, provide a model with auto__model for column generation, ' \
            'and pass the lambda as rows.'

        model, rows = model_and_rows(model, rows)
        assert model is not None or rows is not None, "auto__model or auto__rows must be specified"
        columns = cls.columns_from_model(model=model, include=include, exclude=exclude, columns=columns)
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
    )
    def __html__(self, *, template=None, render=None):
        assert self._is_bound

        request = self.get_request()

        assert self.rows is not None

        context = self._evaluate_parameters.copy()
        context['query'] = self.query
        context['bulk_form'] = self.bulk_form

        if self.query and self.query.form and not self.query.form.is_valid():
            self.rows = None
            context['invalid_form_message'] = mark_safe('<i class="fa fa-meh-o fa-5x" aria-hidden="true"></i>')

        return render(request=request, template=template or self.template, context=context)

    def as_view(self):
        return build_as_view_wrapper(self)
