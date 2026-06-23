import logging
import re
from datetime import (
    date,
    datetime,
)
from pathlib import Path

import pytest
import time_machine
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.urls import path

from iommi.sql_trace import (
    SQL_DEBUG_LEVEL_WORST,
    colorize,
    format_clickable_filename,
    format_explain_output,
    format_sql,
    get_sql_debug,
    is_explainable,
    linkify,
    no_sql_debug,
    run_explain,
    safe_unicode_literal,
    set_sql_debug,
    sql_debug_format_stack_trace,
    sql_debug_log_to_request,
    sql_debug_total_time,
    sql_debug_trace_sql,
)
from iommi.struct import Struct
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

    with time_machine.travel('1948-02-19', tick=True):
        client.get('/no_queries/?_iommi_sql_trace')
        assert 'GET /no_queries/?_iommi_sql_trace -> 200' in caplog.text

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
        assert 'File "' in caplog.text
        assert 'iommi/sql_trace__tests.py", line ' in caplog.text
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


def test_sql_debug_format_stack_trace(monkeypatch):
    monkeypatch.setattr('iommi.sql_trace.colored', lambda text, **kwargs: text)
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


def test_linkify():
    base_path = Path(__file__).parent.parent.absolute()

    original = """
  File "foo/django/template/bar", line 1, in f =>
  File "foo.py", line 1, in _resolve_lookup => (looking up: django_template_bit)
  File "foo.py", line 13, in asd =>
""".strip()
    expected = f"""
  File "<a href="pycharm://open?file={base_path}/foo/django/template/bar&amp;line=1">foo/django/template/bar</a> ", line 1, in f =&gt;
  File "<a href="pycharm://open?file={base_path}/foo.py&amp;line=1">foo.py</a> ", line 1, in _resolve_lookup =&gt; (looking up: django_template_bit)
  File "<a href="pycharm://open?file={base_path}/foo.py&amp;line=13">foo.py</a> ", line 13, in asd =&gt;
""".strip()
    actual = linkify(original).strip()
    assert actual == expected


def test_format_clickable_line_nones():
    assert (
        format_clickable_filename(None, None, None) == '  File "<unknown>", line <unknown>, in <unknown> => <unknown>'
    )


@pytest.mark.django_db
def test_explain_links_appear_in_trace(settings, client):
    settings.ROOT_URLCONF = __name__
    settings.DEBUG = True
    settings.SQL_DEBUG = SQL_DEBUG_LEVEL_WORST

    response = client.get('/?_iommi_sql_trace=worst')
    content = response.content.decode()
    assert '[EXPLAIN]' in content
    assert '_iommi_sql_explain=' in content


@pytest.mark.django_db
def test_explain_output_renders(settings, client):
    settings.ROOT_URLCONF = __name__
    settings.DEBUG = True
    settings.SQL_DEBUG = SQL_DEBUG_LEVEL_WORST

    response = client.get('/?_iommi_sql_trace=worst&_iommi_sql_explain=0')
    content = response.content.decode()
    # EXPLAIN QUERY PLAN output should be rendered as a table
    assert '<table' in content
    assert '<th' in content


@pytest.mark.django_db
def test_explain_invalid_index(settings, client):
    settings.ROOT_URLCONF = __name__
    settings.DEBUG = True
    settings.SQL_DEBUG = SQL_DEBUG_LEVEL_WORST

    # Out of bounds index - should render normally without EXPLAIN output
    response = client.get('/?_iommi_sql_trace=worst&_iommi_sql_explain=999')
    content = response.content.decode()
    assert '4 queries' in content
    assert '[EXPLAIN]' in content

    # Non-integer index - should render normally
    response = client.get('/?_iommi_sql_trace=worst&_iommi_sql_explain=abc')
    content = response.content.decode()
    assert '4 queries' in content


def test_is_explainable():
    assert is_explainable('SELECT * FROM foo') is True
    assert is_explainable('INSERT INTO foo VALUES (1)') is True
    assert is_explainable('UPDATE foo SET x=1') is True
    assert is_explainable('DELETE FROM foo') is True
    assert is_explainable('BEGIN') is False
    assert is_explainable('COMMIT') is False
    assert is_explainable('ROLLBACK') is False
    assert is_explainable('SAVEPOINT x') is False


