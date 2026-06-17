"""
Helpers for writing tests against your iommi based frontend.

These functions make it easy to simulate filling out and submitting an
iommi `Form` (or `EditTable`) in your own test suite, without having to
manually figure out which hidden fields, CSRF tokens, and post targets
need to be present in the POST data.
"""

from bs4 import BeautifulSoup
from django.test import RequestFactory

from iommi.base import keys
from iommi.struct import Struct


def no_auth_middleware_req(method, url='/', **data):
    return getattr(RequestFactory(HTTP_REFERER='/'), method.lower())(url, data=data)


def req(method, url='/', **data):
    """
    Build a request without an authenticated user.

    `method` is the HTTP method (`'get'`, `'post'`, ...), and any keyword
    arguments become the request data.
    """
    request = no_auth_middleware_req(method, url=url, **data)
    request.user = Struct(is_staff=False, is_authenticated=False, is_superuser=False)
    return request


def user_req(method, **data):
    """
    Like `req`, but with a request from a normal authenticated user.
    """
    request = req(method, **data)
    request.user = Struct(is_staff=False, is_authenticated=True, is_superuser=False)
    return request


def staff_req(method, **data):
    """
    Like `req`, but with a request from an authenticated staff/superuser.
    """
    request = req(method, **data)
    request.user = Struct(is_staff=True, is_authenticated=True, is_superuser=True)
    return request


def extract_form_data(content):
    """
    Extract the default form data from rendered HTML.

    This reads all `input`, `select`, `textarea`, and `button` elements and
    returns a dict of their names to their current values, which mirrors what
    a browser would post if the form was submitted without any changes.
    """
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


def do_post(form, do_post_key_validation=True, request_builder=req, **user_data):
    """
    Simulate a user filling out and submitting `form`.

    The form is first rendered to extract its default data (hidden fields, CSRF
    token, post target, current values, ...). The values you pass as keyword
    arguments are then merged on top of those defaults, and the form is bound to
    a POST request with the combined data and returned.

    Example::

        form = do_post(MyForm.create(), name='Tab Benoit')
        assert form.is_valid()

    By default the keys you pass are validated against the keys present in the
    rendered form, to catch typos. Pass `do_post_key_validation=False` to turn
    this off (for example when posting to a virtual key on an `EditTable`).

    Use `request_builder` to control how the POST request is constructed (for
    example pass `user_req` or `staff_req` to post as an authenticated user).
    """
    foo = form.bind(request=req('get')).render_to_response()
    default_data = extract_form_data(foo.content.decode())

    assert 'do_post_key_validation' not in default_data, 'Name collision.'

    if do_post_key_validation:
        for key in user_data.keys():
            virtual_key_for_edit_table_insert = '/-' in key  # keys like "foo/-1"
            assert (
                key in default_data or virtual_key_for_edit_table_insert
            ), f'{key} is not a valid key. Valid keys are: {user_data.keys()}'

    post_data = {**default_data, **user_data}
    assert any(
        k.startswith('-') for k in keys(post_data)
    ), 'Must be at least one post target. Maybe you forgot .create()/.edit()?'
    return form.bind(request=request_builder('post', **post_data))
