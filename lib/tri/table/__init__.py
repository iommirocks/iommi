# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import copy
import json
import warnings
from collections import OrderedDict
from itertools import groupby

from tri.form.render import render_attrs, render_class

from django.conf import settings
from django.core.paginator import Paginator, InvalidPage
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string, get_template
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe
from django.db.models import QuerySet
import six
from tri.declarative import declarative, creation_ordered, with_meta, setdefaults, evaluate_recursive, evaluate, getattr_path, sort_after, LAST, setdefaults_path, dispatch, EMPTY, flatten, Namespace, setattr_path
from tri.form import Field, Form, member_from_model, expand_member, create_members_from_model
from tri.named_struct import NamedStructField, NamedStruct
from tri.struct import Struct
from tri.query import Query, Variable, QueryException, Q_OP_BY_OP

from tri.table.db_compat import setup_db_compat

__version__ = '4.1.0'

LAST = LAST

_column_factory_by_field_type = OrderedDict()


def register_column_factory(field_class, factory):
    _column_factory_by_field_type[field_class] = factory


def prepare_headers(request, bound_columns):
    """
    :type bound_columns: list of BoundColumn
    """
    for column in bound_columns:
        if column.sortable:
            params = request.GET.copy()
            order = request.GET.get('order', None)
            start_sort_desc = column.sort_default_desc
            params['order'] = column.name if not start_sort_desc else '-' + column.name
            if order is not None:
                is_desc = len(order) > 0 and order[0] == '-'
                order_field = is_desc and order[1:] or order
                if order_field == column.name:
                    new_order = is_desc and order[1:] or "-%s" % order
                    params['order'] = new_order
            column.is_sorting = False if order is None else (column.name == order or ('-' + column.name) == order)
            column.url = "?%s" % params.urlencode()
        else:
            column.is_sorting = False
    return bound_columns


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

    objects.sort(key=lambda x: getattr_path(x, order_field), reverse=is_desc)


def yes_no_formatter(value, **_):
    """ Handle True/False from Django model and 1/0 from raw sql """
    if value is True or value == 1:
        return 'Yes'
    if value is False or value == 0:
        return 'No'
    if value is None:  # pragma: no cover
        return ''
    assert False, "Unable to convert {} to Yes/No".format(value)   # pragma: no cover


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


