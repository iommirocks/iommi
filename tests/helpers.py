import re

from bs4 import BeautifulSoup
from django.test import RequestFactory

from iommi import (
    middleware,
    Table,
)
from iommi.base import keys
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
from iommi.struct import Struct
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

        if isinstance(find, dict):
            expected_soup = expected_soup.find(**find)
        else:
            expected_soup = expected_soup.find(find)

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


def no_auth_middleware_req(method, url='/', **data):
    return getattr(RequestFactory(HTTP_REFERER='/'), method.lower())(url, data=data)


def req(method, url='/', **data):
    request = no_auth_middleware_req(method, url=url, **data)
    request.user = Struct(is_staff=False, is_authenticated=False, is_superuser=False)
    return request


def user_req(method, **data):
    request = req(method, **data)
    request.user = Struct(is_staff=False, is_authenticated=True, is_superuser=False)
    return request


def staff_req(method, **data):
    request = req(method, **data)
    request.user = Struct(is_staff=True, is_authenticated=True, is_superuser=True)
    return request


def extract_form_data(content):
    soup = BeautifulSoup(content)

    r = {}
    for input in soup.find_all('input'):
        r[input.get('name')] = input.get('value', '')

    for select in soup.find_all('select'):
        selected = select.find('option', selected='selected')
        if not selected:
            r[select.get('name')] = ''
        else:
            r[select.get('name')] = selected.get('value', '')

    for textarea in soup.find_all('textarea'):
        r[textarea.get('name')] = ''.join(textarea.contents)

    for button in soup.find_all('button'):
        if button.get('name'):
            r[button.get('name')] = button.get('value', '')

    return r


def do_post(form, do_post_key_validation=True, **user_data):
    foo = form.bind(request=req('get')).render_to_response()
    default_data = extract_form_data(foo.content.decode())

    assert 'do_post_key_validation' not in default_data, 'Name collision.'

    if do_post_key_validation:
        for key in user_data.keys():
            virtual_key_for_edit_table_insert = '/-' in key  # keys like "foo/-1"
            assert key in default_data or virtual_key_for_edit_table_insert, f'{key} is not a valid key. Valid keys are: {user_data.keys()}'

    post_data = {**default_data, **user_data}
    assert any(k.startswith('-') for k in keys(post_data)), 'Must be at least one post target. Maybe you forgot .create()/.edit()?'
    return form.bind(request=req('post', **post_data))


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
