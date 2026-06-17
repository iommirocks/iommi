import re

from django.test import RequestFactory

from iommi import (
    Table,
    middleware,
)
from iommi.declarative import declarative
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import Namespace
from iommi.member import (
    bind_members,
    refine_done_members,
)
from iommi.refinable import (
    Refinable,
    RefinableMembers,
)
from iommi.test_helpers import (  # noqa: F401  -- re-exported for backwards compatibility
    do_post,
    extract_form_data,
    no_auth_middleware_req,
    req,
    staff_req,
    user_req,
)
from iommi.traversable import (
    Traversable,
)


def reindent(s, before=" ", after="    "):
    def reindent_line(line):
        m = re.match(r'^((' + re.escape(before) + r')*)(.*)', line)
        return after * (len(m.group(1)) // len(before)) + m.group(3)

    return "\n".join(reindent_line(line) for line in s.splitlines())


def remove_csrf(html_code):
    csrf_regex = r'<input[^>]+csrfmiddlewaretoken[^>]+>'
    return re.sub(csrf_regex, '', html_code)


@dispatch
def verify_table_html(*, table: Table, query=None, find=None, expected_html: str = None):
    if find is None:
        find = dict(class_='table')
        if not expected_html or not expected_html.strip():
            expected_html = "<table class='table'/>"  # pragma: no cover

    verify_part_html(
        part=table,
        query=query,
        find=find,
        expected_html=expected_html,
    )


@dispatch
def verify_part_html(*, part, query=None, find=None, expected_html: str = None):
    if not part._is_bound:
        from django.contrib.auth.models import AnonymousUser

        request = RequestFactory().get("/", query)
        request.user = AnonymousUser()
        part = part.bind(request=request)

    verify_html(
        actual_html=remove_csrf(part.__html__()),
        find=find,
        expected_html=expected_html,
    )


@dispatch
def verify_html(*, actual_html: str, find=None, expected_html: str = None):
    from bs4 import BeautifulSoup

    if expected_html is None:
        expected_html = '<html/>'

    expected_soup = BeautifulSoup(expected_html, 'html.parser')
    actual_soup = BeautifulSoup(actual_html, 'html.parser')

    if find is not None:
        actual_soup_orig = actual_soup
        if isinstance(find, dict):
            actual_soup = actual_soup.find(**find)
        else:
            actual_soup = actual_soup.find(find)

        if not actual_soup:  # pragma: no cover
            prettied_actual = reindent(actual_soup_orig.prettify()).strip()
            print(prettied_actual)
            assert False, f"Couldn't find selector {find} in actual output"

    prettified_actual = reindent(actual_soup.prettify()).strip()
    prettified_expected = reindent(expected_soup.prettify()).strip()
    if prettified_actual != prettified_expected:  # pragma: no cover
        print("Expected")
        print(prettified_expected)
        print("Actual")
        print(prettified_actual)

    assert prettified_actual == prettified_expected


def request_with_middleware(response, request):
    def get_response(request):
        del request
        return response

    m = middleware(get_response)
    return m(request=request)


def call_view_through_middleware(view, request, *args, **kwargs):
    def get_response(request):
        return view(request, *args, **kwargs)

    m = middleware(get_response)
    m.process_view(request, view, args, kwargs)
    return m(request=request)


def get_attrs(x, attrs):
    return {a: x.attrs.get(a) for a in attrs}


class Fruit(Traversable):
    taste = Refinable()


@declarative(Fruit, 'fruits_dict', add_init_kwargs=False)
class Basket(Traversable):
    fruits: Namespace = RefinableMembers()

    def __init__(self, unknown_types_fall_through=False, **kwargs):
        self.unknown_types_fall_through = unknown_types_fall_through
        super(Basket, self).__init__(**kwargs)

    def on_refine_done(self):
        refine_done_members(
            container=self,
            name='fruits',
            members_from_namespace=self.fruits,
            members_from_declared=self.get_declared('fruits_dict'),
            cls=Fruit,
            unknown_types_fall_through=self.unknown_types_fall_through,
        )
        super(Basket, self).on_refine_done()

    def on_bind(self):
        bind_members(container=self, name='fruits')


@declarative(Traversable, 'items_dict', add_init_kwargs=False)
class Box(Traversable):
    items: Namespace = RefinableMembers()

    def __init__(self, unknown_types_fall_through=False, **kwargs):
        self.unknown_types_fall_through = unknown_types_fall_through
        super(Box, self).__init__(**kwargs)

    def on_refine_done(self):
        refine_done_members(
            container=self,
            name='items',
            members_from_namespace=self.items,
            members_from_declared=self.get_declared('items_dict'),
            cls=Basket,
            unknown_types_fall_through=self.unknown_types_fall_through,
        )
        super(Box, self).on_refine_done()

    def on_bind(self):
        bind_members(container=self, name='items')


def prettify(content):
    from bs4 import BeautifulSoup

    return reindent(BeautifulSoup(content, 'html.parser').prettify().strip())
