# coding: utf-8
from copy import copy
from itertools import groupby
import itertools
from django import forms
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage
from django.db.models.query import QuerySet
from django.forms import fields
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string, get_template
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from tri.declarative import declarative, creation_ordered, with_meta
from tri.struct import Struct
from tri.tables.templatetags.tri_tables import lookup_attribute, yes_no_formatter, table_cell_formatter


__version__ = '0.10.0'

next_creation_count = itertools.count().next


def prepare_headers(request, columns):
    columns = [copy(column) for column in columns if column.get('show', True)]
    for column in columns:
        if column.get('sortable', True):
            params = request.GET.copy()
            order = request.GET.get('order', None)
            if order is not None:
                is_desc = len(order) > 0 and order[0] == '-'
                order_field = is_desc and order[1:] or order
                new_order = is_desc and order[1:] or "-%s" % order
                if order is not None and order_field == column['name']:
                    params['order'] = new_order
                else:
                    params['order'] = column['name']
            else:
                params['order'] = column['name']
            column['is_sorting'] = False if order is None else (column['name'] == order or ('-' + column['name']) == order)
            column['url'] = "?%s" % params.urlencode()
        column['show'] = column.get('show', True)
    return columns


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

    property_path = order_field.split('__')

    def get_property(p):
        p = getattr(p, property_path[0])
        if callable(p):
            p = p()
        for prop in property_path[1:]:
            try:
                p = getattr(p, prop)
                if callable(p):
                    p = p()
            except AttributeError:  # pragma: no cover
                if settings.DEBUG:
                    raise
                return p
        return p
    objects.sort(key=get_property, reverse=is_desc)


