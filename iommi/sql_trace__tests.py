from datetime import (
    date,
    datetime,
)

import pytest
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.urls import path
from tri_struct import Struct

from iommi.sql_trace import (
    colorize,
    get_sql_debug,
    no_sql_debug,
    safe_unicode_literal,
    set_sql_debug,
    sql_debug_format_stack_trace,
)


def bogus_view(request):
    list(User.objects.filter(username='foo'))
    return HttpResponse('unseen')


urlpatterns = [
    path('', bogus_view)
]


@pytest.mark.django_db
def test_middleware(settings, client):
    settings.ROOT_URLCONF = __name__
    settings.DEBUG = True

    response = client.get('/?_iommi_sql_trace')

    content = response.content.decode().replace('&quot;', '"')
    assert 'unseen' not in content

    assert '1 queries' in content
    # noinspection SqlResolve
    assert 'SELECT "auth_user"."id", "auth_user"."password", "auth_user"."last_login", "auth_user"."is_superuser", "auth_user"."username", "auth_user"."first_name", "auth_user"."last_name", "auth_user"."email", "auth_user"."is_staff", "auth_user"."is_active", "auth_user"."date_joined" FROM "auth_user" WHERE "auth_user"."username"' in content
    assert '<span style="color: green; font-weight: bold">SELECT</span>' in content


@pytest.mark.parametrize('text, fg, bold, expected', [
    ('foo', None, False, 'foo'),
    ('foo', 'red', False, '<span style="color: red">foo</span> '),
    ('foo', None, True, '<span style="font-weight: bold">foo</span> '),
    ('foo', 'red', True, '<span style="color: red; font-weight: bold">foo</span> '),
])
def test_colorize(text, fg, bold, expected):
    assert colorize(text, fg, bold) == expected


@pytest.mark.parametrize('params, expected', [
    (None, (1, 2, 3)),
    ([1, 2, 3], (1, 2, 3)),
    ((1, 2, 3), (1, 2, 3)),
    (1, '1'),
    (1.5, '1.5'),
    (date(2020, 1, 3), "'2020-01-03'"),
    (datetime(2020, 1, 3, 13, 37), "'2020-01-03 13:37'"),
    ({'foo': 1.5}, {'foo': '1.5'}),
    (b'foo', 'foo'),
])
def test_safe_unicode_literal(params, expected):
    assert safe_unicode_literal(params), expected


def test_set_sql_debug():
    with pytest.raises(AssertionError):
        set_sql_debug('invalid')

    set_sql_debug('None')
    assert get_sql_debug() is None

    set_sql_debug('worst')
    assert get_sql_debug() == 'worst'

    with no_sql_debug():
        assert get_sql_debug() is None

    assert get_sql_debug() == 'worst'


def test_sql_debug_format_stack_trace():
    frame2 = Struct(
        f_lineno=1,
        f_back=None,
        f_locals={
            'bit': 'django_template_bit',
        },
        f_code=Struct(
            co_name='_resolve_lookup',
            co_filename='foo.py',
        ),
    )
    frame1 = Struct(
        f_lineno=1,
        f_back=frame2,
        f_code=Struct(
            co_name='f',
            co_filename='/lib/python/foo.py',
        ),
    )
    frame0 = Struct(
        f_lineno=1,
        f_back=frame1,
        f_code=Struct(
            co_name='f',
            co_filename='foo.py',
        ),
    )
    frame = Struct(
        f_lineno=1,
        f_back=frame0,
        f_code=Struct(
            co_name='f',
            co_filename='foo2.py',
        ),
    )

    expected = """  File "foo2.py", line 1, in f => \n  File "foo.py", line 1, in f => \n  File "foo.py", line 1, in _resolve_lookup => (looking up: django_template_bit)"""
    assert sql_debug_format_stack_trace(frame) == expected
