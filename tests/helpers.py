from bs4 import BeautifulSoup
from django.test import RequestFactory
from tri.tables import render_table_to_response, render_table


def verify_table_html(table, expected_html, query=None):
    """
    Verify that the table renders to the expected markup, modulo formatting
    """
    actual_html = render_table(request=RequestFactory().get("/", query), table=table)

    prettified_actual = BeautifulSoup(u"<html>{}</html>".format(actual_html)).find('table').prettify().strip()
    prettified_expected = BeautifulSoup(expected_html).find('table').prettify().strip()

    assert prettified_expected == prettified_actual
