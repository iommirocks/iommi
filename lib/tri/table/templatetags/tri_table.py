from __future__ import absolute_import
from __future__ import unicode_literals

from django import template

register = template.Library()


def paginator(context, adjacent_pages=6):
    """Adds pagination context variables for first, adjacent and next page links
    in addition to those already populated by the object_list generic view."""
    page = context["page"]
    assert page != 0  # pages are 1-indexed!
    if page <= adjacent_pages:
        page = adjacent_pages + 1
    elif page > context["pages"] - adjacent_pages:  # pragma: no cover
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


register.inclusion_tag("tri_table/paginator.html", takes_context=True)(paginator)
