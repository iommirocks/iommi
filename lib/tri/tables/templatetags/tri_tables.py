from django.conf import settings
from django.db.models import Manager
from django.db.models.query import QuerySet
from django.forms import CheckboxInput
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django import template

register = template.Library()


@register.filter
def table_row_css_class(row, table):
    """
    @type table: tri.tables.BaseTable
    """
    if table is None:
        return ''
    row_css_class = table.Meta.row_attrs.get('class', '')
    if row_css_class:
        return ' ' + (row_css_class(row) if callable(row_css_class) else row_css_class)
    else:
        return ''


@register.filter
def table_cell_url(row, column):
    cell_url = column['cell_url']
    return cell_url(row) if callable(cell_url) else cell_url


@register.filter
def table_cell_url_title(row, column):
    cell_url_title = column['cell_url_title']
    return cell_url_title(row) if callable(cell_url_title) else cell_url_title


@register.filter
def table_cell_attrs(row, column):
    cell_attrs = column.get('cell_attrs')
    return attrs_to_string(row, cell_attrs)


@register.filter
def table_row_attrs(row, attrs):
    attrs = attrs.copy()
    attrs.pop('class', None)
    return attrs_to_string(row, attrs)


def attrs_to_string(row, attrs):
    if not attrs:
        return ''

    def evaluate(item):
        attr, value = item
        value = escape(value(row) if callable(value) else value)
        return ' %s="%s"' % (attr, value) if value else ''

    return mark_safe(''.join(map(evaluate, attrs.items())))


@register.filter
def table_attrs(table):
    def evaluate(item):
        attr, value = item
        value = escape(value() if callable(value) else value)
        return ' %s="%s"' % (attr, value) if value else ''

    return mark_safe(''.join(map(evaluate, table.Meta.attrs.items())))


@register.filter
def row_template(table, row):
    try:
        return table.Meta.row_template(row)
    except TypeError:
        return table.Meta.row_template
    except AttributeError:
        return 'tri_tables/table_row.html'


def lookup_attribute(column, row):
    attribute_path = column.attr
    try:
        obj = row
        for attribute_name in attribute_path.split('__'):
            obj = getattr(obj, attribute_name)
            if obj is None:
                return
        return obj
    except AttributeError:
        if hasattr(row, '__getitem__'):
            try:
                return row[attribute_path]
            except (TypeError, KeyError):
                try:
                    return row[column.index]
                except (TypeError, KeyError, IndexError):
                    pass
    return settings.TEMPLATE_STRING_IF_INVALID


def yes_no_formatter(value):
    """ Handle True/False from Django model and 1/0 from raw sql """
    if value is True or value == 1:
        return 'Yes'
    if value is False or value == 0:
        return 'No'
    if value is None:
        return ''
    assert False, "Unable to convert {} to Yes/No".format(value)


def list_formatter(value):
    return ', '.join([unicode(x) for x in value])


_cell_formatters = {
    bool: yes_no_formatter,
    tuple: list_formatter,
    list: list_formatter,
    set: list_formatter,
    QuerySet: lambda value: list_formatter(list(value))
}


def register_cell_formatter(type_or_class, formatter):
    global _cell_formatters
    _cell_formatters[type_or_class] = formatter


@register.filter
def table_cell_formatter(row, column):
    """
    @type column: tri.tables.Column
    """
    if 'cell_value' in column:
        value = column.cell_value(row) if callable(column.cell_value) else column.cell_value
    else:
        row = lookup_attribute(column, row)
        if row is None:
            return ''
        value = row

    if 'cell_format' in column:
        return column.cell_format(value) if callable(column.cell_format) else column.cell_format

    if isinstance(value, Manager):
        value = value.all()

    formatter = _cell_formatters.get(type(value))
    if formatter:
        value = formatter(value)

    if value is None:
        return ''

    return value


def paginator(context, adjacent_pages=6):
    """Adds pagination context variables for first, adjacent and next page links
    in addition to those already populated by the object_list generic view."""
    page = context["page"]
    if page <= adjacent_pages:
        page = adjacent_pages + 1
    elif page > context["pages"] - adjacent_pages:
        page = context["pages"] - adjacent_pages
    page_numbers = [n for n in
                    range(page - adjacent_pages, page + adjacent_pages + 1)
                    if 0 < n <= context["pages"]]

    get = context['request'].GET.copy() if 'request' in context else {}
    if 'page' in get:
        del get['page']

    return {
        "extra": get and (get.urlencode() + "&") or "",
        "hits": context["hits"],
        "results_per_page": context["results_per_page"],
        "page": context["page"],
        "pages": context["pages"],
        "page_numbers": page_numbers,
        "next": context["next"],
        "previous": context["previous"],
        "has_next": context["has_next"],
        "has_previous": context["has_previous"],
        "show_first": 1 not in page_numbers,
        "show_last": context["pages"] not in page_numbers,
        "show_hits": context["show_hits"],
        "hit_label": context["hit_label"],
    }
register.inclusion_tag("tri_tables/paginator.html", takes_context=True)(paginator)


@register.filter()
def as_compact(form):
    r = []
    for field in form.fields:
        r.append(render_to_string('tri_tables/compact_form_row.html', {'field': form[field]}))
    return mark_safe('\n'.join(r))


@register.filter(name='is_checkbox')
def is_checkbox(field):
    try:
        return isinstance(field.field.widget, CheckboxInput)
    except AttributeError:
        pass
    return False