@creation_ordered
class Column(Struct):
    """
    Class that describes a column, i.e. the text of the header, how to get and display the data in the cell, etc.
    """

    # noinspection PyShadowingBuiltins
    def __init__(self,
                 name=None,
                 attr=None,
                 display_name=None,
                 css_class=None,
                 url=None,
                 title=None,
                 show=True,
                 sortable=True,
                 sort_key=None,
                 group=None,
                 filter=True,
                 filter_show=True,
                 filter_field=None,
                 filter_choices=None,
                 filter_type=None,
                 bulk=False,
                 bulk_field=None,
                 bulk_choices=None,
                 auto_rowspan=False,

                 cell_template=None,
                 cell_value=None,
                 cell_format=None,
                 cell_attrs=None,
                 cell_url=None,
                 cell_url_title=None,):
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
        :param group: string describing the group of the header. If this parameter is used the header of the table now has two rows. Consecutive identical groups on the first level of the header are joined in a nice way.
        :param filter: set to false to disable filtering of this column.
        :param filter_show: set to false to hide the filtering component for this column. Sometimes it's useful to allow filtering via the URL to get direct linking but you don't want the GUI added.
        :param filter_field: a django field to use for the filter GUI. Use this if the default isn't what you wanted.
        :param filter_choices: an iterable of choices or a QuerySet of choices to be available for filtering. This is a short form for using filter_field and specifying the entire field yourself.
        :param filter_type: by default the filtering is exact, but you can use `Column.FILTER_TYPES.CONTAINS` to make it a contains match and `Column.FILTER_TYPES.ICONTAINS` for case insensitive contains matching.
        :param bulk: enable bulk editing for this column
        :param bulk_field: a django field to use for the filter GUI. Use this if the default isn't what you wanted.
        :param bulk_choices: an iterable of choices or a QuerySet of choices to be available for bulk editing. This is a short form for using bulk_field and specifying the entire field yourself.
        :param auto_rowspan: enable automatic rowspan for this column. To join two cells with rowspan, just set this auto_rowspan to True and make those two cells output the same text and we'll handle the rest.
        :param cell_template: name of a template file. The template gets two arguments: `row` and `user`.
        :param cell_value: string or callable with one argument: the row. This is used to extract which data to display from the object.
        :param cell_format: string or callable with one argument: the value. This is used to convert the extracted data to html output (use `mark_safe`) or a string.
        :param cell_attrs: dict of attr name to callable with one argument: the row
        :param cell_url: callable with one argument: the row
        :param cell_url_title: callable with one argument: the row
        """
        self.table = None  # this member is filled in by the table after it is constructed

        self.creation_count = next_creation_count()

        if cell_template is not None:
            assert cell_format is None
            assert cell_value is None or callable(cell_value)
            orig_cell_value = cell_value
            cell_value = lambda row: dict(row=row,
                                          user=self.table.request.user if self.table.request else None,
                                          **(orig_cell_value(row) if orig_cell_value is not None else {}))
            cell_format = lambda bindings: render_to_string(cell_template, bindings)
        if name:
            self._set_name(name)
        values = {k: v for k, v in dict(
            name=name,
            attr=attr,
            display_name=display_name,
            css_class=CssClass(css_class),
            url=url,
            title=title,
            show=show,
            sortable=sortable,
            sort_key=sort_key,
            group=group,
            filter=filter,
            filter_show=filter_show,
            filter_field=filter_field,
            filter_choices=filter_choices,
            filter_type=filter_type,
            bulk=bulk,
            bulk_field=bulk_field,
            bulk_choices=bulk_choices,
            auto_rowspan=auto_rowspan,

            cell_value=cell_value,
            cell_format=cell_format,
            cell_attrs=cell_attrs if cell_attrs is not None else {},
            cell_url=cell_url,
            cell_url_title=cell_url_title).items()
            if v is not None}

        super(Column, self).__init__(**values)

    FILTER_TYPES = Struct({
        'ICONTAINS': Struct({'django_query_suffix': 'icontains'}),
        'CONTAINS': Struct({'django_query_suffix': 'contains'})
    })

    def _set_name(self, name):
        self.name = name
        self.attr = getattr(self, 'attr', name)
        self.sort_key = getattr(self, 'sort_key', self.attr)
        self.display_name = getattr(self, 'display_name', force_unicode(name).rsplit('__', 1)[-1].replace("_", " ").capitalize())

    @staticmethod
    def icon(icon, is_report=False, icon_title='', show=True, **kwargs):
        """
        Shortcut to create font awesome-style icons.

        :param icon: the font awesome name of the icon
        """
        params = dict(
            name='',
            display_name='',
            sortable=False,
            css_class='thin',
            show=show and not is_report,
            title=icon_title,
            filter=False,
            cell_value=lambda row: True,
            cell_attrs={'class': 'cj'},
            cell_format=lambda value: mark_safe('<i class="fa fa-lg fa-%s"%s></i>' % (icon, ' title="%s"' % icon_title if icon_title else '')) if value else '')
        params.update(kwargs)
        return Column(**params)

    @staticmethod
    def edit(is_report=False, **kwargs):
        """
        Shortcut for creating a clickable edit icon. The URL defaults to `your_object.get_absolute_url() + 'edit/'`. Specify the option cell_url to override.
        """
        params = dict(
            cell_url=lambda row: row.get_absolute_url() + 'edit/',
            display_name=''
        )
        params.update(kwargs)
        return Column.icon('pencil-square-o', is_report, 'Edit', **params)

    @staticmethod
    def delete(is_report=False, **kwargs):
        """
        Shortcut for creating a clickable delete icon. The URL defaults to `your_object.get_absolute_url() + 'delete/'`. Specify the option cell_url to override.
        """
        params = dict(
            cell_url=lambda row: row.get_absolute_url() + 'delete/',
            display_name=''
        )
        params.update(kwargs)
        return Column.icon('trash-o', is_report, 'Delete', **params)

    @staticmethod
    def download(is_report=False, **kwargs):
        """
        Shortcut for creating a clickable download icon. The URL defaults to `your_object.get_absolute_url() + 'download/'`. Specify the option cell_url to override.
        """
        params = dict(
            cell_url=lambda row: row.get_absolute_url() + 'download/',
            cell_value=lambda row: getattr(row, 'pk', False),
        )
        params.update(kwargs)
        return Column.icon('download', is_report, 'Download', **params)

    @staticmethod
    def run(is_report=False, show=True, **kwargs):
        """
        Shortcut for creating a clickable run icon. The URL defaults to `your_object.get_absolute_url() + 'run/'`. Specify the option cell_url to override.
        """
        params = dict(
            name='',
            title='Run',
            sortable=False,
            css_class='thin',
            cell_url=lambda row: row.get_absolute_url() + 'run/',
            cell_value='Run',
            show=show and not is_report,
            filter=False,
        )
        params.update(kwargs)
        return Column(**params)

    @staticmethod
    def select(is_report=False, checkbox_name='pk', show=True, checked=lambda x: False, **kwargs):
        """
        Shortcut for a column of checkboxes to select rows. This is useful for implementing bulk operations.

        :param checkbox_name: the name of the checkbox. Default is "pk", resulting in checkboxes like "pk_1234".
        :param checked: callable to specify if the checkbox should be checked initially. Defaults to False.
        """
        params = dict(
            name='__select__',
            title='Select all',
            display_name=mark_safe('<i class="fa fa-check-square-o"></i>'),
            sortable=False,
            show=show and not is_report,
            filter=False,
            css_class='thin nopad',
            cell_attrs={'class': 'cj'},
            cell_value=lambda row: mark_safe('<input type="checkbox"%s class="checkbox" name="%s_%s" />' % (' checked' if checked(row.pk) else '', checkbox_name, row.pk)),
        )
        params.update(kwargs)
        return Column(**params)

    @staticmethod
    def check(is_report=False, **kwargs):
        """
        Shortcut to render booleans as a check mark if true or blank if false.
        """
        def render_icon(value):
            if callable(value):
                value = value()
            return mark_safe('<i class="fa fa-check" title="Yes"></i>') if value else ''

        params = dict(
            cell_format=yes_no_formatter if is_report else render_icon,
            cell_attrs={'class': 'cj'},
        )
        params.update(kwargs)
        return Column(**params)

    @staticmethod
    def link(**kwargs):
        """
        Shortcut for creating a cell that is a link. The URL is the result of calling `get_absolute_url()` on the object.
        """
        column = None  # Filled in later

        def url(row):
            r = lookup_attribute(column, row)
            return r.get_absolute_url() if r else ''

        params = dict(
            cell_url=url,
            filter=False,
        )
        params.update(kwargs)
        column = Column(**params)
        return column

    @staticmethod
    def number(**kwargs):
        """
        Shortcut for rendering a number. Sets the "rj" (as in "right justified") CSS class on the cell and header.
        """
        if 'cell_attrs' not in kwargs:
            kwargs['cell_attrs'] = {}
        if 'class' not in kwargs['cell_attrs']:
            kwargs['cell_attrs']['class'] = 'rj'
        return Column(**kwargs)


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
        attrs = {}
        row_attrs = {}
        bulk_filter = {}
        bulk_exclude = {}
        sortable = True
        row_template = 'tri_tables/table_row.html'

    """
    :param data: a list of QuerySet of objects
    :param columns: (use this only when not using the declarative style) a list of Column objects
    :param attrs: dict of strings to string/callable of HTML attributes to apply to the table
    :param row_attrs: dict of strings to string/callable of HTML attributes to apply to the row. Callables are passed the row as argument.
    :param bulk_filter: filters to apply to the QuerySet before performing the bulk operation
    :param bulk_exclude: exclude filters to apply to the QuerySet before performing the bulk operation
    :param sortable: set this to false to turn off sorting for all columns
    """
    def __init__(self, data, columns, **params):
        self.data = data

        if isinstance(columns, dict):
            for name, column in columns.items():
                column._set_name(name)
            self.columns = columns.values()
        else:
            self.columns = columns

        for index, column in enumerate(self.columns):
            column.table = self
            column.index = index

        self.Meta = self.get_meta()
        self.Meta.update(**params)

        if not self.Meta.sortable:
            for column in self.columns:
                column.sortable = False

        self.Meta.attrs.setdefault('class', 'listview')

        self.header_levels = None

    # noinspection PyProtectedMember
    def prepare_headers_and_sort(self, request):
        order = request.GET.get('order', None)
        if order is not None:
            is_desc = order[0] == '-'
            order_field = is_desc and order[1:] or order
            sort_column = [x for x in self.columns if x.get('name', None) == order_field][0]
            order_args = sort_column.get('sort_key', sort_column['name'])
            order_args = isinstance(order_args, list) and order_args or [order_args]

            if sort_column.get('sortable', True):
                if isinstance(self.data, list):
                    order_by_on_list(self.data, order_args[0], is_desc)
                else:
                    if not settings.DEBUG:
                        # We should crash on invalid sort commands in DEV, but just ignore in PROD
                        valid_sort_fields = {x.name for x in self.data.model._meta.fields}
                        order_args = [order_arg for order_arg in order_args if order_arg.split('__', 1)[0] in valid_sort_fields]
                    order_args = ["%s%s" % (is_desc and '-' or '', x) for x in order_args]
                    self.data = self.data.order_by(*order_args)
        headers = prepare_headers(request, self.columns)

        # The id(header) and the type(x.display_name) stuff is to make None not be equal to None in the grouping
        header_groups = []
        for group_name, group_iterator in groupby(headers, key=lambda header: header.get('group', id(header))):

            header_group = list(group_iterator)

            header_groups.append(Struct(display_name=group_name,
                                        sortable=False,
                                        colspan=len(header_group),
                                        css_class=CssClass('superheader')))

            for x in header_group:
                x.css_class.add('subheader')
                if x.get('is_sorting'):
                    x.css_class.add('sorted_column')

            header_group[0].css_class.add('first_column')

        header_groups[0].css_class.add('first_column')

        for x in header_groups:
            if type(x.display_name) not in (str, unicode):
                x.display_name = ''
        if all([x.display_name == '' for x in header_groups]):
            header_groups = []

        self.header_levels = [header_groups, headers] if len(header_groups) > 1 else [headers]

        return headers, self.header_levels


class CssClass(object):

    def __init__(self, s):
        self.parts = s.split(' ') if s else []

    def add(self, c):
        if c not in self.parts:
            self.parts.append(c)

    def __str__(self):
        return " ".join(self.parts)


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


def object_list_context(request,
                        table,
                        links=None,
                        paginate_by=None,
                        page=None,
                        extra_context=None,
                        context_processors=None,
                        paginator=None,
                        show_hits=False,
                        hit_label='Items'):
    if extra_context is None:  # pragma: no cover
        extra_context = {}

    grouped_links = {}
    if links is not None:
        links = [link for link in links if link.show and link.url]

        grouped_links = groupby((link for link in links if link.group is not None), key=lambda l: l.group)
        grouped_links = [(g, slugify(g), list(lg)) for g, lg in grouped_links]  # because django templates are crap!

        links = [link for link in links if link.group is None]

    table.prepare_headers_and_sort(request)

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
    auto_rowspan_columns = [column for column in table.columns if column.auto_rowspan]

    if auto_rowspan_columns:
        table.data = list(table.data)
        no_value_set = object()
        for column in auto_rowspan_columns:
            rowspan_by_row = {}  # cells for rows in this dict are displayed, if they're not in here, they get style="display: none"
            prev_value = no_value_set
            prev_row = no_value_set
            for row in table.data:
                value = table_cell_formatter(row, column)
                if prev_value != value:
                    rowspan_by_row[id(row)] = 1
                    prev_value = value
                    prev_row = row
                else:
                    rowspan_by_row[id(prev_row)] += 1

            column.cell_attrs['rowspan'] = set_row_span(rowspan_by_row)
            assert 'style' not in column.cell_attrs  # TODO: support both specifying style cell_attrs and auto_rowspan
            column.cell_attrs['style'] = set_display_none(rowspan_by_row)

    base_context.update(extra_context)
    return RequestContext(request, base_context, context_processors)


def set_row_span(rowspan_by_row):
    return lambda row: rowspan_by_row[id(row)] if id(row) in rowspan_by_row else ''


def set_display_none(rowspan_by_row):
    return lambda row: 'display: none' if id(row) not in rowspan_by_row else ''


def render_table_filters(request, table):
    filter_fields = [(col.name, col.get('filter_type')) for col in table.columns if col.filter]
    if request.method == 'GET' and filter_fields and hasattr(table.data, 'model'):
        column_by_name = {col.name: col for col in table.columns}

        for name, filter_type in filter_fields:
            if name in request.GET and request.GET[name]:
                col = column_by_name[name]
                if filter_type:
                    table.data = table.data.filter(**{col.attr + '__' + filter_type.django_query_suffix: request.GET[name]})
                else:
                    table.data = table.data.filter(**{col.attr: request.GET[name]})

        filtered_columns_with_ui = [col for col in table.columns if col.filter and col.filter_show]

        class FilterForm(forms.Form):
            def __init__(self, *args, **kwargs):
                super(FilterForm, self).__init__(*args, **kwargs)
                for column in filtered_columns_with_ui:
                    filter_field = column.get('filter_field')
                    if 'filter_choices' in column and not filter_field:
                        filter_choices = column.filter_choices
                        if isinstance(filter_choices, QuerySet):
                            filter_choices = [(x.pk, x) for x in filter_choices]
                        if ('', '') not in filter_choices:
                            filter_choices = [('', '')] + filter_choices
                        filter_field = forms.ChoiceField(choices=filter_choices)
                    if filter_field:
                        self.fields[column.name] = filter_field
                    else:
                        model = table.data.model
                        attr = column.attr
                        last_name = attr.split('__')[-1]
                        for x in attr.split('__')[:-1]:
                            try:
                                model = getattr(model, x).get_queryset().model
                            except AttributeError:  # pragma: no cover
                                # Support for old Django versions
                                model = getattr(model, x).get_query_set().model
                        field_by_name = forms.fields_for_model(model)
                        self.fields[column.name] = field_by_name[last_name]
                        self.fields[column.name].label = column.display_name

                for field_name, field in self.fields.items():
                    if isinstance(field, fields.BooleanField):
                        self.fields[field_name] = forms.ChoiceField(label=field.label, help_text=field.help_text, required=False, choices=[('', ''), ('1', 'Yes'), ('0', 'No')])
                        self.fields[field_name].creation_counter = field.creation_counter

                for field in self.fields.values():
                    field.required = False
                    field.blank = True
                    field.null = True
                    if hasattr(field, 'choices') and type(field.choices) in (list, tuple) and field.choices[0] != ('', ''):
                        field.choices = [('', '')] + field.choices

        filter_form = FilterForm(request.GET)
        filter_form._errors = {}
        return filter_form


def render_table(request,
                 table,
                 links=None,
                 context=None,
                 template_name='tri_tables/list.html',
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
    context['filter_form'] = render_table_filters(request, table)

    table.request = request

    bulk_form = None
    bulk_fields = [x.name for x in table.columns if x.bulk]
    if bulk_fields:
        column_by_name = {column.name: column for column in table.columns if column.bulk}

        class BulkForm(forms.ModelForm):
            class Meta:
                model = table.data.model
                fields = bulk_fields

            def __init__(self, *args, **kwargs):
                super(BulkForm, self).__init__(*args, **kwargs)
                for name, column in {k: v for k, v in column_by_name.items() if 'bulk_field' in v}.items():
                    self.fields[name] = column.bulk_field

                for field_name, field in self.fields.items():
                    field.required = False
                    field.blank = True
                    field.null = True
                    if hasattr(field, 'choices'):
                        if 'bulk_choices' in column_by_name[field_name]:
                            choices = column_by_name[field_name].bulk_choices
                        else:
                            choices = field.choices

                        if isinstance(choices, QuerySet):
                            choices = [(c.pk, c) for c in choices]
                        if ('', '') not in choices:
                            choices = [('', '')] + list(choices)
                        field.choices = choices
        bulk_form = BulkForm

    if bulk_form:
        if request.method == 'POST':
            pks = [key[len('pk_'):] for key in request.POST if key.startswith('pk_')]

            f = bulk_form(request.POST)
            if f.is_valid():
                table.data \
                    .filter(pk__in=pks) \
                    .filter(**table.Meta.bulk_filter) \
                    .exclude(**table.Meta.bulk_exclude) \
                    .update(**{k: v for k, v in f.cleaned_data.items() if v is not None and v is not ''})

            return HttpResponseRedirect(request.META['HTTP_REFERER'])
        else:
            context['bulk_form'] = bulk_form()

    context = object_list_context(request,
                                  table=table,
                                  links=links,
                                  paginate_by=paginate_by,
                                  page=page,
                                  extra_context=context,
                                  context_processors=context_processors,
                                  paginator=paginator,
                                  show_hits=show_hits,
                                  hit_label=hit_label)

    if not table.data and blank_on_empty:
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
