import copy
import warnings
from collections import OrderedDict
from enum import (
    auto,
    Enum,
)
from functools import total_ordering
from itertools import groupby
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Type,
    Union,
    Callable,
)

from django.conf import settings
from django.core.paginator import (
    InvalidPage,
    Paginator,
)
from django.db.models import QuerySet
from django.http import (
    Http404,
    HttpResponseRedirect,
)
from django.utils.encoding import (
    force_text,
)
from django.utils.html import (
    conditional_escape,
    format_html,
)
from django.utils.safestring import mark_safe
from iommi._web_compat import (
    render_template,
    Template,
)
from iommi.base import (
    PagePart,
    path_join,
    setup_endpoint_proxies,
    DISPATCH_PREFIX,
    model_and_rows,
    no_copy_on_bind,
    collect_members,
    bind_members,
)
from iommi.form import (
    Action,
    create_members_from_model,
    expand_member,
    Form,
    group_actions,
    member_from_model,
)
from iommi.query import (
    Q_OP_BY_OP,
    Query,
    QueryException,
)
from iommi.render import (
    render_attrs,
)
from tri_declarative import (
    class_shortcut,
    declarative,
    dispatch,
    EMPTY,
    evaluate,
    evaluate_recursive,
    getattr_path,
    LAST,
    Namespace,
    Refinable,
    refinable,
    RefinableObject,
    setattr_path,
    setdefaults_path,
    sort_after,
    with_meta,
    evaluate_strict,
)
from tri_named_struct import (
    NamedStruct,
    NamedStructField,
)
from tri_struct import (
    merged,
    Struct,
)

LAST = LAST

_column_factory_by_field_type = OrderedDict()


def register_column_factory(field_class, factory):
    _column_factory_by_field_type[field_class] = factory


def evaluate_members(obj, attrs, **kwargs):
    for attr in attrs:
        setattr(obj, attr, evaluate_recursive(getattr(obj, attr), **kwargs))


DESCENDING = 'descending'
ASCENDING = 'ascending'

DEFAULT_PAGE_SIZE = 40


