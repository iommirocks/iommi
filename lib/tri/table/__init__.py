# coding: utf-8
from __future__ import absolute_import, unicode_literals
from itertools import groupby
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string, get_template
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.db.models import QuerySet
from tri.declarative import declarative, creation_ordered, with_meta, setdefaults, evaluate_recursive, evaluate, getattr_path
from tri.form import extract_subkeys, Field, Form
from tri.named_struct import NamedStructField, NamedStruct
from tri.struct import Struct, Frozen, merged
from tri.query import Query, Variable, QueryException


__version__ = '1.7.0'


def prepare_headers(request, bound_columns):
    """
    :type bound_columns: list of BoundColumn
    """
    for column in bound_columns:
        if column.sortable:
            params = request.GET.copy()
            order = request.GET.get('order', None)
            start_sort_desc = column['sort_default_desc']
            params['order'] = column['name'] if not start_sort_desc else '-' + column['name']
            if order is not None:
                is_desc = len(order) > 0 and order[0] == '-'
                order_field = is_desc and order[1:] or order
                if order_field == column['name']:
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


def render_attrs(attrs):
    """
    Render HTML attributes, or return '' if no attributes needs to be rendered.
    """
    if attrs is not None:
        return mark_safe(' %s' % ' '.join(['%s="%s"' % (key, value) for key, value in sorted(attrs.items()) if value]))
    return ''


def yes_no_formatter(table, column, row, value):
    """ Handle True/False from Django model and 1/0 from raw sql """
    del table, column, row
    if value is True or value == 1:
        return 'Yes'
    if value is False or value == 0:
        return 'No'
    if value is None:  # pragma: no cover
        return ''
    assert False, "Unable to convert {} to Yes/No".format(value)   # pragma: no cover


def list_formatter(table, column, row, value):
    del table, column, row
    return ', '.join([conditional_escape(x) for x in value])


_cell_formatters = {
    bool: yes_no_formatter,
    tuple: list_formatter,
    list: list_formatter,
    set: list_formatter,
    QuerySet: lambda table, column, row, value: list_formatter(table=table, column=column, row=row, value=list(value))
}


def register_cell_formatter(type_or_class, formatter):
    """
    Register a default formatter for a type. A formatter is a function that takes four keyword arguments: table, column, row, value
    """
    global _cell_formatters
    _cell_formatters[type_or_class] = formatter


def default_cell_formatter(table, column, row, value):
    """
    :type column: tri.table.BoundColumn
    """
    formatter = _cell_formatters.get(type(value))
    if formatter:
        value = formatter(table=table, column=column, row=row, value=value)

    if value is None:
        return ''

    return conditional_escape(value)


class BoundRow(Struct):
    """
    Internal class used in row rendering
    """
    def __init__(self, table, row, **kwargs):
        """
        :type table: Table
        """
        self.table = table
        self.row = row
        super(BoundRow, self).__init__(**evaluate_recursive(kwargs, table=table, row=row))

    def render(self):
        if self.template:
            # positional arguments here to get compatibility with both django 1.7 and 1.8+
            return render_to_string(self.template, dict(bound_row=self, row=self.row, table=self.table))
        else:
            return '<tr%s>%s</tr>' % (self.render_attrs(), self.render_cells())

    def render_attrs(self):
        attrs = self.attrs.copy()
        if attrs['class']:
            attrs['class'] += ' '
        attrs['class'] += 'row%s' % (self.row_index % 2 + 1)
        pk = getattr(self.row, 'pk', None)
        if pk:
            attrs['data-pk'] = pk
        return render_attrs(attrs)

    def render_cells(self):
        return '\n'.join([bound_column.render_cell(bound_row=self) for bound_column in self.table.shown_bound_columns])


