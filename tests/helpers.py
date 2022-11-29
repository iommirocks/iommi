import inspect
import os.path
import re
from os import (
    makedirs,
)
from pathlib import Path
from uuid import uuid4

from django.test import RequestFactory
from iommi.struct import Struct

from iommi import (
    middleware,
    render_if_needed,
    Table,
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
        if not expected_html.strip():
            expected_html = "<table/>"  # pragma: no cover

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

    if find is None:
        find = dict()
    hit = actual_soup.find(**find)
    if not hit:  # pragma: no cover
        prettied_actual = reindent(actual_soup.prettify()).strip()
        print(prettied_actual)
        assert False, f"Couldn't find selector {find} in actual output"

    prettified_hit = reindent(hit.prettify()).strip()
    prettified_expected = reindent(expected_soup.find(**find).prettify()).strip()
    if prettified_hit != prettified_expected:  # pragma: no cover
        print(prettified_hit)

    assert prettified_hit == prettified_expected


def request_with_middleware(response, request):
    def get_response(request):
        del request
        return response

    m = middleware(get_response)
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


def _show_relative_path_from_name(name):
    return Path('doc_includes') / (name.replace('/', os.path.sep) + '.html')


def _show_path_from_name(name):
    return Path(__file__).parent.parent / 'docs' / 'custom' / _show_relative_path_from_name(name)


_show_output_used = set()


def show_output(part, path='/'):
    frame = inspect.currentframe().f_back
    base_name = os.path.join(
        Path(frame.f_code.co_filename).stem.replace('test_', '').replace('doc_', '').replace('_api_', ''), frame.f_code.co_name
    )
    name = base_name
    counter = 0
    while name in _show_output_used:
        counter += 1
        name = f'{base_name}{counter}'
    _show_output_used.add(name)

    file_path = _show_path_from_name(name)
    makedirs(file_path.parent, exist_ok=True)
    with open(file_path, 'wb') as f:
        content = part if isinstance(part, bytes) else render_if_needed(req('get', path=path), part).content
        f.write(content)
        return content


# This synonym exists to have a different name for make_doc_rsts.py
show_output_collapsed = show_output


def create_iframe(name, collapsed):
    uuid = uuid4()
    file_path = _show_relative_path_from_name(name)
    text = '► Show result' if collapsed else '▼ Hide result'
    display = 'none' if collapsed else ''
    return f'''
        <div class="iframe_collapse" onclick="toggle('{uuid}', this)">{text}</div>
        <iframe id="{uuid}" src="{file_path}" style="background: white; display: {display}; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    '''
