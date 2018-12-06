# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import copy
import warnings
from collections import OrderedDict
from functools import total_ordering
from itertools import groupby

from tri.form.render import render_attrs, render_class

from django.conf import settings
from django.core.paginator import Paginator, InvalidPage
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe
from django.db.models import QuerySet
import six
from tri.declarative import declarative, creation_ordered, with_meta, evaluate_recursive, evaluate, getattr_path, sort_after, LAST, setdefaults_path, dispatch, EMPTY, Namespace, setattr_path, RefinableObject, refinable, Refinable, shortcut, Shortcut
from tri.form import Field, Form, member_from_model, expand_member, create_members_from_model, render_template, handle_dispatch, DISPATCH_PATH_SEPARATOR, evaluate_and_group_links
from tri.named_struct import NamedStructField, NamedStruct
from tri.struct import Struct, merged
from tri.query import Query, Variable, QueryException, Q_OP_BY_OP
from tri.form import Link as tri_form_Link

from tri.table.db_compat import setup_db_compat

__version__ = '6.0.3'  # pragma: no mutate

LAST = LAST

_column_factory_by_field_type = OrderedDict()


def register_column_factory(field_class, factory):
    _column_factory_by_field_type[field_class] = factory


def _with_path_prefix(table, name):
    if table.name:
        return DISPATCH_PATH_SEPARATOR.join([table.name, name])
    else:
        return name


def prepare_headers(table, bound_columns):
    """
    :type bound_columns: list of BoundColumn
    """
    if table.request is None:
        return

    for column in bound_columns:
        if column.sortable:
            params = table.request.GET.copy()
            param_path = _with_path_prefix(table, 'order')
            order = table.request.GET.get(param_path, None)
            start_sort_desc = column.sort_default_desc
            params[param_path] = column.name if not start_sort_desc else '-' + column.name
            if order is not None:
                is_desc = len(order) > 0 and order[0] == '-'
                order_field = is_desc and order[1:] or order
                if order_field == column.name:
                    new_order = is_desc and order[1:] or "-%s" % order
                    params[param_path] = new_order
            column.is_sorting = False if order is None else (column.name == order or ('-' + column.name) == order)
            column.url = "?%s" % params.urlencode()
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
    assert False, "Unable to convert {} to Yes/No".format(value)   # pragma: no cover  # pragma: no mutate


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


def default_cell_formatter(table, column, row, value, **_):
    """
    :type column: tri.table.Column
    """
    formatter = _cell_formatters.get(type(value))
    if formatter:
        value = formatter(table=table, column=column, row=row, value=value)

    if value is None:
        return ''

    return conditional_escape(value)