class ColumnBase(NamedStruct):
    """
    Class that describes a column, i.e. the text of the header, how to get and display the data in the cell, etc.
    """

    name = NamedStructField()
    """ :type: unicode """
    attrs = NamedStructField(default={})
    attr = NamedStructField(default=lambda table, column: column.name)
    css_class = NamedStructField(default=set())
    url = NamedStructField()
    title = NamedStructField()
    show = NamedStructField(default=True)
    sort_key = NamedStructField(lambda column: column.attr)
    sort_default_desc = NamedStructField(default=False)
    display_name = NamedStructField(default=lambda table, column: force_unicode(column.name).rsplit('__', 1)[-1].replace("_", " ").capitalize())
    sortable = NamedStructField(default=True)
    group = NamedStructField()
    auto_rowspan = NamedStructField(default=False)

    cell__template = NamedStructField()
    cell__value = NamedStructField(default=lambda table, column, row: getattr_path(row, evaluate(column.attr, table=table, column=column)))
    cell__format = NamedStructField(default=default_cell_formatter)
    cell__attrs = NamedStructField(default={})
    cell__url = NamedStructField()
    """ :type : str or callable """
    cell__url_title = NamedStructField()
    """ :type : str or callable """

    model = NamedStructField()
    choices = NamedStructField()
    bulk = NamedStructField()
    query = NamedStructField()

    extra = NamedStructField(default=Struct())


