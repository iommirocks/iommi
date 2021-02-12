import logging
import re
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
    format_sql,
    get_sql_debug,
    no_sql_debug,
    safe_unicode_literal,
    set_sql_debug,
    sql_debug_format_stack_trace,
    SQL_DEBUG_LEVEL_ALL_WITH_STACKS,
    SQL_DEBUG_LEVEL_WORST,
    sql_debug_log_to_request,
    sql_debug_total_time,
    sql_debug_trace_sql,
)
from iommi.thread_locals import set_current_request
from tests.helpers import req


def bogus_view(request):
    list(User.objects.filter(username='foo'))
    list(User.objects.filter(username='foo'))
    list(User.objects.filter(username='foo'))
    list(User.objects.filter(username='foo'))
    return HttpResponse('unseen')


def bogus_view_with_no_queries(request):
    return HttpResponse('unseen')


urlpatterns = [
    path('', bogus_view),
    path('no_queries/', bogus_view_with_no_queries),
]


@pytest.mark.django_db
def test_middleware(settings, client, caplog):
    caplog.set_level(logging.DEBUG)
    settings.ROOT_URLCONF = __name__
    settings.DEBUG = True
    settings.SQL_DEBUG = SQL_DEBUG_LEVEL_WORST
    settings.SQL_DEBUG_WORST_SUSPICIOUS_CUTOFF = 0
    settings.SQL_DEBUG_WORST_QUERY_CUTOFF = 1

    client.get('/no_queries/?_iommi_sql_trace')
    assert 'GET /no_queries/?_iommi_sql_trace -> 200  (0.000s)' in caplog.text

    caplog.clear()

    response = client.get('/?_iommi_sql_trace')

    content = response.content.decode().replace('&quot;', '"')
    assert 'unseen' not in content

    assert '4 queries' in content
    # noinspection SqlResolve
    select_statement = 'SELECT "auth_user"."id", "auth_user"."password", "auth_user"."last_login", "auth_user"."is_superuser", "auth_user"."username", "auth_user"."first_name", "auth_user"."last_name", "auth_user"."email", "auth_user"."is_staff", "auth_user"."is_active", "auth_user"."date_joined" FROM "auth_user" WHERE "auth_user"."username"'
    assert select_statement in content
    assert '<span style="color: green; font-weight: bold">SELECT</span>' in content

    assert '------ 4 times: -------' in caplog.text
    assert select_statement in caplog.text
    assert 'File "iommi/iommi/sql_trace__tests.py", line ' in caplog.text
    assert re.findall(r'GET /\?_iommi_sql_trace -> 200  \(0\.\d\d\ds\) \(sql time: 0\.\d\d\ds\)', caplog.text)
    assert '... and 3 more unique statements' in caplog.text


@pytest.mark.parametrize(
    'text, fg, bold, expected',
    [
        ('foo', None, False, 'foo'),
        ('foo', 'red', False, '<span style="color: red">foo</span> '),
        ('foo', None, True, '<span style="font-weight: bold">foo</span> '),
        ('foo', 'red', True, '<span style="color: red; font-weight: bold">foo</span> '),
    ],
)
def test_colorize(text, fg, bold, expected):
    assert colorize(text, fg, bold) == expected


@pytest.mark.parametrize(
    'params, expected',
    [
        (None, (1, 2, 3)),
        ([1, 2, 3], (1, 2, 3)),
        ((1, 2, 3), (1, 2, 3)),
        (1, '1'),
        (1.5, '1.5'),
        (date(2020, 1, 3), "'2020-01-03'"),
        (datetime(2020, 1, 3, 13, 37), "'2020-01-03 13:37'"),
        ({'foo': 1.5}, {'foo': '1.5'}),
        (b'foo', 'foo'),
    ],
)
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
    frames = [
        Struct(
            f_lineno=1,
            f_locals={
                'bit': 'django_template_bit',
            },
            f_code=Struct(
                co_name='asd',
                co_filename='foo.py',
            ),
        ),
        Struct(
            f_lineno=1,
            f_locals={},
            f_code=Struct(
                co_name='_resolve_lookup',
                co_filename='foo.py',
            ),
        ),
        Struct(
            f_lineno=1,
            f_code=Struct(
                co_name='f',
                co_filename='foo/django/template/bar',
            ),
        ),
        Struct(
            f_lineno=1,
            f_code=Struct(
                co_name='f',
                co_filename='foo/django/template/bar',
            ),
        ),
        Struct(
            f_lineno=1,
            f_code=Struct(
                co_name='f',
                co_filename='/lib/python/foo.py',
            ),
        ),
        Struct(
            f_lineno=1,
            f_code=Struct(
                co_name='f',
                co_filename='foo.py',
            ),
        ),
        Struct(
            f_lineno=1,
            f_code=Struct(
                co_name='f',
                co_filename='foo2.py',
            ),
        ),
    ]

    for i, f in enumerate(frames):
        if i == 0:
            f.f_back = None
        else:
            f.f_back = frames[i - 1]

    frame = frames[-1]

    expected = """
  File "foo2.py", line 1, in f => 
  File "foo.py", line 1, in f => 
  File "foo/django/template/bar", line 1, in f => 
  File "foo.py", line 1, in _resolve_lookup => (looking up: django_template_bit)
  File "foo.py", line 1, in asd =>
  """.strip()  # noqa: W291
    actual = sql_debug_format_stack_trace(frame).strip()
    assert actual == expected


def test_sql_debug_trace_sql_cutoff(caplog):
    caplog.set_level(logging.DEBUG)
    set_sql_debug(SQL_DEBUG_LEVEL_WORST)

    sql_debug_trace_sql('!' * 10_001)
    assert caplog.records[0].msg.startswith('!' * 10_000)
    assert caplog.records[0].msg[10_000:] == '... [10001 bytes sql]'


def test_sql_debug_trace_sql_frame(caplog):
    caplog.set_level(logging.DEBUG)
    set_sql_debug(SQL_DEBUG_LEVEL_ALL_WITH_STACKS)

    with pytest.raises(KeyError):
        sql_debug_trace_sql('foo')

    frame = Struct(
        f_lineno=1,
        f_back=None,
        f_locals={},
        f_code=Struct(
            co_name='foo',
            co_filename='foo.py',
        ),
    )

    sql_debug_trace_sql('foo', frame=frame)
    assert caplog.records[0].msg == '  File "foo.py", line 1, in foo =>'


def test_sql_debug_log_to_request_adds_attribute():
    set_sql_debug(SQL_DEBUG_LEVEL_WORST)

    request = req('get')
    set_current_request(request)
    sql_debug_log_to_request(sql='q', foo='bar')
    assert request.iommi_sql_debug_log == [dict(sql='q', foo='bar')]


def test_sql_debug_total_time():
    set_sql_debug(SQL_DEBUG_LEVEL_WORST)

    set_current_request(None)
    assert sql_debug_total_time() == 0.0

    request = req('get')
    set_current_request(request)
    request.iommi_sql_debug_log = [dict(duration=3), dict(duration=7)]
    assert sql_debug_total_time() == 10


def test_format_sql():
    assert format_sql('SELECT x AND y FROM foo', short_limit=0) == (
        '<span><span style="color: green; font-weight: bold">SELECT</span> <span '
        'style="color: green">x</span> <span><br>&nbsp;</span>&nbsp;<span '
        'style="color: green; font-weight: bold">AND</span> <span style="color: '
        'green">y</span> <span><br>&nbsp;</span><span style="color: green; '
        'font-weight: bold">FROM</span> <span style="color: green">foo</span> </span>'
    )