@creation_ordered
class Column(RefinableObject):
    """
    Class that describes a column, i.e. the text of the header, how to get and display the data in the cell, etc.
    """
    name = Refinable()
    after = Refinable()
    attrs = Refinable()
    url = Refinable()
    title = Refinable()
    show = Refinable()
    sort_default_desc = Refinable()
    sortable = Refinable()
    group = Refinable()
    auto_rowspan = Refinable()
    cell = Refinable()
    model = Refinable()
    model_field = Refinable()
    choices = Refinable()
    bulk = Refinable()
    query = Refinable()
    extra = Refinable()

    @dispatch(
        show=True,
        sort_default_desc=False,
        sortable=True,
        auto_rowspan=False,
        bulk__show=False,
        query__show=False,
        attrs=EMPTY,
        attrs__class=EMPTY,
        cell__template=None,
        cell__attrs=EMPTY,
        cell__value=lambda table, column, row, **_: getattr_path(row, evaluate(column.attr, table=table, column=column)),
        cell__format=default_cell_formatter,
        cell__url=None,
        cell__url_title=None,
        extra=EMPTY,
    )
    def __init__(self, **kwargs):
        """
        :param name: the name of the column
        :param attr: What attribute to use, defaults to same as name. Follows django conventions to access properties of properties, so "foo__bar" is equivalent to the python code `foo.bar`. This parameter is based on the variable name of the Column if you use the declarative style of creating tables.
        :param display_name: the text of the header for this column. By default this is based on the `name` parameter so normally you won't need to specify it.
        :param css_class: CSS class of the header
        :param url: URL of the header. This should only be used if "sorting" is off.
        :param title: title/tool tip of header
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

        setdefaults_path(kwargs, {'attrs__class__' + c: True for c in kwargs.pop('css_class', {})})

        super(Column, self).__init__(**kwargs)

        self.table = None
        """ :type: Table """
        self.column = None
        """ :type: Column """
        self.index = None
        """ :type: int """
        self.is_sorting = None
        """ :type: bool """

    def __repr__(self):
        return '<{}.{} {}>'.format(self.__class__.__module__, self.__class__.__name__, self.name)

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

    def _bind(self, table, index):
        bound_column = copy.copy(self)
        bound_column.attrs = Namespace(self.attrs.copy())
        bound_column.attrs['class'] = Namespace(bound_column.attrs['class'].copy())

        bound_column.index = index
        bound_column.bulk = setdefaults_path(
            Struct(),
            self.bulk,
            attr=self.attr,
        )
        bound_column.query = setdefaults_path(
            Struct(),
            self.query,
            attr=self.attr,
        )

        for k, v in table.column.get(bound_column.name, {}).items():
            setattr_path(bound_column, k, v)
        bound_column.table = table
        bound_column.column = self

        return bound_column

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

    def render_css_class(self):
        return render_class(self.attrs['class'])

    @staticmethod
    def from_model(model, field_name=None, model_field=None, **kwargs):
        return member_from_model(
            model=model,
            factory_lookup=_column_factory_by_field_type,
            factory_lookup_register_function=register_column_factory,
            field_name=field_name,
            model_field=model_field,
            defaults_factory=lambda model_field: {},
            **kwargs)

    @staticmethod
    def expand_member(model, field_name=None, model_field=None, **kwargs):
        return expand_member(
            model=model,
            factory_lookup=_column_factory_by_field_type,
            field_name=field_name,
            model_field=model_field,
            **kwargs)


@shortcut
@dispatch(
    call_target=Column,
    name='',
    display_name='',
    sortable=False,
    attrs__class__thin=True,
    cell__value=lambda table, column, row, **_: True,
    cell__attrs__class__cj=True,
)
def column_shortcut_icon(icon, is_report=False, icon_title='', show=True, call_target=None, **kwargs):
    """
    Shortcut to create font awesome-style icons.

    :param icon: the font awesome name of the icon
    """
    setdefaults_path(kwargs, dict(
        show=lambda table, **rest: evaluate(show, table=table, **rest) and not is_report,
        title=icon_title,
        cell__format=lambda value, **_: mark_safe('<i class="fa fa-lg fa-%s"%s></i>' % (icon, ' title="%s"' % icon_title if icon_title else '')) if value else ''
    ))
    return call_target(**kwargs)


Column.icon = staticmethod(column_shortcut_icon)


@shortcut
@dispatch(
    call_target=Column.icon,
    cell__url=lambda row, **_: row.get_absolute_url() + 'edit/',
    display_name=''
)
def column_shortcut_edit(is_report=False, call_target=None, **kwargs):
    """
    Shortcut for creating a clickable edit icon. The URL defaults to `your_object.get_absolute_url() + 'edit/'`. Specify the option cell__url to override.
    """
    return call_target('pencil-square-o', is_report, 'Edit', **kwargs)


Column.edit = staticmethod(column_shortcut_edit)


@shortcut
@dispatch(
    call_target=Column.icon,
    cell__url=lambda row, **_: row.get_absolute_url() + 'delete/',
    display_name=''
)
def column_shortcut_delete(is_report=False, call_target=None, **kwargs):
    """
    Shortcut for creating a clickable delete icon. The URL defaults to `your_object.get_absolute_url() + 'delete/'`. Specify the option cell__url to override.
    """
    return call_target('trash-o', is_report, 'Delete', **kwargs)


Column.delete = staticmethod(column_shortcut_delete)


@shortcut
@dispatch(
    call_target=Column.icon,
    cell__url=lambda row, **_: row.get_absolute_url() + 'download/',
    cell__value=lambda row, **_: getattr(row, 'pk', False),
)
def column_shortcut_download(is_report=False, call_target=None, **kwargs):
    """
    Shortcut for creating a clickable download icon. The URL defaults to `your_object.get_absolute_url() + 'download/'`. Specify the option cell__url to override.
    """
    return call_target('download', is_report, 'Download', **kwargs)


Column.download = staticmethod(column_shortcut_download)


@shortcut
@dispatch(
    call_target=Column,
    name='',
    title='Run',
    sortable=False,
    css_class={'thin'},
    cell__url=lambda row, **_: row.get_absolute_url() + 'run/',
    cell__value='Run',
)
def column_shortcut_run(is_report=False, show=True, call_target=None, **kwargs):
    """
    Shortcut for creating a clickable run icon. The URL defaults to `your_object.get_absolute_url() + 'run/'`. Specify the option cell__url to override.
    """
    setdefaults_path(kwargs, dict(
        show=lambda table, **rest: evaluate(show, table=table, **rest) and not is_report,
    ))
    return call_target(**kwargs)


Column.run = staticmethod(column_shortcut_run)


SELECT_DISPLAY_NAME = '<i class="fa fa-check-square-o" onclick="tri_table_js_select_all(this)"></i>'


@shortcut
@dispatch(
    call_target=Column,
    name='__select__',
    title='Select all',
    display_name=mark_safe(SELECT_DISPLAY_NAME),
    sortable=False,
    attrs__class__thin=True,
    attrs__class__nopad=True,
    cell__attrs__class__cj=True,
)
def column_shortcut_select(is_report=False, checkbox_name='pk', show=True, checked=lambda x: False, call_target=None, **kwargs):
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


Column.select = staticmethod(column_shortcut_select)


@shortcut
@dispatch(
    call_target=Column,
    cell__attrs__class__cj=True,
    query__call_target=Variable.boolean,
    bulk__call_target=Field.boolean,
)
def column_shortcut_boolean(is_report=False, call_target=None, **kwargs):
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


Column.boolean = staticmethod(column_shortcut_boolean)
Column.boolean_tristate = Shortcut(
    query__call_target=Variable.boolean_tristate,
    call_target=Column.boolean,
)


@shortcut
@dispatch(
    call_target=Column,
    bulk__call_target=Field.choice,
    query__call_target=Variable.choice,
)
def column_shortcut_choice(call_target, **kwargs):
    choices = kwargs['choices']
    setdefaults_path(kwargs, dict(
        bulk__choices=choices,
        query__choices=choices,
    ))
    return call_target(**kwargs)


Column.choice = staticmethod(column_shortcut_choice)


@shortcut
@dispatch(
    call_target=Column.choice,
    bulk__call_target=Field.choice_queryset,
    query__call_target=Variable.choice_queryset,
)
def column_shortcut_choice_queryset(call_target, **kwargs):
    setdefaults_path(kwargs, dict(
        bulk__model=kwargs.get('model'),
        query__model=kwargs.get('model'),
    ))
    return call_target(**kwargs)


Column.choice_queryset = staticmethod(column_shortcut_choice_queryset)


@shortcut
@dispatch(
    call_target=Column.choice,
    bulk__call_target=Field.multi_choice_queryset,
    query__call_target=Variable.multi_choice_queryset,
    cell__format=lambda value, **_: ', '.join(['%s' % x for x in value.all()]),
)
def column_shortcut_multi_choice_queryset(call_target, **kwargs):
    setdefaults_path(kwargs, dict(
        bulk__model=kwargs.get('model'),
        query__model=kwargs.get('model'),
    ))
    return call_target(**kwargs)


Column.multi_choice_queryset = staticmethod(column_shortcut_multi_choice_queryset)

Column.text = Shortcut(
    call_target=Column,
)


# Shortcut for creating a cell that is a link. The URL is the result of calling `get_absolute_url()` on the object.
def link_cell_url(table, column, row, value):
    del table, value
    r = getattr_path(row, column.attr)
    return r.get_absolute_url() if r else ''


Column.link = Shortcut(
    call_target=Column,
    cell__url=link_cell_url,
)

# Shortcut for rendering a number. Sets the "rj" (as in "right justified") CSS class on the cell and header.
Column.number = Shortcut(
    call_target=Column,
    cell__attrs__class__rj=True,
)

Column.float = Shortcut(
    call_target=Column.number,
    query__call_target=Variable.float,
    bulk__call_target=Field.float,
)

Column.integer = Shortcut(
    call_target=Column.number,
    query__call_target=Variable.integer,
    bulk__call_target=Field.integer,
)

Column.substring = Shortcut(
    call_target=Column,
    query__gui_op=':',
)

Column.date = Shortcut(
    call_target=Column,
    query__call_target=Variable.date,
    query__op_to_q_op=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OP_BY_OP[op],
    bulk__call_target=Field.date,
)

Column.datetime = Shortcut(
    call_target=Column,
    query__call_target=Variable.datetime,
    query__op_to_q_op=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OP_BY_OP[op],
    bulk__call_target=Field.datetime,
)

Column.time = Shortcut(
    call_target=Column,
    query__call_target=Variable.time,
    query__op_to_q_op=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OP_BY_OP[op],
    bulk__call_target=Field.time,
)

Column.email = Shortcut(
    call_target=Column,
    query__call_target=Variable.email,
    bulk__call_target=Field.email,
)

Column.decimal = Shortcut(
    call_target=Column,
    bulk__call_target=Field.decimal,
    query__call_target=Variable.decimal,
)


class BoundRow(object):
    """
    Internal class used in row rendering
    """

    @dispatch(
        attrs=EMPTY,
        extra=EMPTY,
    )
    def __init__(self, table, row, row_index, template, attrs, extra):
        self.table = table
        """ :type : Table """
        self.row = row
        """ :type : object """
        self.row_index = row_index
        self.template = template
        self.attrs = attrs
        self.extra = extra

    def render(self):
        if self.template:
            context = dict(bound_row=self, row=self.row, **self.table.context)
            return render_template(self.table.request, self.template, context)

        return format_html('<tr{}>{}</tr>', self.render_attrs(), self.render_cells())

    def render_attrs(self):
        attrs = self.attrs.copy()
        attrs['class'] = attrs['class'].copy() if isinstance(attrs['class'], dict) else {k: True for k in attrs['class'].split(' ')}
        attrs['class'].setdefault('row%s' % (self.row_index % 2 + 1), True)
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


@python_2_unicode_compatible
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
            self._value = evaluate(self.bound_column.cell.value, table=self.bound_row.table, column=self.bound_column.column, row=self.bound_row.row, bound_row=self.bound_row, bound_column=self.bound_column)
        return self._value

    @property
    def attrs(self):
        return evaluate_recursive(self.bound_column.cell.attrs, table=self.table, column=self.bound_column, row=self.row, value=self.value)

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
            return render_template(self.table.request, cell__template, context)

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
        return "<%s column=%s row=%s>" % (self.__class__.__name__, self.bound_column.column, self.bound_row.row)  # pragma: no cover


class TemplateConfig(NamedStruct):
    template = NamedStructField()


class RowConfig(NamedStruct):
    attrs = NamedStructField()
    template = NamedStructField()
    extra = NamedStructField()


@declarative(Column, 'columns_dict')
@with_meta
class Table(RefinableObject):

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
    bulk_filter = Refinable()
    """ :type: tri.declarative.Namespace """
    bulk_exclude = Refinable()
    """ :type: tri.declarative.Namespace """
    sortable = Refinable()
    default_sort_order = Refinable()
    attrs = Refinable()
    row = Refinable()
    filter = Refinable()
    header = Refinable()
    links = Refinable()
    model = Refinable()
    column = Refinable()
    bulk = Refinable()
    endpoint_dispatch_prefix = Refinable()
    extra = Refinable()
    """ :type: tri.declarative.Namespace """
    endpoint = Refinable()

    @staticmethod
    @refinable
    def preprocess_data(data, **_):
        return data

    @staticmethod
    @refinable
    def preprocess_row(table, row, **_):
        del table
        return row

    @dispatch(
        column=EMPTY,
        bulk_filter={},
        bulk_exclude={},
        sortable=True,
        default_sort_order=None,
        attrs=EMPTY,
        attrs__class__listview=True,
        row__attrs__class=EMPTY,
        row__template=None,
        filter__template='tri_query/form.html',  # tri.query dependency, see render_filter() below.
        header__template='tri_table/table_header_rows.html',
        links__template='tri_form/links.html',
        model=None,
        query=EMPTY,
        bulk=EMPTY,

        endpoint_dispatch_prefix=None,
        endpoint__query=lambda table, key, value: table.query.endpoint_dispatch(key=key, value=value) if table.query is not None else None,
        endpoint__bulk=lambda table, key, value: table.bulk_form.endpoint_dispatch(key=key, value=value) if table.bulk is not None else None,

        extra=EMPTY,
    )
    def __init__(self, data=None, request=None, columns=None, columns_dict=None, model=None, filter=None, column=None, bulk=None, header=None, query=None, row=None, instance=None, links=None, **kwargs):
        """
        :param data: a list or QuerySet of objects
        :param columns: (use this only when not using the declarative style) a list of Column objects
        :param attrs: dict of strings to string/callable of HTML attributes to apply to the table
        :param row__attrs: dict of strings to string/callable of HTML attributes to apply to the row. Callables are passed the row as argument.
        :param row__template: name of template (or `Template` object) to use for rendering the row
        :param bulk_filter: filters to apply to the QuerySet before performing the bulk operation
        :param bulk_exclude: exclude filters to apply to the QuerySet before performing the bulk operation
        :param sortable: set this to false to turn off sorting for all columns
        """

        if data is None:  # pragma: no cover
            assert model is not None
            data = model.objects.all()

        if isinstance(data, QuerySet):
            model = data.model

        def generate_columns():
            for column_ in columns if columns is not None else []:
                yield column_
            for name, column_ in columns_dict.items():
                column_.name = name
                yield column_
        columns = sort_after(list(generate_columns()))

        assert len(columns) > 0, 'columns must be specified. It is only set to None to make linting tools not give false positives on the declarative style'

        self.data = data
        self.request = request
        self.columns = columns
        """ :type : list of Column """

        self.instance = instance

        super(Table, self).__init__(
            model=model,
            filter=TemplateConfig(**filter),
            links=TemplateConfig(**links),
            header=TemplateConfig(**header),
            row=RowConfig(**row),
            bulk=bulk,
            column=column,
            **kwargs
        )

        self.query_args = query
        self._query = None
        """ :type : tri.query.Query """
        self._query_form = None
        """ :type : tri.form.Form """
        self._query_error = None
        """ :type : list of str """

        self._bulk_form = None
        """ :type : tri.form.Form """
        self._bound_columns = None
        """ :type : list of Column """
        self._shown_bound_columns = None
        """ :type : list of Column """
        self._bound_column_by_name = None
        """ :type: dict[str, Column] """
        self._has_prepared = False
        """ :type: bool """
        self.header_levels = None

    def render_links(self):
        return render_template(self.request, self.links.template, self.context)

    def render_header(self):
        return render_template(self.request, self.header.template, self.context)

    def render_filter(self):
        if not self.query_form:
            return ''
        return render_template(self.request, self.filter.template, merged(self.context, form=self.query_form))

    def _prepare_auto_rowspan(self):
        auto_rowspan_columns = [column for column in self.shown_bound_columns if column.auto_rowspan]

        if auto_rowspan_columns:
            self.data = list(self.data)
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

    def _prepare_evaluate_members(self):
        self._shown_bound_columns = [bound_column for bound_column in self._bound_columns if bound_column.show]

        for attr in (
            'column',
            'bulk_filter',
            'bulk_exclude',
            'sortable',
            'attrs',
            'row',
            'filter',
            'header',
            'links',
            'model',
            '_query',
            'bulk',
            'endpoint',
        ):
            setattr(self, attr, evaluate_recursive(getattr(self, attr), table=self))

        if not self.sortable:
            for bound_column in self._bound_columns:
                bound_column.sortable = False

    def _prepare_sorting(self):
        if self.request is None:
            return

        order = self.request.GET.get(_with_path_prefix(self, 'order'), self.default_sort_order)
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
                if isinstance(self.data, list):
                    order_by_on_list(self.data, order_args[0], is_desc)
                else:
                    if not settings.DEBUG:
                        # We should crash on invalid sort commands in DEV, but just ignore in PROD
                        # noinspection PyProtectedMember
                        valid_sort_fields = {x.name for x in self.model._meta.get_fields()}
                        order_args = [order_arg for order_arg in order_args if order_arg.split('__', 1)[0] in valid_sort_fields]
                    order_args = ["%s%s" % (is_desc and '-' or '', x) for x in order_args]
                    self.data = self.data.order_by(*order_args)

    def _prepare_headers(self):
        prepare_headers(self, self.shown_bound_columns)
        # The id(header) and the type(x.display_name) stuff is to make None not be equal to None in the grouping
        group_columns = []

        class GroupColumn(Struct):
            def render_css_class(self):
                return render_class(self.attrs['class'])

        for group_name, group_iterator in groupby(self._shown_bound_columns, key=lambda header: header.group or id(header)):

            columns_in_group = list(group_iterator)

            group_columns.append(GroupColumn(
                display_name=group_name,
                colspan=len(columns_in_group),
                attrs={'class': Struct(superheader=True)},
            ))

            for bound_column in columns_in_group:
                bound_column.attrs['class'].subheader = True
                if bound_column.is_sorting:
                    bound_column.attrs['class'].sorted_column = True

            columns_in_group[0].attrs['class'].first_column = True

        if group_columns:
            group_columns[0].attrs['class'].first_column = True

        for group_column in group_columns:
            if not isinstance(group_column.display_name, six.string_types):
                group_column.display_name = ''
        if all(c.display_name == '' for c in group_columns):
            group_columns = []

        self.header_levels = [group_columns, (self._shown_bound_columns)] if len(group_columns) > 1 else [(self._shown_bound_columns)]

    @property
    def query(self):
        """ :rtype : tri.query.Query """
        self.prepare()
        return self._query

    @property
    def query_form(self):
        """ :rtype : tri.form.Form """
        self.prepare()
        return self._query_form

    @property
    def query_error(self):
        """ :rtype : list of str """
        self.prepare()
        return self._query_error

    @property
    def bulk_form(self):
        """ :rtype : tri.form.Form """
        self.prepare()
        return self._bulk_form

    @property
    def bound_columns(self):
        """ :rtype : list of Column """
        self.prepare()
        return self._bound_columns

    @property
    def shown_bound_columns(self):
        """ :rtype : list of Column """
        self.prepare()
        return self._shown_bound_columns

    @property
    def bound_column_by_name(self):
        """ :rtype: dict[str, Column] """
        self.prepare()
        return self._bound_column_by_name

    # noinspection PyProtectedMember
    def prepare(self):
        if self._has_prepared:
            return

        def bind_columns():
            for index, column in enumerate(self.columns):
                bound_column = column._bind(self, index)
                bound_column._evaluate()
                yield bound_column

        self._bound_columns = list(bind_columns())
        self._bound_column_by_name = OrderedDict((bound_column.name, bound_column) for bound_column in self._bound_columns)

        self._has_prepared = True

        self._prepare_evaluate_members()
        self._prepare_sorting()
        self._prepare_headers()

        if self.model:

            def generate_variables():
                for column in self._bound_columns:
                    if column.query.show:
                        query_namespace = setdefaults_path(
                            Namespace(),
                            column.query,
                            call_target=Variable,
                            name=column.name,
                            gui__display_name=column.display_name,
                            attr=column.attr,
                            model=column.table.model,
                        )
                        yield query_namespace()
            variables = list(generate_variables())

            self._query = Query(
                gui__name=self.name,
                request=self.request,
                variables=variables,
                endpoint_dispatch_prefix=DISPATCH_PATH_SEPARATOR.join(part for part in [self.endpoint_dispatch_prefix, 'query'] if part is not None),
                **self.query_args
            )
            self._query_form = self._query.form() if self._query.variables else None

            self._query_error = ''
            if self._query_form:
                try:
                    q = self.query.to_q()
                    if q:
                        self.data = self.data.filter(q)
                except QueryException as e:
                    self._query_error = str(e)

            def generate_bulk_fields():
                for column in self._bound_columns:
                    if column.bulk.show:
                        bulk_namespace = setdefaults_path(
                            Namespace(),
                            column.bulk,
                            call_target=Field.from_model,
                            name=column.name,
                            attr=column.attr,
                            required=False,
                            empty_choice_tuple=(None, '', '---', True),
                            model=self.model,
                        )
                        if bulk_namespace['call_target'] == Field.from_model:
                            bulk_namespace['field_name'] = column.attr
                        yield bulk_namespace()
            bulk_fields = list(generate_bulk_fields())
            if bulk_fields:
                bulk_fields.append(Field.hidden(name='_all_pks_', attr=None, initial='0', required=False, template='tri_form/input.html'))

                self._bulk_form = Form(
                    data=self.request.POST,
                    fields=bulk_fields,
                    name=self.name,
                    endpoint_dispatch_prefix=DISPATCH_PATH_SEPARATOR.join(part for part in [self.endpoint_dispatch_prefix, 'bulk'] if part is not None),
                    **self.bulk
                )
            else:
                self._bulk_form = None

        self._prepare_auto_rowspan()

    def bound_rows(self):
        return self

    def __iter__(self):
        self.prepare()
        for i, row in enumerate(self.preprocess_data(self.data)):
            new_row = self.preprocess_row(table=self, row=row)
            if new_row is None:
                warnings.warn('preprocess_row must return the object that has been processed', DeprecationWarning)
                new_row = row
            row = new_row

            yield BoundRow(table=self, row=row, row_index=i, **evaluate_recursive(self.row, table=self, row=row))

    def render_attrs(self):
        attrs = self.attrs.copy()
        return render_attrs(attrs)

    def render_tbody(self):
        return mark_safe('\n'.join([bound_row.render() for bound_row in self.bound_rows()]))

    def render_paginator(self, adjacent_pages=6):
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

        context = merged(context, dict(
            extra=get and (get.urlencode() + "&") or "",
            page_numbers=page_numbers,
            show_first=1 not in page_numbers,
            show_last=context["pages"] not in page_numbers,
            show_hits=context["show_hits"],
            hit_label=context["hit_label"],
        ))

        return render_template(request=self.request, template='tri_table/paginator.html', context=context)

    @staticmethod
    @dispatch(
        column=EMPTY,
    )
    def columns_from_model(column, **kwargs):
        return create_members_from_model(
            member_params_by_member_name=column,
            default_factory=Column.from_model,
            **kwargs
        )

    @staticmethod
    @dispatch(
        column=EMPTY,
    )
    def from_model(data=None, model=None, column=None, instance=None, include=None, exclude=None, extra_fields=None, **kwargs):
        """
        Create an entire form based on the fields of a model. To override a field parameter send keyword arguments in the form
        of "the_name_of_the_field__param". For example:

        .. code:: python

            class Foo(Model):
                foo = IntegerField()

            Table.from_model(data=request.GET, model=Foo, field__foo__help_text='Overridden help text')

        :param include: fields to include. Defaults to all
        :param exclude: fields to exclude. Defaults to none (except that AutoField is always excluded!)

        """
        assert model is not None or data is not None, "model or data must be specified"
        if model is None and isinstance(data, QuerySet):
            model = data.model
        columns = Table.columns_from_model(model=model, include=include, exclude=exclude, extra=extra_fields, column=column)
        return Table(data=data, model=model, instance=instance, columns=columns, **kwargs)

    def endpoint_dispatch(self, key, value):
        parts = key.split(DISPATCH_PATH_SEPARATOR, 1)
        prefix = parts.pop(0)
        remaining_key = parts[0] if parts else None
        for endpoint, handler in self.endpoint.items():
            if prefix == endpoint:
                return handler(table=self, key=remaining_key, value=value)

    def bulk_queryset(self):
        queryset = self.model.objects.all() \
            .filter(**self.bulk_filter) \
            .exclude(**self.bulk_exclude)

        if self._bulk_form.fields_by_name._all_pks_.value == '1':
            return queryset
        else:
            pks = [key[len('pk_'):] for key in self.request.POST if key.startswith('pk_')]
            return queryset.filter(pk__in=pks)


class Link(tri_form_Link):
    """
    Class that describes links to add underneath the table.
    """

    # backwards compatibility with old interface
    def __init__(self, title, url=None, **kwargs):
        if url:
            warnings.warn('url parameter is deprecated, use attrs__href', DeprecationWarning)
            kwargs['attrs__href'] = url

        super(Link, self).__init__(title=title, **kwargs)

    @staticmethod
    def icon(icon, title, **kwargs):
        icon_classes = kwargs.pop('icon_classes', [])
        icon_classes_str = ' '.join(['fa-' + icon_class for icon_class in icon_classes])
        return Link(mark_safe('<i class="fa fa-%s %s"></i> %s' % (icon, icon_classes_str, title)), **kwargs)


def table_context(request,
                  table,
                  links=None,
                  paginate_by=None,
                  page=None,
                  extra_context=None,
                  paginator=None,
                  show_hits=False,
                  hit_label='Items'):
    """
    :type table: Table
    """
    if extra_context is None:  # pragma: no cover
        extra_context = {}

    assert table.data is not None

    links, grouped_links = evaluate_and_group_links(links, table=table)

    base_context = {
        'links': links,
        'grouped_links': grouped_links,
        'table': table,
    }

    if paginate_by:
        try:
            paginate_by = int(request.GET.get('page_size', paginate_by))
        except ValueError:  # pragma: no cover
            pass
        if paginator is None:
            paginator = Paginator(table.data, paginate_by)
            object_list = None
        else:  # pragma: no cover
            object_list = table.data
        if not page:
            page = request.GET.get('page', 1)
        try:
            page = int(page)
            if page < 1:  # pragma: no cover
                page = 1
            if page > paginator.num_pages:  # pragma: no cover
                page = paginator.num_pages
            if object_list is None:
                table.data = paginator.page(page).object_list
        except (InvalidPage, ValueError):  # pragma: no cover
            if page == 1:
                table.data = []
            else:
                raise Http404

        base_context.update({
            'request': request,
            'is_paginated': paginator.num_pages > 1,
            'results_per_page': paginate_by,
            'has_next': paginator.num_pages > page,
            'has_previous': page > 1,
            'page_size': paginate_by,
            'page': page,
            'next': page + 1,
            'previous': page - 1,
            'pages': paginator.num_pages,
            'hits': paginator.count,
            'show_hits': show_hits,
            'hit_label': hit_label})
    else:  # pragma: no cover
        base_context.update({
            'is_paginated': False})

    base_context.update(extra_context)
    return base_context


@dispatch(
    table=EMPTY,
)
def render_table(request,
                 table,
                 links=None,
                 context=None,
                 template='tri_table/list.html',
                 blank_on_empty=False,
                 paginate_by=40,  # pragma: no mutate
                 page=None,
                 paginator=None,
                 show_hits=False,
                 hit_label='Items',
                 post_bulk_edit=lambda table, queryset, updates: None):
    """
    Render a table. This automatically handles pagination, sorting, filtering and bulk operations.

    :param request: the request object. This is set on the table object so that it is available for lambda expressions.
    :param table: an instance of Table
    :param links: a list of instances of Link
    :param context: dict of extra context parameters
    :param template: if you need to render the table differently you can override this parameter with either a name of a template to load or a `Template` instance.
    :param blank_on_empty: turn off the displaying of `{{ empty_message }}` in the template when the list is empty
    :param show_hits: Display how many items there are total in the paginator.
    :param hit_label: Label for the show_hits display.
    :return: a string with the rendered HTML table
    """
    if not context:
        context = {}

    if table is None or isinstance(table, Namespace):
        table = Table.from_model(**table)

    assert isinstance(table, Table)
    table.request = request

    should_return, dispatch_result = handle_dispatch(request=request, obj=table)
    if should_return:
        return dispatch_result

    context['bulk_form'] = table.bulk_form
    context['query_form'] = table.query_form
    context['tri_query_error'] = table.query_error

    if table.bulk_form and request.method == 'POST':
        if table.bulk_form.is_valid():
            queryset = table.bulk_queryset()

            updates = {
                field.name: field.value
                for field in table.bulk_form.fields
                if field.value is not None and field.value is not '' and field.attr is not None
            }
            queryset.update(**updates)

            post_bulk_edit(table=table, queryset=queryset, updates=updates)

            return HttpResponseRedirect(request.META['HTTP_REFERER'])

    table.context = table_context(
        request,
        table=table,
        links=links,
        paginate_by=paginate_by,
        page=page,
        extra_context=context,
        paginator=paginator,
        show_hits=show_hits,
        hit_label=hit_label,
    )

    if not table.data and blank_on_empty:
        return ''

    if table.query_form and not table.query_form.is_valid():
        table.data = None
        table.context['invalid_form_message'] = mark_safe('<i class="fa fa-meh-o fa-5x" aria-hidden="true"></i>')

    return render_template(request, template, table.context)


def render_table_to_response(*args, **kwargs):
    """
    Shortcut for `HttpResponse(render_table(*args, **kwargs))`
    """
    response = render_table(*args, **kwargs)
    if isinstance(response, HttpResponse):  # pragma: no cover
        return response
    return HttpResponse(response)


setup_db_compat()
