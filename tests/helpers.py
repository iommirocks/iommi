from bs4 import BeautifulSoup
from django.test import RequestFactory
from tri.tables import render_table_to_response


def verify_table_html(table, expected_html, data=None):
    """
    Verify that the table renders to the expected markup, modulo formatting
    """
    actual_html = str(render_table_to_response(request=RequestFactory().get("/", data), table=table))

    prettified_actual = BeautifulSoup(actual_html).find('table').prettify().strip()
    prettified_expected = BeautifulSoup(expected_html).find('table').prettify().strip()

    assert prettified_expected == prettified_actual