@pytest.mark.django_db
def test_run_explain_with_select():
    # Create the table first by accessing the model
    User.objects.exists()

    entry = {
        'sql': 'SELECT "auth_user"."id" FROM "auth_user" WHERE "auth_user"."username" = %s',
        'params': ('foo',),
        'using': 'default',
    }
    result = run_explain(entry)
    assert result is not None
    assert '<table' in result


def test_run_explain_non_explainable():
    entry = {'sql': 'BEGIN', 'params': None, 'using': 'default'}
    result = run_explain(entry)
    assert result is None


def test_format_explain_output():
    # The most expensive row scales the gradient bar to 100%, the cheaper one proportionally.
    html = format_explain_output(
        ['Plan'],
        [['Seq Scan  (cost=0.00..2.00 rows=1)'], ['Index  (cost=0.00..1.00 rows=1)']],
    )
    assert html == (
        '<table style="border-collapse: collapse; margin: 8px 0; font-size: 13px">'
        '<tr><th style="border: 1px solid #666; padding: 4px 8px; white-space: pre; text-align: left">Plan</th></tr>'
        '<tr><td style="border: 1px solid #666; padding: 4px 8px; white-space: pre;'
        ' background: linear-gradient(to right, rgba(79,79,255,0.3) 100.0%, transparent 100.0%)">'
        'Seq Scan  (cost=0.00..2.00 rows=1)</td></tr>'
        '<tr><td style="border: 1px solid #666; padding: 4px 8px; white-space: pre;'
        ' background: linear-gradient(to right, rgba(79,79,255,0.3) 50.0%, transparent 50.0%)">'
        'Index  (cost=0.00..1.00 rows=1)</td></tr>'
        '</table>'
    )


@pytest.mark.parametrize(
    'sql, color, keyword',
    [
        ('SELECT x FROM foo', 'green', 'SELECT'),
        ('INSERT INTO foo', 'magenta', 'INSERT'),
        ('UPDATE foo SET x', 'orange', 'UPDATE'),
        ('DELETE FROM foo', 'red', 'DELETE'),
        ('COMMIT', 'cyan', 'COMMIT'),
        ('BEGIN', 'cyan', 'BEGIN'),
        ('ROLLBACK', 'red', 'ROLLBACK'),
    ],
)
def test_format_sql_keyword_colors(sql, color, keyword):
    # short_limit high so the query is rendered "short" (no line wrapping).
    html = format_sql(sql, short_limit=1000)
    assert f'<span style="color: {color}; font-weight: bold">{keyword}</span>' in html


def test_sql_debug_format_stack_trace_skips_framework_frames(monkeypatch):
    monkeypatch.setattr('iommi.sql_trace.colored', lambda text, **kwargs: text)

    skip_filenames = [
        '/lib/python/x.py',
        'a/django/core/x.py',
        'a/pydev/pydevd/x.py',
        'a/gunicorn/x.py',
        'iommi/iommi/declarative/dispatch.py',
        'iommi/iommi/member.py',
    ]

    frames = [
        Struct(f_lineno=1, f_locals={}, f_code=Struct(co_name='user_code', co_filename='myapp/views.py')),
    ]
    for i, filename in enumerate(skip_filenames):
        frames.append(Struct(f_lineno=1, f_locals={}, f_code=Struct(co_name=f'skip{i}', co_filename=filename)))

    for i, f in enumerate(frames):
        f.f_back = None if i == 0 else frames[i - 1]

    result = sql_debug_format_stack_trace(frames[-1])

    assert 'user_code' in result
    for i in range(len(skip_filenames)):
        assert f'skip{i}' not in result


def test_format_explain_output_scales_to_actual_max_cost():
    # The most expensive row defines 100%; costs below 1.0 must still scale (col_max tracks the
    # real max, starting from 0, and the gradient shows whenever col_max > 0).
    html = format_explain_output(
        ['Plan'],
        [['A (cost=0.00..0.50 rows=1)'], ['B (cost=0.00..0.25 rows=1)']],
    )
    assert 'rgba(79,79,255,0.3) 100.0%' in html
    assert 'rgba(79,79,255,0.3) 50.0%' in html
