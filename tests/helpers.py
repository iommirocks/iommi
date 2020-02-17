import re

from bs4 import BeautifulSoup
from django.test import RequestFactory
from tri_declarative import (
    dispatch,
    Namespace,
)
from tri_struct import Struct

from iommi import (
    Table,
    middleware,
)
from iommi.base import (
    Traversable,
    no_copy_on_bind,
)


def reindent(s, before=" ", after="    "):

    def reindent_line(line):
        m = re.match(r'^((' + re.escape(before) + r')*)(.*)', line)
        return after * (len(m.group(1)) // len(before)) + m.group(3)

    return "\n".join(reindent_line(line) for line in s.splitlines())


def remove_csrf(html_code):
    csrf_regex = r'<input[^>]+csrfmiddlewaretoken[^>]+>'
    return re.sub(csrf_regex, '', html_code)


@dispatch(
    table__call_target=Table,
)
def verify_table_html(*, expected_html, query=None, find=None, table, **kwargs):
    """
    Verify that the table renders to the expected markup, modulo formatting
    """
    if find is None:
        find = dict(class_='table')
        if not expected_html.strip():
            expected_html = "<table/>"

    if isinstance(table, Namespace):
        table = table()

    table: Table

    request = RequestFactory().get("/", query)
    if not table._is_bound:
        table.bind(request=request)

    from django.contrib.auth.models import AnonymousUser
    request.user = AnonymousUser()
    actual_html = remove_csrf(table.__html__(**kwargs))

    expected_soup = BeautifulSoup(expected_html, 'html.parser')
    prettified_expected = reindent(expected_soup.find(**find).prettify()).strip()
    actual_soup = BeautifulSoup(actual_html, 'html.parser')
    hit = actual_soup.find(**find)
    if not hit:
        print(actual_html)
        assert False, f"Couldn't find selector {find} in actual output"
    assert hit, actual_soup
    prettified_actual = reindent(hit.prettify()).strip()

    if prettified_actual != prettified_expected:
        print(actual_html)
    assert prettified_actual == prettified_expected


def request_with_middleware(*, response, data):
    def get_response(request):
        del request
        return response

    m = middleware(get_response)
    return m(request=RequestFactory().get('/', data=data))


def req(method, **data):
    return getattr(RequestFactory(HTTP_REFERER='/'), method.lower())('/', data=data)


def get_attrs(x, attrs):
    return {a: x.attrs.get(a) for a in attrs}


@no_copy_on_bind
class StubTraversable(Traversable):
    def __init__(self, *, _name, members=None):
        super(StubTraversable, self).__init__(_name=_name)
        self._declared_members = members or {}

    def on_bind(self):
        self._bound_members = Struct({k: v.bind(parent=self) for k, v in self._declared_members.items()})


def prettify(content):
    return reindent(BeautifulSoup(content, 'html.parser').prettify().strip())
