from django.conf import settings
from django.db.models import Manager
from django.db.models.query import QuerySet
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django import template

register = template.Library()

@register.filter
def table_row_css_class(obj, table):
    """
    @type table: tri.tables.BaseTable
    """
    if table is None:
        return ''
    callable_or_string = table.row_css_class
    if callable_or_string:
        return callable_or_string(obj) if callable(callable_or_string) else callable_or_string
    else:
        return ''


@register.filter
def header_cell_url(obj, header):
    x = header['cell_url']
    return x(obj) if callable(x) else x


@register.filter
def header_cell_url_title(obj, header):
    x = header['cell_url_title']
    return x(obj) if callable(x) else x


@register.filter
def header_cell_attrs(obj, header):
    attrs = header.get('cell_attrs')
    return header_row_attrs(obj, attrs)


@register.filter
def header_row_attrs(obj, attrs):
    if not attrs:
        return ''

    def evaluate(attr, value):
        value = escape(value(obj) if callable(value) else value)
        return '%s="%s"' % (attr, value) if value else ''

    return mark_safe(' ' + ' '.join([evaluate(attr, value) for attr, value in attrs.items()]))


@register.filter
def table_attrs(table):
    def evaluate(attr, value):
        value = escape(value() if callable(value) else value)
        return '%s="%s"' % (attr, value) if value else ''

    return mark_safe(' ' + ' '.join([evaluate(attr, value) for attr, value in table.attrs.items()]))


def lookup_attribute(attribute_path, obj):
    for attribute_name in attribute_path.split('__'):
        obj = getattr(obj, attribute_name, settings.TEMPLATE_STRING_IF_INVALID)
        if obj is None:
            break
    return obj


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
def header_cell_formatter(obj, header):
    if 'cell_value' in header:
        value = header.cell_value(obj) if callable(header.cell_value) else header.cell_value
    else:
        obj = lookup_attribute(header['name'], obj)
        if obj is None:
            return ''
        value = obj

    if 'cell_format' in header:
        return header.cell_format(value) if callable(header.cell_format) else header.cell_format

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

    get = context['request'].GET.copy()
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
register.inclusion_tag("paginator.html", takes_context=True)(paginator)

@register.filter()
def as_compact(form):
    r = []
    for field in form.fields:
        r.append(render_to_string('compact_form_row.html', {'field': form[field]}))
    return mark_safe('\n'.join(r))