@creation_ordered
class Column(Frozen, ColumnBase):
    # noinspection PyShadowingBuiltins
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
        :param cell__template: name of a template file. The template gets arguments: `table`, `bound_column`, `bound_row`, `row` and `value`.
        :param cell__value: string or callable that receives kw arguments: `table`, `column` and `row`. This is used to extract which data to display from the object.
        :param cell__format: string or callable that receives kw arguments: `table`, `column`, `row` and `value`. This is used to convert the extracted data to html output (use `mark_safe`) or a string.
        :param cell__attrs: dict of attr name to callables that receive kw arguments: `table`, `column`, `row` and `value`.
        :param cell__url: callable that receives kw arguments: `table`, `column`, `row` and `value`.
        :param cell__url_title: callable that receives kw arguments: `table`, `column`, `row` and `value`.
        """

        setdefaults(kwargs, dict(
            bulk=(Struct(extract_subkeys(kwargs, 'bulk', defaults=dict(show=False)))),
            query=(Struct(extract_subkeys(kwargs, 'query', defaults=dict(show=False)))),
            extra=(Struct(extract_subkeys(kwargs, 'extra'))),
        ))

        kwargs = {k: v for k, v in kwargs.items() if not k.startswith('bulk__') and not k.startswith('query__') and not k.startswith('extra__')}

        assert isinstance(kwargs['bulk'], dict)
        assert isinstance(kwargs['query'], dict)
        assert isinstance(kwargs['extra'], dict)

        super(Column, self).__init__(**kwargs)

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
            css_class={'thin'},
            show=lambda table, column: evaluate(show, table=table, column=column) and not is_report,
            title=icon_title,
            cell__value=lambda table, column, row: True,
            cell__attrs={'class': 'cj'},
            cell__format=lambda table, column, row, value: mark_safe('<i class="fa fa-lg fa-%s"%s></i>' % (icon, ' title="%s"' % icon_title if icon_title else '')) if value else ''
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
            show=lambda table, column: evaluate(show, table=table, column=column) and not is_report,
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
            show=lambda table, column: evaluate(show, table=table, column=column) and not is_report,
            css_class={'thin', 'nopad'},
            cell__attrs={'class': 'cj'},
            cell__value=lambda table, column, row: mark_safe('<input type="checkbox"%s class="checkbox" name="%s_%s" />' % (' checked' if checked(row.pk) else '', checkbox_name, row.pk)),
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
            cell__format=lambda table, column, row, value: yes_no_formatter(table=table, column=column, row=row, value=value) if is_report else render_icon(value),
            cell__attrs={'class': 'cj'},
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
        if 'cell__attrs' not in kwargs:
            kwargs['cell__attrs'] = {}
        if 'class' not in kwargs['cell__attrs']:
            kwargs['cell__attrs']['class'] = 'rj'
        return Column(**kwargs)

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


class BoundColumn(ColumnBase):

    table = NamedStructField()
    """ :type: Table """
    column = NamedStructField()
    """ :type: Column """
    index = NamedStructField()
    """ :type: int """
    is_sorting = NamedStructField()
    """ :type: bool """

    def render_css_class(self):
        return ' '.join(sorted(self.css_class))

    def cell_contents(self, bound_row):
        return evaluate(self.cell__value, table=bound_row.table, column=self.column, row=bound_row.row)

    def render_cell(self, bound_row):
        assert self.show

        row = bound_row.row
        value = self.cell_contents(bound_row=bound_row)

        table = bound_row.table
        if self.cell__template:
            value = render_to_string(self.cell__template, {'table': table, 'bound_column': self, 'bound_row': bound_row, 'row': bound_row.row, 'value': value})

        cell_contents = evaluate(self.cell__format, table=self.table, column=self, row=row, value=value)
        if self.cell__url:
            cell__url = self.cell__url(table=table, column=self, row=row, value=value) if callable(self.cell__url) else self.cell__url

            cell__url_title = self.cell__url_title(table=table, column=self, row=row, value=value) if callable(self.cell__url_title) else self.cell__url_title
            cell_contents = '<a href="{}"{}>{}</a>'.format(
                cell__url,
                ' title=%s' % cell__url_title if cell__url_title else '',
                cell_contents,
            )
        return '<td{attrs}>{cell_contents}</td>'.format(
            attrs=render_attrs(evaluate_recursive(self.cell__attrs, table=table, column=self, row=row, value=value)),
            cell_contents=cell_contents,
        )


@declarative(Column, 'columns')
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

    class Meta:
        attrs = {'class': 'listview'}
        bulk_filter = {}
        bulk_exclude = {}
        sortable = True
        row__attrs = {'class': ''}
        row__template = None
        filter__template = 'tri_query/form.html'
        header__template = 'tri_table/table_header_rows.html'
        links__template = 'tri_table/links.html'

        model = None

    def __init__(self, data, request=None, columns=None, **kwargs):
        """
        :param data: a list of QuerySet of objects
        :param columns: (use this only when not using the declarative style) a list of Column objects
        :param attrs: dict of strings to string/callable of HTML attributes to apply to the table
        :param row__attrs: dict of strings to string/callable of HTML attributes to apply to the row. Callables are passed the row as argument.
        :param row__template: name of template to use for rendering the row
        :param bulk_filter: filters to apply to the QuerySet before performing the bulk operation
        :param bulk_exclude: exclude filters to apply to the QuerySet before performing the bulk operation
        :param sortable: set this to false to turn off sorting for all columns
        :param filter__template:
        :param header__template:
        :param links__template:

        """
        assert columns is not None, 'columns must be specified. It is only set to None to make linting tools not give false positives on the declarative style'

        self._has_prepared = False

        self.data = data
        self.request = request

        if isinstance(self.data, QuerySet):
            kwargs['model'] = data.model

        if isinstance(columns, dict):
            for name, column in columns.items():
                dict.__setitem__(column, 'name', name)
            self.columns = columns.values()
        else:
            self.columns = columns
            """:type : list of Column"""

        self.bound_columns = None
        self.shown_bound_columns = None

        self.Meta = self.get_meta()
        self.Meta.update(**kwargs)

        self.header_levels = None
        self.query = None
        self.query_form = None
        self.query_error = None
        self.bulk_form = None

        self.query_kwargs = extract_subkeys(kwargs, 'query')
        self.bulk_kwargs = extract_subkeys(kwargs, 'bulk')

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
                    value = column.cell_contents(bound_row=bound_row)
                    if prev_value != value:
                        rowspan_by_row[id(bound_row.row)] = 1
                        prev_value = value
                        prev_row = bound_row.row
                    else:
                        rowspan_by_row[id(prev_row)] += 1

                column.cell__attrs['rowspan'] = set_row_span(rowspan_by_row)
                assert 'style' not in column.cell__attrs  # TODO: support both specifying style cell__attrs and auto_rowspan
                column.cell__attrs['style'] = set_display_none(rowspan_by_row)

    def _prepare_evaluate_members(self):
        self.shown_bound_columns = [bound_column for bound_column in self.bound_columns if bound_column.show]

        model = self.Meta.pop('model')  # avoid trying to eval model, since it's callable
        self.Meta = evaluate_recursive(self.Meta, table=self)
        self.Meta.model = model

        if not self.Meta.sortable:
            for bound_column in self.bound_columns:
                bound_column.sortable = False

    def _prepare_sorting(self):
        # sorting
        order = self.request.GET.get('order', None)
        if order is not None:
            is_desc = order[0] == '-'
            order_field = is_desc and order[1:] or order
            sort_column = [x for x in self.shown_bound_columns if x.name == order_field][0]
            order_args = evaluate(sort_column.sort_key, column=sort_column)
            order_args = isinstance(order_args, list) and order_args or [order_args]

            if sort_column.sortable:
                if isinstance(self.data, list):
                    order_by_on_list(self.data, order_args[0], is_desc)
                else:
                    if not settings.DEBUG:
                        # We should crash on invalid sort commands in DEV, but just ignore in PROD
                        # noinspection PyProtectedMember
                        valid_sort_fields = {x.name for x in self.Meta.model._meta.fields}
                        order_args = [order_arg for order_arg in order_args if order_arg.split('__', 1)[0] in valid_sort_fields]
                    order_args = ["%s%s" % (is_desc and '-' or '', x) for x in order_args]
                    self.data = self.data.order_by(*order_args)

    def _prepare_headers(self):
        headers = prepare_headers(self.request, self.shown_bound_columns)

        # The id(header) and the type(x.display_name) stuff is to make None not be equal to None in the grouping
        header_groups = []

        class HeaderGroup(Struct):
            def render_css_class(self):
                return ' '.join(sorted(self.css_class))

        for group_name, group_iterator in groupby(headers, key=lambda header: header.group or id(header)):

            header_group = list(group_iterator)

            header_groups.append(HeaderGroup(
                display_name=group_name,
                sortable=False,
                colspan=len(header_group),
                css_class={'superheader'}))

            for x in header_group:
                x.css_class.add('subheader')
                if x.is_sorting:
                    x.css_class.add('sorted_column')

            header_group[0].css_class.add('first_column')

        header_groups[0].css_class.add('first_column')

        for x in header_groups:
            if type(x.display_name) not in (str, unicode):
                x.display_name = ''
        if all([x.display_name == '' for x in header_groups]):
            header_groups = []

        self.header_levels = [header_groups, headers] if len(header_groups) > 1 else [headers]
        return headers

    # noinspection PyProtectedMember
    def prepare(self, request):
        if self._has_prepared:
            return

        self.request = request

        def bind_columns():
            for index, column in enumerate(self.columns):
                values = evaluate_recursive(Struct(column), table=self, column=column)
                values = merged(values, column=column, table=self, index=index)
                yield BoundColumn(**values)

        self.bound_columns = list(bind_columns())

        self._has_prepared = True

        self._prepare_evaluate_members()
        self._prepare_sorting()
        headers = self._prepare_headers()
        self._prepare_auto_rowspan()

        if self.Meta.model:
            def bulk(column):
                bulk_kwargs = {
                    'name': column.name,
                    'attr': column.attr,
                    'required': False,
                    'empty_choice_tuple': (None, '', '---', True),
                    'model': self.Meta.model,
                    'class': Field.from_model,
                }
                bulk_kwargs.update(column.bulk)
                if bulk_kwargs['class'] == Field.from_model:
                    bulk_kwargs['field_name'] = column.attr
                return bulk_kwargs.pop('class')(**bulk_kwargs)

            def query(column):
                query_kwargs = {
                    'class': Variable,
                    'name': column.name,
                    'gui__label': column.display_name,
                    'attr': column.attr,
                    'model': column.table.Meta.model,
                }
                query_kwargs.update(column.query)
                return query_kwargs.pop('class')(**query_kwargs)

            self.query = Query(request=request, variables=[query(bound_column) for bound_column in self.bound_columns if bound_column.query.show], **self.query_kwargs)
            self.query_form = self.query.form(request) if self.query.variables else None

            self.query_error = ''
            if self.query_form:
                try:
                    self.data = self.data.filter(self.query.to_q())
                except QueryException as e:
                    self.query_error = e.message

            bulk_fields = [bulk(bound_column) for bound_column in self.bound_columns if bound_column.bulk.show]
            self.bulk_form = Form(data=request.POST, fields=bulk_fields, **self.bulk_kwargs) if bulk_fields else None

        return headers, self.header_levels

    def bound_rows(self):
        row_params = extract_subkeys(self.Meta, 'row')
        for i, row in enumerate(self.data):
            yield BoundRow(table=self, row=row, row_index=i, **row_params)

    def render_attrs(self):
        return render_attrs(self.Meta.attrs)

    def render_tbody(self):
        return '\n'.join([bound_row.render() for bound_row in self.bound_rows()])


class Link(Struct):
    """
    Class that describes links to add underneath the table.
    """
    # noinspection PyShadowingBuiltins
    def __init__(self, title, url, show=True, group=None, id=None):
        super(Link, self).__init__(title=title, url=url, show=show, group=group, id=id)

    @staticmethod
    def icon(icon, title, **kwargs):
        return Link(mark_safe('<i class="fa fa-%s"></i> %s' % (icon, title)), **kwargs)


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
    return lambda row, **_: rowspan_by_row[id(row)] if id(row) in rowspan_by_row else ''


def set_display_none(rowspan_by_row):
    return lambda row, **_: 'display: none' if id(row) not in rowspan_by_row else ''


def render_table(request,
                 table,
                 links=None,
                 context=None,
                 template_name='tri_table/list.html',
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
    :param template_name: if you need to render the table differently you can override this parameter
    :param blank_on_empty: turn off the displaying of `{{ empty_message }}` in the template when the list is empty
    :param show_hits: Display how many items there are total in the paginator.
    :param hit_label: Label for the show_hits display.
    :return: a string with the rendered HTML table
    """
    if not context:
        context = {}

    table.prepare(request)

    context['bulk_form'] = table.bulk_form
    context['query_form'] = table.query_form
    context['tri_query_error'] = table.query_error

    if table.bulk_form and request.method == 'POST':
        pks = [key[len('pk_'):] for key in request.POST if key.startswith('pk_')]

        if table.bulk_form.is_valid():
            table.Meta.model.objects.all() \
                .filter(pk__in=pks) \
                .filter(**table.Meta.bulk_filter) \
                .exclude(**table.Meta.bulk_exclude) \
                .update(**{field.name: field.value for field in table.bulk_form.fields if field.value is not None and field.value is not ''})

        return HttpResponseRedirect(request.META['HTTP_REFERER'])

    context = table_context(request,
                            table=table,
                            links=links,
                            paginate_by=paginate_by,
                            page=page,
                            extra_context=context,
                            context_processors=context_processors,
                            paginator=paginator,
                            show_hits=show_hits,
                            hit_label=hit_label)

    if not table.data and blank_on_empty:  # pragma: no cover
        return ''

    return get_template(template_name).render(context)


def render_table_to_response(*args, **kwargs):
    """
    Shortcut for `HttpResponse(render_table(*args, **kwargs))`
    """
    response = render_table(*args, **kwargs)
    if isinstance(response, HttpResponse):  # pragma: no cover
        return response
    return HttpResponse(response)