class NamespaceAwareObject(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            getattr(self, k)  # Check existence
            setattr(self, k, v)
        super(NamespaceAwareObject, self).__init__()


@creation_ordered
class Column(NamespaceAwareObject):
    """
    Class that describes a column, i.e. the text of the header, how to get and display the data in the cell, etc.
    """

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

        self.name = None
        """ :type: unicode """
        self.after = None
        self.attrs = None
        self.url = None
        self.title = None
        self.show = None
        self.sort_default_desc = None
        self.sortable = None
        self.group = None
        self.auto_rowspan = None
        """ :type: bool """
        self.cell = None
        self.model = None
        self.model_field = None
        self.choices = None
        self.bulk = None
        self.query = None

        self.extra = None

        super(Column, self).__init__(**kwargs)

        self.table = None
        """ :type: Table """
        self.column = None
        """ :type: Column """
        self.index = None
        """ :type: int """
        self.is_sorting = None
        """ :type: bool """

    @staticmethod
    def attr(table, column, **_):
        return column.name

    @staticmethod
    def sort_key(table, column, **_):
        return column.attr

    @staticmethod
    def display_name(table, column, **_):
        return force_text(column.name).rsplit('__', 1)[-1].replace("_", " ").capitalize()

    def _bind(self, table, index):
        bound_column = copy.copy(self)

        bound_column.index = index
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

        for k, v in table.column.get(bound_column.name, {}).items():
            setattr_path(bound_column, k, v)
        bound_column.table = table
        bound_column.column = self

        return bound_column

    EVALUATED_ATTRIBUTES = [
        'after', 'attr', 'auto_rowspan', 'bulk', 'cell', 'choices', 'display_name', 'extra', 'group', 'model', 'model_field', 'query', 'show', 'sort_default_desc', 'sort_key', 'sortable', 'title', 'url'
    ]

    def _evaluate(self):
        """
        Evaluates callable/lambda members. After this function is called all members will be values.
        """
        for k in self.EVALUATED_ATTRIBUTES:
            v = getattr(self, k)
            new_value = evaluate_recursive(v, table=self.table, column=self)
            if new_value is not v:
                setattr(self, k, new_value)

    def render_css_class(self):
        return render_class(self.attrs['class'])

    @staticmethod
    def text(**kwargs):  # pragma: no cover
        return Column(**kwargs)

    @staticmethod
    def icon(icon, is_report=False, icon_title='', show=True, **kwargs):
        """
        Shortcut to create font awesome-style icons.

        :param icon: the font awesome name of the icon
        """
        setdefaults(kwargs, dict(
            name='',
            display_name='',
            sortable=False,
            attrs__class__thin=True,
            show=lambda table, **rest: evaluate(show, table=table, **rest) and not is_report,
            title=icon_title,
            cell__value=lambda table, column, row, **_: True,
            cell__attrs__class__cj=True,
            cell__format=lambda value, **_: mark_safe('<i class="fa fa-lg fa-%s"%s></i>' % (icon, ' title="%s"' % icon_title if icon_title else '')) if value else ''
        ))
        return Column(**kwargs)

    @staticmethod
    def edit(is_report=False, **kwargs):
        """
        Shortcut for creating a clickable edit icon. The URL defaults to `your_object.get_absolute_url() + 'edit/'`. Specify the option cell__url to override.
        """
        setdefaults(kwargs, dict(
            cell__url=lambda row, **_: row.get_absolute_url() + 'edit/',
            display_name=''
        ))
        return Column.icon('pencil-square-o', is_report, 'Edit', **kwargs)

    @staticmethod
    def delete(is_report=False, **kwargs):
        """
        Shortcut for creating a clickable delete icon. The URL defaults to `your_object.get_absolute_url() + 'delete/'`. Specify the option cell__url to override.
        """
        setdefaults(kwargs, dict(
            cell__url=lambda row, **_: row.get_absolute_url() + 'delete/',
            display_name=''
        ))
        return Column.icon('trash-o', is_report, 'Delete', **kwargs)

    @staticmethod
    def download(is_report=False, **kwargs):
        """
        Shortcut for creating a clickable download icon. The URL defaults to `your_object.get_absolute_url() + 'download/'`. Specify the option cell__url to override.
        """
        setdefaults(kwargs, dict(
            cell__url=lambda row, **_: row.get_absolute_url() + 'download/',
            cell__value=lambda row, **_: getattr(row, 'pk', False),
        ))
        return Column.icon('download', is_report, 'Download', **kwargs)

    @staticmethod
    def run(is_report=False, show=True, **kwargs):
        """
        Shortcut for creating a clickable run icon. The URL defaults to `your_object.get_absolute_url() + 'run/'`. Specify the option cell__url to override.
        """
        setdefaults(kwargs, dict(
            name='',
            title='Run',
            sortable=False,
            css_class={'thin'},
            cell__url=lambda row, **_: row.get_absolute_url() + 'run/',
            cell__value='Run',
            show=lambda table, **rest: evaluate(show, table=table, **rest) and not is_report,
        ))
        return Column(**kwargs)

    @staticmethod
    def select(is_report=False, checkbox_name='pk', show=True, checked=lambda x: False, **kwargs):
        """
        Shortcut for a column of checkboxes to select rows. This is useful for implementing bulk operations.

        :param checkbox_name: the name of the checkbox. Default is "pk", resulting in checkboxes like "pk_1234".
        :param checked: callable to specify if the checkbox should be checked initially. Defaults to False.
        """
        setdefaults(kwargs, dict(
            name='__select__',
            title='Select all',
            display_name=mark_safe('<i class="fa fa-check-square-o"></i>'),
            sortable=False,
            show=lambda table, **rest: evaluate(show, table=table, **rest) and not is_report,
            attrs__class__thin=True,
            attrs__class__nopad=True,
            cell__attrs__class__cj=True,
            cell__value=lambda row, **_: mark_safe('<input type="checkbox"%s class="checkbox" name="%s_%s" />' % (' checked' if checked(row.pk) else '', checkbox_name, row.pk)),
        ))
        return Column(**kwargs)

    @staticmethod
    def boolean(is_report=False, **kwargs):
        """
        Shortcut to render booleans as a check mark if true or blank if false.
        """
        def render_icon(value):
            if callable(value):
                value = value()
            return mark_safe('<i class="fa fa-check" title="Yes"></i>') if value else ''

        setdefaults(kwargs, dict(
            cell__format=lambda value, **rest: yes_no_formatter(value=value, **rest) if is_report else render_icon(value),
            cell__attrs__class__cj=True,
            query__class=Variable.boolean,
            bulk__class=Field.boolean,
        ))
        return Column(**kwargs)

    @staticmethod
    def link(**kwargs):
        """
        Shortcut for creating a cell that is a link. The URL is the result of calling `get_absolute_url()` on the object.
        """
        def url(table, column, row, value):
            del table, value
            r = getattr_path(row, column.attr)
            return r.get_absolute_url() if r else ''

        setdefaults(kwargs, dict(
            cell__url=url,
        ))
        return Column(**kwargs)

    @staticmethod
    def number(**kwargs):
        """
        Shortcut for rendering a number. Sets the "rj" (as in "right justified") CSS class on the cell and header.
        """
        setdefaults(kwargs, dict(
            cell__attrs__class__rj=True
        ))
        return Column(**kwargs)

    @staticmethod
    def float(**kwargs):
        setdefaults(kwargs, dict(
            query__class=Variable.float,
            bulk__class=Field.float,
        ))
        return Column.number(**kwargs)

    @staticmethod
    def integer(**kwargs):
        setdefaults(kwargs, dict(
            query__class=Variable.integer,
            bulk__class=Field.integer,
        ))
        return Column.number(**kwargs)

    @staticmethod
    def choice_queryset(**kwargs):
        setdefaults(kwargs, dict(
            bulk__class=Field.choice_queryset,
            bulk__model=kwargs.get('model'),
            query__class=Variable.choice_queryset,
            query__model=kwargs.get('model'),
        ))
        return Column.choice(**kwargs)

    @staticmethod
    def multi_choice_queryset(**kwargs):
        setdefaults(kwargs, dict(
            bulk__class=Field.multi_choice_queryset,
            bulk__model=kwargs.get('model'),
            query__class=Variable.multi_choice_queryset,
            query__model=kwargs.get('model'),
            cell__format=lambda value, **_: ', '.join(['%s' % x for x in value.all()]),
        ))
        return Column.choice(**kwargs)

    @staticmethod
    def choice(**kwargs):
        choices = kwargs['choices']
        setdefaults(kwargs, dict(
            bulk__class=Field.choice,
            bulk__choices=choices,
            query__class=Variable.choice,
            query__choices=choices,
        ))
        return Column(**kwargs)

    @staticmethod
    def substring(**kwargs):
        setdefaults(kwargs, dict(
            query__gui_op=':',
        ))
        return Column(**kwargs)

    @staticmethod
    def date(**kwargs):
        setdefaults(kwargs, dict(
            query__class=Variable.date,
            query__op_to_q_op=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OP_BY_OP[op],
            bulk__class=Field.date,
        ))
        return Column(**kwargs)

    @staticmethod
    def datetime(**kwargs):
        setdefaults(kwargs, dict(
            query__class=Variable.datetime,
            query__op_to_q_op=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OP_BY_OP[op],
            bulk__class=Field.datetime,
        ))
        return Column(**kwargs)

    @staticmethod
    def time(**kwargs):
        setdefaults(kwargs, dict(
            query__class=Variable.time,
            query__op_to_q_op=lambda op: {'=': 'exact', ':': 'contains'}.get(op) or Q_OP_BY_OP[op],
            bulk__class=Field.time,
        ))
        return Column(**kwargs)

    @staticmethod
    def email(**kwargs):
        setdefaults(kwargs, dict(
            query__class=Variable.email,
            bulk__class=Field.email,
        ))
        return Column(**kwargs)

    @staticmethod
    def decimal(**kwargs):
        setdefaults(kwargs, dict(
            bulk__class=Field.decimal,
            query__class=Variable.decimal,
        ))
        return Column(**kwargs)

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
            context = RequestContext(self.table.request, dict(bound_row=self, row=self.row, table=self.table))
            if isinstance(self.template, six.string_types):
                # positional arguments here to get compatibility with both django 1.7 and 1.8+
                return render_to_string(self.template, context)
            else:
                return self.template.render(context)

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

        self.value = evaluate(bound_column.cell.value, table=bound_row.table, column=bound_column.column, row=bound_row.row, bound_row=bound_row, bound_column=bound_column)

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
            context = RequestContext(self.table.request, dict(table=self.table, bound_column=self.bound_column, bound_row=self.bound_row, row=self.row, value=self.value, bound_cell=self))
            if isinstance(cell__template, six.string_types):
                return render_to_string(cell__template, context)
            else:
                return cell__template.render(context)

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
        return mark_safe(cell_contents)

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
class Table(object):

    """
    Describe a table. Example:

    .. code:: python

        class FooTable(Table):
            class Meta:
                sortable = False
            a = Column()
            b = Column()

    """

    @dispatch(
        column=EMPTY,
        bulk_filter={},
        bulk_exclude={},
        sortable=True,
        attrs=EMPTY,
        attrs__class__listview=True,
        row__attrs__class=EMPTY,
        row__template=None,
        filter__template='tri_query/form.html',  # tri.query dependency, see render_filter() below.
        header__template='tri_table/table_header_rows.html',
        links__template='tri_table/links.html',
        model=None,
        query=EMPTY,
        bulk=EMPTY,

        endpoint_dispatch_prefix=None,
        endpoint__query=lambda table, key, value: table.query.endpoint_dispatch(key=key, value=value) if table.query is not None else None,
        endpoint__bulk=lambda table, key, value: table.bulk_form.endpoint_dispatch(key=key, value=value) if table.bulk is not None else None,

        extra=EMPTY,
    )
    def __init__(self, data=None, request=None, columns=None, columns_dict=None, model=None, filter=None, bulk_exclude=None, sortable=None, links=None, column=None, bulk=None, header=None, bulk_filter=None, endpoint=None, attrs=None, query=None, endpoint_dispatch_prefix=None, row=None, instance=None, extra=None):
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
            warnings.warn('deriving model from data queryset is deprecated, use Table.from_model', DeprecationWarning)
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

        self.model = model
        self.instance = instance

        self.filter = TemplateConfig(**filter)
        self.links = TemplateConfig(**links)
        self.header = TemplateConfig(**header)
        self.row = RowConfig(**row)
        self.bulk_exclude = bulk_exclude
        self.sortable = sortable
        self.column = column
        self.bulk = bulk
        self.bulk_filter = bulk_filter
        self.endpoint = endpoint
        self.endpoint_dispatch_prefix = endpoint_dispatch_prefix
        self.attrs = attrs

        self.query_args = query
        self.query = None
        """ :type : tri.query.Query """
        self.query_form = None
        """ :type : tri.form.Form """
        self.query_error = None
        """ :type : list of str """

        self.bulk_form = None
        """ :type : tri.form.Form """
        self.bound_columns = None
        """ :type : list of Column """
        self.shown_bound_columns = None
        """ :type : list of Column """
        self.bound_column_by_name = None
        """ :type: dict[str, Column] """
        self._has_prepared = False
        """ :type: bool """
        self.header_levels = None

        self.extra = extra
        """ :type: tri.declarative.Namespace """

    def render_links(self):
        return self.render_template_config(self.links, self.context)

    def render_header(self):
        return self.render_template_config(self.header, self.context)

    def render_filter(self):
        if not self.query_form:
            return ''
        context = self.context
        with context.push():
            context['form'] = self.query_form
            return self.render_template_config(self.filter, context)

    @staticmethod
    def render_template_config(template_config, context):
        if template_config.template:
            if isinstance(template_config.template, six.string_types):
                return render_to_string(template_config.template, context)
            else:
                return template_config.template.render(context)
        return ''

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

                column.cell.attrs['rowspan'] = set_row_span(rowspan_by_row)
                assert 'style' not in column.cell.attrs  # TODO: support both specifying style cell__attrs and auto_rowspan
                column.cell.attrs['style'] = set_display_none(rowspan_by_row)

    def _prepare_evaluate_members(self):
        self.shown_bound_columns = [bound_column for bound_column in self.bound_columns if bound_column.show]

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
            'query',
            'bulk',
            'endpoint',
        ):
            setattr(self, attr, evaluate_recursive(getattr(self, attr), table=self))

        if not self.sortable:
            for bound_column in self.bound_columns:
                bound_column.sortable = False

    def _prepare_sorting(self):
        # sorting
        order = self.request.GET.get('order', None)
        if order is not None:
            is_desc = order[0] == '-'
            order_field = is_desc and order[1:] or order
            tmp = [x for x in self.shown_bound_columns if x.name == order_field]
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
                        valid_sort_fields = {x.name for x in self.model._meta.fields}
                        order_args = [order_arg for order_arg in order_args if order_arg.split('__', 1)[0] in valid_sort_fields]
                    order_args = ["%s%s" % (is_desc and '-' or '', x) for x in order_args]
                    self.data = self.data.order_by(*order_args)

    def _prepare_headers(self):
        bound_columns = prepare_headers(self.request, self.shown_bound_columns)

        # The id(header) and the type(x.display_name) stuff is to make None not be equal to None in the grouping
        group_columns = []

        class GroupColumn(Namespace):
            def render_css_class(self):
                return render_class(self.attrs['class'])

        for group_name, group_iterator in groupby(bound_columns, key=lambda header: header.group or id(header)):

            columns_in_group = list(group_iterator)

            group_columns.append(GroupColumn(
                display_name=group_name,
                sortable=False,
                colspan=len(columns_in_group),
                attrs__class__superheader=True,
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

        self.header_levels = [group_columns, bound_columns] if len(group_columns) > 1 else [bound_columns]
        return bound_columns

    # noinspection PyProtectedMember
    def prepare(self, request):
        if self._has_prepared:
            return

        self.request = request

        def bind_columns():
            for index, column in enumerate(self.columns):
                bound_column = column._bind(self, index)
                bound_column._evaluate()
                yield bound_column

        self.bound_columns = list(bind_columns())
        self.bound_column_by_name = OrderedDict((bound_column.name, bound_column) for bound_column in self.bound_columns)

        self._has_prepared = True

        self._prepare_evaluate_members()
        self._prepare_sorting()
        headers = self._prepare_headers()

        if self.model:

            def generate_variables():
                for column in self.bound_columns:
                    if column.query.show:
                        query_kwargs = setdefaults_path(
                            Struct(),
                            column.query,
                            dict(
                                name=column.name,
                                gui__label=column.display_name,
                                attr=column.attr,
                                model=column.table.model,
                            ), {
                                'class': Variable,
                            }
                        )
                        yield query_kwargs.pop('class')(**query_kwargs)
            variables = list(generate_variables())

            self.query = Query(
                request=request,
                variables=variables,
                endpoint_dispatch_prefix='__'.join(part for part in [self.endpoint_dispatch_prefix, 'query'] if part is not None),
                **flatten(self.query_args)
            )
            self.query_form = self.query.form() if self.query.variables else None

            self.query_error = ''
            if self.query_form:
                try:
                    self.data = self.data.filter(self.query.to_q())
                except QueryException as e:
                    self.query_error = str(e)

            def generate_bulk_fields():
                for column in self.bound_columns:
                    if column.bulk.show:
                        bulk_kwargs = setdefaults_path(
                            Struct(),
                            column.bulk,
                            dict(
                                name=column.name,
                                attr=column.attr,
                                required=False,
                                empty_choice_tuple=(None, '', '---', True),
                                model=self.model,
                            ), {
                                'class': Field.from_model,
                            }
                        )
                        if bulk_kwargs['class'] == Field.from_model:
                            bulk_kwargs['field_name'] = column.attr
                        yield bulk_kwargs.pop('class')(**bulk_kwargs)
            bulk_fields = list(generate_bulk_fields())

            self.bulk_form = Form(
                data=request.POST,
                fields=bulk_fields,
                endpoint_dispatch_prefix='__'.join(part for part in [self.endpoint_dispatch_prefix, 'bulk'] if part is not None),
                **flatten(self.bulk)
            ) if bulk_fields else None

        self._prepare_auto_rowspan()

        return headers, self.header_levels

    def bound_rows(self):
        return self

    def __iter__(self):
        self.prepare(self.request)
        for i, row in enumerate(self.data):
            yield BoundRow(table=self, row=row, row_index=i, **evaluate_recursive(self.row, table=self, row=row))

    def render_attrs(self):
        attrs = self.attrs.copy()
        return render_attrs(attrs)

    def render_tbody(self):
        return mark_safe('\n'.join([bound_row.render() for bound_row in self.bound_rows()]))

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
        assert model or data, "model or data must be specified"
        if model is None and isinstance(data, QuerySet):
            model = data.model
        columns = Table.columns_from_model(model=model, include=include, exclude=exclude, extra=extra_fields, column=column)
        return Table(data=data, model=model, instance=instance, columns=columns, **kwargs)

    def endpoint_dispatch(self, key, value):
        parts = key.split('__', 1)
        prefix = parts.pop(0)
        remaining_key = parts[0] if parts else None
        for endpoint, handler in self.endpoint.items():
            if prefix == endpoint:
                return handler(table=self, key=remaining_key, value=value)


class Link(Struct):
    """
    Class that describes links to add underneath the table.
    """
    # noinspection PyShadowingBuiltins
    def __init__(self, title, url, show=True, group=None, id=None, **kwargs):
        super(Link, self).__init__(title=title, url=url, show=show, group=group, id=id, **kwargs)

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
                  context_processors=None,
                  paginator=None,
                  show_hits=False,
                  hit_label='Items'):
    """
    :type table: Table
    """
    if extra_context is None:  # pragma: no cover
        extra_context = {}

    assert table.data is not None

    grouped_links = {}
    if links is not None:
        links = evaluate_recursive(links, table=table)
        links = [link for link in links if link.show and link.url]

        grouped_links = groupby((link for link in links if link.group is not None), key=lambda l: l.group)
        grouped_links = [(g, slugify(g), list(lg)) for g, lg in grouped_links]  # because django templates are crap!

        links = [link for link in links if link.group is None]

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
    return RequestContext(request, base_context, context_processors)


def set_row_span(rowspan_by_row):
    return lambda row, **_: rowspan_by_row[id(row)] if id(row) in rowspan_by_row else None


def set_display_none(rowspan_by_row):
    return lambda row, **_: 'display: none' if id(row) not in rowspan_by_row else None


@dispatch(
    table=EMPTY,
)
def render_table(request,
                 table,
                 links=None,
                 context=None,
                 template_name='tri_table/list.html',  # deprecated
                 template=None,
                 blank_on_empty=False,
                 paginate_by=40,
                 page=None,
                 context_processors=None,
                 paginator=None,
                 show_hits=False,
                 hit_label='Items'):
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

    table.prepare(request)
    assert isinstance(table, Table)

    for key, value in request.GET.items():
        if key.startswith('__'):
            remaining_key = key[2:]
            expected_prefix = table.endpoint_dispatch_prefix
            if expected_prefix is not None:
                parts = remaining_key.split('__', 1)
                prefix = parts.pop(0)
                if prefix != expected_prefix:
                    return
                remaining_key = parts[0] if parts else None
            data = table.endpoint_dispatch(key=remaining_key, value=value)
            if data is not None:
                return HttpResponse(json.dumps(data), content_type='application/json')

    context['bulk_form'] = table.bulk_form
    context['query_form'] = table.query_form
    context['tri_query_error'] = table.query_error

    if table.bulk_form and request.method == 'POST':
        pks = [key[len('pk_'):] for key in request.POST if key.startswith('pk_')]

        if table.bulk_form.is_valid():
            table.model.objects.all() \
                .filter(pk__in=pks) \
                .filter(**table.bulk_filter) \
                .exclude(**table.bulk_exclude) \
                .update(**{field.name: field.value for field in table.bulk_form.fields if field.value is not None and field.value is not ''})

        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    table.context = table_context(
        request,
        table=table,
        links=links,
        paginate_by=paginate_by,
        page=page,
        extra_context=context,
        context_processors=context_processors,
        paginator=paginator,
        show_hits=show_hits,
        hit_label=hit_label,
    )

    if not table.data and blank_on_empty:  # pragma: no cover
        return ''

    if table.query_form and not table.query_form.is_valid():
        table.data = None
        table.context['invalid_form_message'] = mark_safe('<i class="fa fa-meh-o fa-5x" aria-hidden="true"></i>')

    if not template:
        template = template_name

    if isinstance(template, six.string_types):
        return get_template(template).render(table.context)
    else:
        return template.render(table.context)


def render_table_to_response(*args, **kwargs):
    """
    Shortcut for `HttpResponse(render_table(*args, **kwargs))`
    """
    response = render_table(*args, **kwargs)
    if isinstance(response, HttpResponse):  # pragma: no cover
        return response
    return HttpResponse(response)


setup_db_compat()
