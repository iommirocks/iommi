import re
from bs4 import BeautifulSoup
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from iommi import (
    Table,
    middleware,
)
from iommi.base import (
    Traversable,
    no_copy_on_bind,
)
from tri_declarative import (
    dispatch,
    Namespace,
)
from tri_struct import Struct


def reindent(s, before=" ", after="    "):

    def reindent_line(line):
        m = re.match(r'^((' + re.escape(before) + r')*)(.*)', line)
        return after * (len(m.group(1)) // len(before)) + m.group(3)

    return "\n".join(reindent_line(line) for line in s.splitlines())


def remove_csrf(html_code):
    csrf_regex = r'<input[^>]+csrfmiddlewaretoken[^>]+>'
    return re.sub(csrf_regex, '', html_code)


@dispatch(
    table__call_target=Table.from_model,
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
class TestTraversable(Traversable):
    def __init__(self, *, name, children=None):
        super(TestTraversable, self).__init__()
        self.name = name
        self.declared_members = children or {}
        self.bound_members = None

    def children(self):
        return self.bound_members

    def on_bind(self):
        self.bound_members = Struct({k: v.bind(parent=self) for k, v in self.declared_members.items()})
