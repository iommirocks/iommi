import re
from bs4 import BeautifulSoup
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from tri.tables import render_table


def reindent(s, before=" ", after="    "):

    def reindent_line(line):
        m = re.match(r'^((' + re.escape(before) + r')*)(.*)', line)
        return after * (len(m.group(1)) / len(before)) + m.group(3)

    return "\n".join(reindent_line(line) for line in s.splitlines())


def verify_table_html(table, expected_html, query=None, find=None, links=None):
    """
    Verify that the table renders to the expected markup, modulo formatting
    """
    if not find:
        find = dict(name='table')
        if not expected_html.strip():
            expected_html = "<table/>"

    request = RequestFactory().get("/", query)
    request.user = AnonymousUser()
    actual_html = render_table(request=request, table=table, links=links)

    prettified_actual = reindent(BeautifulSoup(actual_html).find(**find).prettify()).strip()
    prettified_expected = reindent(BeautifulSoup(expected_html).find(**find).prettify()).strip()

    assert prettified_expected == prettified_actual