def prepare_headers(table, bound_columns):
    request = table.request()
    if request is None:
        return

    for column in bound_columns:
        if column.sortable:
            params = request.GET.copy()
            param_path = path_join(table.path(), 'order')
            order = request.GET.get(param_path, None)
            start_sort_desc = column.sort_default_desc
            params[param_path] = column.name if not start_sort_desc else '-' + column.name
            column.is_sorting = False
            if order is not None:
                is_desc = order.startswith('-')
                order_field = order if not is_desc else order[1:]
                if order_field == column.name:
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
    :param order_field: field name, follows django conventions, so "foo__bar" means `foo.bar`, can be a callable.
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
class Column(RefinableObject, PagePart):
    """
    Class that describes a column, i.e. the text of the header, how to get and display the data in the cell, etc.
    """
    name: str = Refinable()
    after: Union[int, str] = Refinable()
    url: str = Refinable()
    show: bool = Refinable()
    sort_default_desc: bool = Refinable()
    sortable: bool = Refinable()
    group: Optional[str] = Refinable()
    auto_rowspan: bool = Refinable()
    cell: Namespace = Refinable()
    model = Refinable()
    model_field = Refinable()
    choices: Iterable = Refinable()
    bulk: Namespace = Refinable()
    query: Namespace = Refinable()
    extra: Namespace = Refinable()
    superheader = Refinable()
    header: Namespace = Refinable()
    data_retrieval_method = Refinable()

    @dispatch(
        show=True,
        sort_default_desc=False,
        sortable=True,
        auto_rowspan=False,
        bulk__show=False,
        query__show=False,
        data_retrieval_method=DataRetrievalMethods.attribute_access,
        cell__template=None,
        cell__attrs=EMPTY,
        cell__value=lambda table, bound_column, row, **_: getattr_path(row, evaluate_strict(bound_column.attr, table=table, bound_column=bound_column)),
        cell__format=default_cell_formatter,
        cell__url=None,
        cell__url_title=None,
        extra=EMPTY,
        header__attrs__class__sorted_column=lambda bound_column, **_: bound_column.is_sorting,
        header__attrs__class__descending=lambda bound_column, **_: bound_column.sort_direction == DESCENDING,
        header__attrs__class__ascending=lambda bound_column, **_: bound_column.sort_direction == ASCENDING,
        header__attrs__class__first_column=lambda header, **_: header.index_in_group == 0,
        header__attrs__class__subheader=True,
        header__template='iommi/table/header.html',
    )
    def __init__(self, **kwargs):
        """
        :param name: the name of the column
        :param attr: What attribute to use, defaults to same as name. Follows django conventions to access properties of properties, so "foo__bar" is equivalent to the python code `foo.bar`. This parameter is based on the variable name of the Column if you use the declarative style of creating tables.
        :param display_name: the text of the header for this column. By default this is based on the `name` parameter so normally you won't need to specify it.
        :param url: URL of the header. This should only be used if "sorting" is off.
        :param show: set this to False to hide the column
        :param sortable: set this to False to disable sorting on this column
        :param sort_key: string denoting what value to use as sort key when this column is selected for sorting. (Or callable when rendering a table from list.)
        :param sort_default_desc: Set to True to make table sort link to sort descending first.
        :param group: string describing the group of the header. If this parameter is used the header of the table now has two rows. Consecutive identical groups on the first level of the header are joined in a nice way.
        :param auto_rowspan: enable automatic rowspan for this column. To join two cells with rowspan, just set this auto_rowspan to True and make those two cells output the same text and we'll handle the rest.
        :param cell__template: name of a template file, or `Template` instance. Gets arguments: `table`, `bound_column`, `bound_row`, `row` and `value`. Your own arguments should be sent in the 'extra' parameter.
        :param cell__value: string or callable that receives kw arguments: `table`, `column` and `row`. This is used to extract which data to display from the object.
        :param cell__format: string or callable that receives kw arguments: `table`, `column`, `row` and `value`. This is used to convert the extracted data to html output (use `mark_safe`) or a string.
        :param cell__attrs: dict of attr name to callables that receive kw arguments: `table`, `column`, `row` and `value`.
        :param cell__url: callable that receives kw arguments: `table`, `column`, `row` and `value`.
        :param cell__url_title: callable that receives kw arguments: `table`, `column`, `row` and `value`.
        """

        if 'attrs' in kwargs:
            if not kwargs['attrs']['class']:
                del kwargs['attrs']['class']

            if not kwargs['attrs']:
                kwargs.pop('attrs')

        super(Column, self).__init__(**kwargs)

        # TODO: this seems weird.. why do we need this?
        self.declared_column: Column = None
        self.is_sorting: bool = None
        self.sort_direction: str = None

    def __repr__(self):
        return '<{}.{} {}>'.format(self.__class__.__module__, self.__class__.__name__, self.name)

    @property
    def table(self):
        return self.parent

    @staticmethod
    @refinable
    def attr(table, column, **_):
        return column.name

    @staticmethod
    @refinable
    def sort_key(table, column, **_):
        return column.attr

    @staticmethod
    @refinable
    def display_name(table, column, **_):
        return force_text(column.name).rsplit('__', 1)[-1].replace("_", " ").capitalize()

    def on_bind(self) -> None:
        for k, v in self.parent._column.get(self.name, {}).items():
            setattr_path(self, k, v)

        self.header.attrs = Namespace(self.header.attrs.copy())
        self.header.attrs['class'] = Namespace(self.header.attrs['class'].copy())

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

    def _evaluate(self):
        """
        Evaluates callable/lambda members. After this function is called all members will be values.
        """
        evaluated_attributes = self.get_declared('refinable_members').keys()
        for k in evaluated_attributes:
            v = getattr(self, k)
            new_value = evaluate_recursive(v, table=self.table, column=self)
            if new_value is not v:
                setattr(self, k, new_value)

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
    def expand_member(cls, model, field_name=None, model_field=None, **kwargs):
        return expand_member(
            cls=cls,
            model=model,
            factory_lookup=_column_factory_by_field_type,
            field_name=field_name,
            model_field=model_field,
            **kwargs)

    @classmethod
    @class_shortcut(
        name='',
        display_name='',
        sortable=False,
        header__attrs__class__thin=True,
        cell__value=lambda table, **_: True,
        cell__attrs__class__cj=True,
    )
    def icon(cls, icon, is_report=False, icon_title=None, show=True, call_target=None, **kwargs):
        """
        Shortcut to create font awesome-style icons.

        :param icon: the font awesome name of the icon
        """
        setdefaults_path(kwargs, dict(
            show=lambda table, **rest: evaluate(show, table=table, **rest) and not is_report,
            header__attrs__title=icon_title,
            cell__format=lambda value, **_: mark_safe('<i class="fa fa-lg fa-%s"%s></i>' % (icon, ' title="%s"' % icon_title if icon_title else '')) if value else ''
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='icon',
        cell__url=lambda row, **_: row.get_absolute_url() + 'edit/',
        display_name=''
    )
    def edit(cls, is_report=False, call_target=None, **kwargs):
        """
        Shortcut for creating a clickable edit icon. The URL defaults to `your_object.get_absolute_url() + 'edit/'`. Specify the option cell__url to override.
        """
        return call_target('pencil-square-o', is_report, 'Edit', **kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='icon',
        cell__url=lambda row, **_: row.get_absolute_url() + 'delete/',
        display_name=''
    )
    def delete(cls, is_report=False, call_target=None, **kwargs):
        """
        Shortcut for creating a clickable delete icon. The URL defaults to `your_object.get_absolute_url() + 'delete/'`. Specify the option cell__url to override.
        """
        return call_target('trash-o', is_report, 'Delete', **kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='icon',
        cell__url=lambda row, **_: row.get_absolute_url() + 'download/',
        cell__value=lambda row, **_: getattr(row, 'pk', False),
    )
    def download(cls, is_report=False, call_target=None, **kwargs):
        """
        Shortcut for creating a clickable download icon. The URL defaults to `your_object.get_absolute_url() + 'download/'`. Specify the option cell__url to override.
        """
        return call_target('download', is_report, 'Download', **kwargs)

    @classmethod
    @class_shortcut(
        name='',
        header__attrs__title='Run',
        sortable=False,
        header__attrs__class__thin=True,
        cell__url=lambda row, **_: row.get_absolute_url() + 'run/',
        cell__value='Run',
    )
    def run(cls, is_report=False, show=True, call_target=None, **kwargs):
        """
        Shortcut for creating a clickable run icon. The URL defaults to `your_object.get_absolute_url() + 'run/'`. Specify the option cell__url to override.
        """
        setdefaults_path(kwargs, dict(
            show=lambda table, **rest: evaluate(show, table=table, **rest) and not is_report,
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        name='__select__',
        header__attrs__title='Select all',
        display_name=mark_safe(SELECT_DISPLAY_NAME),
        sortable=False,
        header__attrs__class__thin=True,
        header__attrs__class__nopad=True,
        cell__attrs__class__cj=True,
    )
    def select(cls, is_report=False, checkbox_name='pk', show=True, checked=lambda x: False, call_target=None, **kwargs):
        """
        Shortcut for a column of checkboxes to select rows. This is useful for implementing bulk operations.

        :param checkbox_name: the name of the checkbox. Default is "pk", resulting in checkboxes like "pk_1234".
        :param checked: callable to specify if the checkbox should be checked initially. Defaults to False.
        """
        setdefaults_path(kwargs, dict(
            show=lambda table, **rest: evaluate(show, table=table, **rest) and not is_report,
            cell__value=lambda row, **_: mark_safe('<input type="checkbox"%s class="checkbox" name="%s_%s" />' % (' checked' if checked(row.pk) else '', checkbox_name, row.pk)),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        cell__attrs__class__cj=True,
        query__call_target__attribute='boolean',
        bulk__call_target__attribute='boolean',
    )
    def boolean(cls, is_report=False, call_target=None, **kwargs):
        """
        Shortcut to render booleans as a check mark if true or blank if false.
        """

        def render_icon(value):
            if callable(value):
                value = value()
            return mark_safe('<i class="fa fa-check" title="Yes"></i>') if value else ''

        setdefaults_path(kwargs, dict(
            cell__format=lambda value, **rest: yes_no_formatter(value=value, **rest) if is_report else render_icon(value),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='boolean',
        query__call_target__attribute='boolean_tristate',
    )
    def boolean_tristate(cls, *args, **kwargs):
        call_target = kwargs.pop('call_target', cls)
        return call_target(*args, **kwargs)

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
    @class_shortcut
    def text(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut
    def link(cls, call_target, **kwargs):
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
    @class_shortcut(
        cell__attrs__class__rj=True,
    )
    def number(cls, call_target, **kwargs):
        # Shortcut for rendering a number. Sets the "rj" (as in "right justified") CSS class on the cell and header.
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
        query__gui_op=':',
    )
    def substring(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        query__call_target__attribute='date',
        query__op_to_q_op=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OP_BY_OP[op],
        bulk__call_target__attribute='date',
    )
    def date(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        query__call_target__attribute='datetime',
        query__op_to_q_op=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OP_BY_OP[op],
        bulk__call_target__attribute='datetime',
    )
    def datetime(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        query__call_target__attribute='time',
        query__op_to_q_op=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OP_BY_OP[op],
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
        cell__format=lambda value, **_: ', '.join(['%s' % x for x in value.all()]),
        data_retrieval_method=DataRetrievalMethods.prefetch,
    )
    def many_to_many(cls, call_target, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.remote_field.model.objects.all(),
            bulk__call_target__attribute='many_to_many',
            query__call_target__attribute='many_to_many',
            extra__django_related_field=True,
        )
        kwargs['model'] = model_field.remote_field.model
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice_queryset',
        data_retrieval_method=DataRetrievalMethods.select,
    )
    def foreign_key(cls, call_target, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.foreign_related_fields[0].model.objects.all(),
            model=model_field.foreign_related_fields[0].model,
        )
        return call_target(**kwargs)


class BoundRow(object):
    """
    Internal class used in row rendering
    """

    @dispatch(
        attrs=EMPTY,
        extra=EMPTY,
    )
    def __init__(self, table, row, row_index, template, attrs, extra):
        self.table: Table = table
        self.row: Any = row
        assert not isinstance(self.row, BoundRow)
        self.row_index = row_index
        self.template = template
        self.attrs = attrs
        self.extra = extra

    def render(self):
        if self.template:
            context = dict(bound_row=self, row=self.row, **self.table.context)
            return render_template(self.table.request(), self.template, context)

        return format_html('<tr{}>{}</tr>', self.render_attrs(), self.render_cells())

    @property
    def rendered_attrs(self):
        return self.render_attrs()

    def render_attrs(self):
        attrs = self.attrs.copy()
        attrs['class'] = attrs['class'].copy() if isinstance(attrs['class'], dict) else {k: True for k in attrs['class'].split(' ')}
        pk = getattr(self.row, 'pk', None)
        if pk is not None:
            attrs['data-pk'] = pk
        return render_attrs(attrs)

    def render_cells(self):
        return mark_safe('\n'.join(bound_cell.render() for bound_cell in self))

    def __iter__(self):
        for bound_column in self.table.shown_bound_columns:
            yield BoundCell(bound_row=self, bound_column=bound_column)

    def __getitem__(self, name):
        bound_column = self.table.bound_column_by_name[name]
        return BoundCell(bound_row=self, bound_column=bound_column)


class BoundCell(object):

    def __init__(self, bound_row, bound_column):

        assert bound_column.show

        self.bound_column = bound_column
        self.bound_row = bound_row
        self.table = bound_row.table
        self.row = bound_row.row

    @property
    def value(self):
        if not hasattr(self, '_value'):
            self._value = evaluate_strict(
                self.bound_column.cell.value,
                table=self.bound_row.table,
                declared_column=self.bound_column.declared_column,
                row=self.bound_row.row,
                bound_row=self.bound_row,
                bound_column=self.bound_column,
            )
        return self._value

    @property
    def attrs(self):
        return evaluate_recursive(
            self.bound_column.cell.attrs,
            table=self.table,
            column=self.bound_column,
            row=self.row,
            value=self.value,
        )

    @property
    def url(self):
        url = self.bound_column.cell.url
        if callable(url):
            url = url(table=self.table, column=self.bound_column, row=self.row, value=self.value)
        return url

    @property
    def url_title(self):
        url_title = self.bound_column.cell.url_title
        if callable(url_title):
            url_title = url_title(table=self.table, column=self.bound_column, row=self.row, value=self.value)
        return url_title

    def render(self):
        cell__template = self.bound_column.cell.template
        if cell__template:
            context = dict(table=self.table, bound_column=self.bound_column, bound_row=self.bound_row, row=self.row, value=self.value, bound_cell=self)
            return render_template(self.table.request(), cell__template, context)

        return format_html('<td{}>{}</td>', self.render_attrs(), self.render_cell_contents())

    def render_attrs(self):
        return render_attrs(self.attrs)

    def render_cell_contents(self):
        cell_contents = self.render_formatted()

        url = self.url
        if url:
            url_title = self.url_title
            cell_contents = format_html('<a{}{}>{}</a>',
                                        format_html(' href="{}"', url),
                                        format_html(' title="{}"', url_title) if url_title else '',
                                        cell_contents)
        return cell_contents

    def render_formatted(self):
        return evaluate(self.bound_column.cell.format, table=self.table, column=self.bound_column, row=self.row, value=self.value)

    def __str__(self):
        return self.render()

    def __repr__(self):
        return "<%s column=%s row=%s>" % (self.__class__.__name__, self.bound_column.declared_column, self.bound_row.row)  # pragma: no cover


class TemplateConfig(NamedStruct):
    template = NamedStructField()


class HeaderConfig(NamedStruct):
    attrs = NamedStructField()
    template = NamedStructField()
    extra = NamedStructField()


class RowConfig(NamedStruct):
    attrs = NamedStructField()
    template = NamedStructField()
    extra = NamedStructField()


class Header(object):
    @dispatch(
        attrs=EMPTY,
    )
    def __init__(self, display_name, attrs, template, table, url=None, bound_column=None, number_of_columns_in_group=None, index_in_group=None):
        self.table = table
        self.display_name = mark_safe(display_name)
        self.template = template
        self.url = url
        self.bound_column = bound_column
        self.number_of_columns_in_group = number_of_columns_in_group
        self.index_in_group = index_in_group
        self.attrs = attrs
        evaluate_members(self, ['attrs'], header=self, table=table, bound_column=bound_column)

    @property
    def rendered(self):
        return render_template(self.table.request(), self.template, dict(header=self))

    def render_attrs(self):
        return render_attrs(self.attrs)

    def __repr__(self):
        return '<Header: %s>' % ('superheader' if self.bound_column is None else self.bound_column.name)


@no_copy_on_bind
@declarative(Column, 'columns_dict')
@with_meta
class Table(RefinableObject, PagePart):
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

    name = Refinable()
    bulk_filter: Namespace = Refinable()
    bulk_exclude: Namespace = Refinable()
    sortable = Refinable()
    default_sort_order = Refinable()
    attrs = Refinable()
    template: Union[str, Template] = Refinable()
    row = Refinable()
    filter: Namespace = Refinable()
    header = Refinable()
    model: Type['django.db.models.Model'] = Refinable()
    rows = Refinable()
    column = Refinable()
    bulk: Namespace = Refinable()
    default_child = Refinable()
    extra: Namespace = Refinable()
    endpoint: Namespace = Refinable()
    superheader: Namespace = Refinable()
    paginator: Namespace = Refinable()
    paginator_template: str = Refinable()
    page_size: int = Refinable()
    actions = Refinable()
    actions_template: Union[str, Template] = Refinable()
    member_class = Refinable()
    form_class = Refinable()
    query_class = Refinable()

    class Meta:
        member_class = Column
        form_class = Form
        query_class = Query
        endpoint__tbody = (lambda table, key, value: {'html': table.render(template='tri_table/table_container.html')})

        attrs = {'data-endpoint': lambda table, **_: DISPATCH_PREFIX + path_join(table.path(), 'tbody')}
        query__default_child = True
        query__gui__default_child = True

    def children(self):
        return Struct(
            query=self.query,
            bulk=self.bulk,

            # TODO: should be a PagePart?
            columns=Struct(
                name='columns',
                children=lambda: self.bound_column_by_name,
            ),
            # TODO: this can have name collisions with the keys above
            **setup_endpoint_proxies(self.endpoint)
        )

    def endpoint_kwargs(self):
        return dict(table=self)

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
        column=EMPTY,
        bulk_filter={},
        bulk_exclude={},
        sortable=True,
        default_sort_order=None,
        attrs=EMPTY,
        attrs__class__listview=True,
        template='iommi/table/list.html',
        row__attrs__class=EMPTY,
        row__template=None,
        filter__template='iommi/query/form.html',  # tri.query dependency, see render_filter() below.
        header__template='iommi/table/table_header_rows.html',
        paginator_template='iommi/table/paginator.html',
        paginator__call_target=Paginator,

        # TODO: actions should be action
        action=EMPTY,
        actions_template='iommi/form/actions.html',
        query=EMPTY,
        bulk=EMPTY,
        page_size=DEFAULT_PAGE_SIZE,

        extra=EMPTY,

        superheader__attrs__class__superheader=True,
        superheader__template='iommi/table/header.html',
    )
    def __init__(self, *, request=None, columns=None, columns_dict=None, model=None, rows=None, filter=None, column=None, bulk=None, header=None, query=None, row=None, instance=None, action=None, actions=None, default_child=None, **kwargs):
        """
        :param rows: a list or QuerySet of objects
        :param columns: (use this only when not using the declarative style) a list of Column objects
        :param attrs: dict of strings to string/callable of HTML attributes to apply to the table
        :param row__attrs: dict of strings to string/callable of HTML attributes to apply to the row. Callables are passed the row as argument.
        :param row__template: name of template (or `Template` object) to use for rendering the row
        :param bulk_filter: filters to apply to the QuerySet before performing the bulk operation
        :param bulk_exclude: exclude filters to apply to the QuerySet before performing the bulk operation
        :param sortable: set this to false to turn off sorting for all columns
        """

        model, rows = model_and_rows(model, rows)

        self._action = {}
        # TODO: Action class here should be self.get_meta().SOMETHING_class,
        self.declared_actions = collect_members(items=actions, item=action, cls=Action, store_config=self._action)

        self._column = {}

        def generate_columns():
            if columns is not None:
                for column_ in columns:
                    self._column[column_.name] = column.get(column_.name, {})
                    yield column_
            for name, column_ in columns_dict.items():
                column_.name = name
                self._column[column_.name] = column.get(column_.name, {})
                yield column_
            for name, column_spec in column.items():
                column_spec = setdefaults_path(
                    Namespace(),
                    column_spec,
                    call_target=self.get_meta().member_class,
                    name=name,
                )
                yield column_spec()

        # TODO: use collect_members and bind_members
        columns = sort_after(list(generate_columns()))

        assert len(columns) > 0, 'columns must be specified. It is only set to None to make linting tools not give false positives on the declarative style'

        self.columns: List[Column] = columns

        self.instance = instance

        super(Table, self).__init__(
            model=model,
            rows=rows,
            filter=TemplateConfig(**filter),
            header=HeaderConfig(**header),
            row=RowConfig(**row),
            bulk=bulk,
            column=column,
            **kwargs
        )

        self.default_child = default_child

        self._actions = actions

        self.query_args = query
        self._query: Query = None
        self._query_form: Form = None
        self._query_error: List[str] = None

        self._bulk_form: Form = None
        self._bound_columns: List[Column] = None
        self._shown_bound_columns: List[Column] = None
        self._bound_column_by_name: Dict[str, Column] = None
        self._has_prepared: bool = False
        self.header_levels = None

        if request is not None:
            self.bind(request=request)

    def render_actions(self):
        actions, grouped_actions = group_actions(self.actions)
        return render_template(
            self.request(),
            self.actions_template,
            dict(
                actions=actions,
                grouped_actions=grouped_actions,
                table=self,
            ))

    def render_header(self):
        return render_template(self.request(), self.header.template, self.context)

    def render_filter(self):
        if not self.query_form:
            return ''
        return render_template(self.request(), self.filter.template, merged(self.context, form=self.query_form))

    def _prepare_auto_rowspan(self):
        auto_rowspan_columns = [column for column in self.shown_bound_columns if column.auto_rowspan]

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

                orig_style = column.cell.attrs.get('style')

                def rowspan(row, **_):
                    return rowspan_by_row[id(row)] if id(row) in rowspan_by_row else None

                def style(row, **_):
                    return 'display: none%s' % ('; ' + orig_style if orig_style else '') if id(row) not in rowspan_by_row else orig_style

                assert 'rowspan' not in column.cell.attrs
                dict.__setitem__(column.cell.attrs, 'rowspan', rowspan)
                dict.__setitem__(column.cell.attrs, 'style', style)

    def _prepare_sorting(self):
        request = self.request()
        if request is None:
            return

        order = request.GET.get(path_join(self.path(), 'order'), self.default_sort_order)
        if order is not None:
            is_desc = order[0] == '-'
            order_field = is_desc and order[1:] or order
            tmp = [x for x in self._shown_bound_columns if x.name == order_field]
            if len(tmp) == 0:
                return  # Unidentified sort column
            sort_column = tmp[0]
            order_args = evaluate(sort_column.sort_key, column=sort_column)
            order_args = isinstance(order_args, list) and order_args or [order_args]

            if sort_column.sortable:
                if isinstance(self.rows, list):
                    order_by_on_list(self.rows, order_args[0], is_desc)
                else:
                    if not settings.DEBUG:
                        # We should crash on invalid sort commands in DEV, but just ignore in PROD
                        # noinspection PyProtectedMember
                        valid_sort_fields = {x.name for x in self.model._meta.get_fields()}
                        order_args = [order_arg for order_arg in order_args if order_arg.split('__', 1)[0] in valid_sort_fields]
                    order_args = ["%s%s" % (is_desc and '-' or '', x) for x in order_args]
                    self.rows = self.rows.order_by(*order_args)

    def _prepare_headers(self):
        prepare_headers(self, self.shown_bound_columns)

        for bound_column in self._bound_columns:
            evaluate_members(
                bound_column,
                [
                    'superheader',
                    'header',
                ],
                table=self,
                column=bound_column.declared_column,
                bound_column=bound_column,
            )

        superheaders = []
        subheaders = []

        # The id(header) and stuff is to make None not be equal to None in the grouping
        for _, group_iterator in groupby(self._shown_bound_columns, key=lambda header: header.group or id(header)):
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

            for i, bound_column in enumerate(columns_in_group):
                subheaders.append(
                    Header(
                        display_name=bound_column.display_name,
                        table=self,
                        attrs=bound_column.header.attrs,
                        template=bound_column.header.template,
                        url=bound_column.url,
                        bound_column=bound_column,
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

    @property
    def query(self) -> Query:
        assert self._is_bound
        return self._query

    @property
    def query_form(self) -> Form:
        assert self._is_bound
        return self._query_form

    @property
    def query_error(self) -> List[str]:
        assert self._is_bound
        return self._query_error

    @property
    def bulk_form(self) -> Form:
        assert self._is_bound
        return self._bulk_form

    @property
    def bound_columns(self) -> List[Column]:
        assert self._is_bound
        return self._bound_columns

    @property
    def shown_bound_columns(self) -> List[Column]:
        assert self._is_bound
        return self._shown_bound_columns

    @property
    def bound_column_by_name(self) -> Dict[str, Column]:
        assert self._is_bound
        return self._bound_column_by_name

    def on_bind(self) -> None:
        if self._has_prepared:
            return

        self.actions = bind_members(unbound_items=self.declared_actions, cls=Action, parent=self, table=self)

        def bind_columns():
            for column in self.columns:
                bound_column = column.bind(parent=self)
                bound_column._evaluate()
                yield bound_column

        # TODO: use collect_members and bind_members
        self._bound_columns = list(bind_columns())
        self._bound_column_by_name = OrderedDict((bound_column.name, bound_column) for bound_column in self._bound_columns)

        self._has_prepared = True
        self._is_bound = True

        self._shown_bound_columns = [bound_column for bound_column in self._bound_columns if bound_column.show]

        evaluate_members(self, ['sortable'], table=self)  # needs to be done first because _prepare_headers depends on it
        self._prepare_sorting()

        for bound_column in self._shown_bound_columns:
            # special case for entire table not sortable
            if not self.sortable:
                bound_column.sortable = False

        self._prepare_headers()
        evaluate_members(
            self,
            [
                'column',
                'bulk_filter',
                'bulk_exclude',
                'attrs',
                'row',
                'filter',
                'model',
                '_query',
                'bulk',
            ],
            table=self,
        )

        if self.model:

            def generate_variables():
                for column in self._bound_columns:
                    if column.query.show:
                        query_namespace = setdefaults_path(
                            Namespace(),
                            column.query,
                            call_target__cls=self.get_meta().query_class.get_meta().member_class,
                            model=self.model,
                            name=column.name,
                            attr=column.attr,
                            gui__display_name=column.display_name,
                            gui__call_target__cls=self.get_meta().query_class.get_meta().form_class.get_meta().member_class,
                        )
                        if 'call_target' not in query_namespace['call_target'] and query_namespace['call_target'].get(
                                'attribute') == 'from_model':
                            query_namespace['field_name'] = column.attr
                        yield query_namespace()

            variables = list(generate_variables())

            self._query = self.get_meta().query_class(
                variables=variables,
                **self.query_args
            )
            self._query.bind(parent=self)
            self._query_form = self._query.form if self._query.variables else None

            self._query_error = ''
            if self._query_form:
                try:
                    q = self.query.to_q()
                    if q:
                        self.rows = self.rows.filter(q)
                except QueryException as e:
                    self._query_error = str(e)

            def generate_bulk_fields():
                for column in self._bound_columns:
                    if column.bulk.show:
                        bulk_namespace = setdefaults_path(
                            Namespace(),
                            column.bulk,
                            call_target__cls=self.get_meta().form_class.get_meta().member_class,
                            model=self.model,
                            name=column.name,
                            attr=column.attr,
                            display_name=column.display_name,
                            required=False,
                            empty_choice_tuple=(None, '', '---', True),
                        )
                        if 'call_target' not in bulk_namespace['call_target'] and bulk_namespace['call_target'].get('attribute') == 'from_model':
                            bulk_namespace['field_name'] = column.attr
                        yield bulk_namespace()

            bulk_fields = list(generate_bulk_fields())
            if bulk_fields:
                bulk_fields.append(self.get_meta().form_class.get_meta().member_class.hidden(name='_all_pks_', attr=None, initial='0', required=False, template='iommi/form/input.html'))

                self._bulk_form = self.get_meta().form_class(
                    fields=bulk_fields,
                    name='bulk',
                    **self.bulk
                )
                self._bulk_form.bind(parent=self)
            else:
                self._bulk_form = None

        if isinstance(self.rows, QuerySet):
            prefetch = [x.attr for x in self.shown_bound_columns if x.data_retrieval_method == DataRetrievalMethods.prefetch and x.attr]
            select = [x.attr for x in self.shown_bound_columns if x.data_retrieval_method == DataRetrievalMethods.select and x.attr]
            if prefetch:
                self.rows = self.rows.prefetch_related(*prefetch)
            if select:
                self.rows = self.rows.select_related(*select)

        self._prepare_auto_rowspan()

    def bound_rows(self):
        return self

    def __iter__(self):
        assert self._is_bound
        for i, row in enumerate(self.preprocess_rows(rows=self.rows, table=self)):
            row = self.preprocess_row(table=self, row=row)
            yield BoundRow(table=self, row=row, row_index=i, **evaluate_recursive(self.row, table=self, row=row))

    def render_attrs(self):
        attrs = self.attrs.copy()
        return render_attrs(attrs)

    def render_tbody(self):
        return mark_safe('\n'.join([bound_row.render() for bound_row in self.bound_rows()]))

    def paginator_context(self, adjacent_pages=6):
        context = self.context.copy()
        page = context["page"]
        assert page != 0  # pages are 1-indexed!
        if page <= adjacent_pages:
            page = adjacent_pages + 1
        elif page > context["pages"] - adjacent_pages:
            page = context["pages"] - adjacent_pages
        page_numbers = [
            n for n in
            range(page - adjacent_pages, page + adjacent_pages + 1)
            if 0 < n <= context["pages"]
        ]

        get = context['request'].GET.copy() if 'request' in context else {}
        if 'page' in get:
            del get['page']

        return merged(context, dict(
            extra=get and (get.urlencode() + "&") or "",
            page_numbers=page_numbers,
            show_first=1 not in page_numbers,
            show_last=context["pages"] not in page_numbers,
            show_hits=context["show_hits"],
            hit_label=context["hit_label"],
        ))

    def render_paginator(self, adjacent_pages=6):
        return render_template(request=self.request(), template=self.paginator_template, context=self.paginator_context(adjacent_pages=adjacent_pages))

    @classmethod
    @dispatch(
        column=EMPTY,
    )
    def columns_from_model(cls, column, **kwargs):
        return create_members_from_model(
            member_params_by_member_name=column,
            default_factory=cls.get_meta().member_class.from_model,
            **kwargs
        )

    @classmethod
    @dispatch(
        column=EMPTY,
    )
    def from_model(cls, rows=None, model=None, column=None, instance=None, include=None, exclude=None, extra_columns=None, **kwargs):
        """
        Create an entire form based on the columns of a model. To override a column parameter send keyword arguments in the form
        of "the_name_of_the_column__param". For example:

        .. code:: python

            class Foo(Model):
                foo = IntegerField()

            Table.from_model(request=request, model=Foo, column__foo__help_text='Overridden help text')

        :param include: columns to include. Defaults to all
        :param exclude: columns to exclude. Defaults to none (except that AutoField is always excluded!)

        """
        model, rows = model_and_rows(model, rows)
        assert model is not None or rows is not None, "model or rows must be specified"
        columns = cls.columns_from_model(model=model, include=include, exclude=exclude, extra=extra_columns, column=column)
        return cls(rows=rows, model=model, instance=instance, columns=columns, **kwargs)

    def bulk_queryset(self):
        queryset = self.model.objects.all() \
            .filter(**self.bulk_filter) \
            .exclude(**self.bulk_exclude)

        if self.request().POST.get('_all_pks_') == '1':
            return queryset
        else:
            pks = [key[len('pk_'):] for key in self.request().POST if key.startswith('pk_')]
            return queryset.filter(pk__in=pks)

    @dispatch(
        render=render_template,
        context=EMPTY,
    )
    def render(self, *, context=None, render=None):
        assert self._is_bound

        if not context:
            context = {}

        context['bulk_form'] = self.bulk_form
        context['query_form'] = self.query_form
        context['iommi_query_error'] = self.query_error

        request = self.request()
        if self.bulk_form and request.method == 'POST':
            if self.bulk_form.is_valid():
                queryset = self.bulk_queryset()

                updates = {
                    field.name: field.value
                    for field in self.bulk_form.fields
                    if field.value is not None and field.value != '' and field.attr is not None
                }
                queryset.update(**updates)

                self.post_bulk_edit(table=self, queryset=queryset, updates=updates)

                return HttpResponseRedirect(request.META['HTTP_REFERER'])

        self.context = table_context(
            request,
            table=self,
            extra_context=context,
            paginator=self.paginator,
        )
        if self.query_form and not self.query_form.is_valid():
            self.rows = None
            self.context['invalid_form_message'] = mark_safe('<i class="fa fa-meh-o fa-5x" aria-hidden="true"></i>')

        return render(request=request, template=self.template, context=self.context)

    @classmethod
    @class_shortcut(
        part=EMPTY,
        call_target__attribute='from_model',
        extra__model_verbose_name=None,
        extra__title=None,
    )
    def as_page(cls, *, call_target=None, model=None, part=None, extra=None, rows=None, **kwargs):
        if model is None and isinstance(rows, QuerySet):
            model = rows.model

        if model and extra.model_verbose_name is None:
            # noinspection PyProtectedMember
            extra.model_verbose_name = model._meta.verbose_name_plural.replace('_', ' ').capitalize()

        if extra.title is None:
            extra.title = extra.model_verbose_name

        # TODO: move import?
        from iommi.page import (
            Page,
            html,
        )
        return Page(
            part__title=html.h1(extra.title, **part.pop('title', {})),
            part__table=call_target(extra=extra, model=model, default_child=True, **kwargs),
            part=part,
            default_child=True,
        )


def table_context(request, *, table: Table, extra_context, paginator: Namespace):
    if extra_context is None:
        extra_context = {}

    assert table.rows is not None

    base_context = {
        'table': table,
    }

    if table.page_size:
        try:
            table.page_size = int(request.GET.get('page_size', table.page_size)) if request else table.page_size
        except ValueError:
            pass
        paginator = paginator(table.rows, table.page_size)
        page = request.GET.get('page') if request else None  # None is translated to the default page in paginator.get_page
        try:
            page_obj = paginator.get_page(page)
            table.rows = page_obj.object_list
        except (InvalidPage, ValueError):
            raise Http404

        base_context.update({
            'request': request,
            'is_paginated': paginator.num_pages > 1,
            'results_per_page': table.page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'next': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'page': page_obj.number,
            'pages': paginator.num_pages,
            'hits': paginator.count,

            # TODO: remove these, remember the template
            'show_hits': False,
            'hit_label': 'Items',
        })
    else:
        base_context.update({
            'is_paginated': False,
        })

    base_context.update(extra_context)
    return base_context
