from bs4 import BeautifulSoup
from django.test import RequestFactory
from tri.tables import render_table


def verify_table_html(table, expected_html, query=None, find=None, links=None):
    """
    Verify that the table renders to the expected markup, modulo formatting
    """
    if not find:
        find = dict(name='table')
    actual_html = render_table(request=RequestFactory().get("/", query), table=table, links=links)

    prettified_actual = BeautifulSoup(actual_html).find(**find).prettify().strip()
    prettified_expected = BeautifulSoup(expected_html).find(**find).prettify().strip()

    assert prettified_expected == prettified_actual
