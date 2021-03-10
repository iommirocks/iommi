import itertools
import linecache
import logging
import os
import re
import sys
import threading
from collections import defaultdict
from contextlib import contextmanager
from datetime import (
    date,
    datetime,
)
from logging import addLevelName
from time import monotonic

from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.http import HttpResponse
from django.utils.html import format_html

from iommi.attrs import render_style
from iommi.thread_locals import (
    get_current_request,
    set_current_request,
)

try:
    from termcolor import colored
except ImportError:

    def colored(text, color=None, on_color=None, attrs=None):
        return text


from django.conf import settings
from django.db.backends import utils as django_db_utils


log = logging.getLogger('db')
IOMMI_SQL_LOG = logging.INFO + 1
addLevelName(IOMMI_SQL_LOG, 'IOMMI_SQL_LOG')

SQL_DEBUG_LEVEL_ALL = 'all'
SQL_DEBUG_LEVEL_ALL_WITH_STACKS = 'stacks'
SQL_DEBUG_LEVEL_WORST = 'worst'
SQL_DEBUG_LEVEL_OFF = None

SQL_DEBUG_LEVELS = {
    SQL_DEBUG_LEVEL_ALL,
    SQL_DEBUG_LEVEL_ALL_WITH_STACKS,
    SQL_DEBUG_LEVEL_WORST,
    SQL_DEBUG_LEVEL_OFF,
}

assert getattr(settings, 'SQL_DEBUG', None) in SQL_DEBUG_LEVELS, f'SQL_DEBUG must be one of: {SQL_DEBUG_LEVELS}'


class Middleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.prof = None

    def __call__(self, request):
        set_current_request(request)
        request.iommi_start_time = datetime.now()
        sql_trace = request.GET.get('_iommi_sql_trace')
        request.iommi_sql_debug_log = []

        response = self.get_response(request)

        if not settings.DEBUG and not request.user.is_staff:
            return response

        sql_debug_last_call(response)

        if sql_trace is not None:
            iommi_sql_debug_log = getattr(request, 'iommi_sql_debug_log', None)
            if iommi_sql_debug_log is not None:
                total_duration = float(sum(x['duration'] for x in iommi_sql_debug_log))
                result = [
                    '<style> a, span { box-sizing: border-box; } </style>',
                    f'{len(iommi_sql_debug_log)} queries, {total_duration:.3} seconds total<br><br>',
                ]

                color = '#4f4fff'
                for i, x in enumerate(iommi_sql_debug_log):
                    proportion = x["duration"] / total_duration * 100
                    result.append(
                        f'<a href="#query_{i}" style="display: inline-block; height: 30px; width: {proportion}%; background-color: {color}; border-left: 1px solid black" title="{x["duration"]:.3}s"></a>'
                    )

                result.append('<br>By group:<br>')

                for k, group in itertools.groupby(iommi_sql_debug_log, key=lambda x: x['sql']):
                    group = list(group)
                    duration = sum(x["duration"] for x in group)
                    proportion = duration / total_duration * 100
                    k = k.replace('>', '&gt;')
                    result.append(
                        format_html('<span style="display: inline-block; height: 30px; width: {}%; background-color: {}; border-left: 1px solid black" title="{} queries. Ran {}s, like {}"></span>', proportion, color, len(group), f'{duration:.3}', k)
                    )

                result.append('<p></p><pre>')

                for i, x in enumerate(iommi_sql_debug_log):
                    sql = x['sql']
                    if x['params']:
                        sql %= safe_unicode_literal(x['params'])

                    result.append(f'<a name="query_{i}">')
                    result.append(format_sql(sql, duration=x['duration']))
                    result.append('\n\n')
                result.append('</pre>')
                return HttpResponse(''.join(result))

        return response


def colorize(text, fg, bold=False):
    styles = {}
    if fg:
        styles['color'] = fg
    if bold:
        styles['font-weight'] = 'bold'
    if styles:
        return format_html('<span style="{}">{}</span> ', render_style(styles), text)
    else:
        return text


def format_sql(text, width=60, duration=None, short_limit=120):
    BASE_COLORS = {
        'SELECT': 'green',
        'INSERT': 'magenta',
        'UPDATE': 'orange',
        'DELETE': 'red',
        'COMMIT': 'cyan',
        'BEGIN': 'cyan',
        'ROLLBACK': 'red',
    }
    # pretend all upper case tokens are keywords
    sql_keyword_re = re.compile(r'^[A-Z]+$')
    sql_token_sep_re = re.compile(r'\s+')

    def tokenize(text):
        tokens = re.split(sql_token_sep_re, text.strip().replace('`', ''))
        short = len(text) < short_limit

        _first = True
        column = 0
        fg = None
        for token in tokens:
            bold = False
            if sql_keyword_re.match(token):
                bold = True
                if _first and token in BASE_COLORS:
                    _first = False
                    fg = BASE_COLORS[token]
                if not short:
                    if token in ('AND', 'OR', 'LEFT', 'INNER', 'FROM', 'WHERE', 'ORDER', 'LIMIT'):
                        yield format_html('<span><br>&nbsp;</span>')
                        column = 2
                        if token in (
                            'AND',
                            'OR',
                        ):
                            yield format_html('&nbsp;')
                            column += 2
            yield colorize(token, fg=fg, bold=bold)

            column += len(token) + 1
            if column > width and token[-1] == ',':
                yield format_html('<span><br>{}</span>', format_html('&nbsp;' * 8))
                column = 8
        if duration:
            yield format_html(f"<span>-- [{duration:.3f}s]</span>")

    tokens = list(tokenize(text))
    return format_html('<span>' + ('{}' * len(tokens)) + '</span>', *tokens)


def safe_unicode_literal(obj):
    if obj is None:
        return 'NULL'

    if isinstance(obj, (list, tuple)):
        return tuple([safe_unicode_literal(x) for x in obj])
    elif isinstance(obj, (float, int)):
        return repr(obj)
    elif isinstance(obj, (date, datetime)):
        return repr(obj.isoformat())
    elif isinstance(obj, dict):
        return dict((k, safe_unicode_literal(v)) for k, v in obj.items())
    elif isinstance(obj, bytes):
        return repr(obj.decode(errors="replace"))
    else:
        return repr(obj)


state = threading.local()


def set_sql_debug(new_state, validate=True):
    if new_state == 'None':
        new_state = None
    if validate:
        assert new_state is None or new_state in SQL_DEBUG_LEVELS
    setattr(state, 'sql_debug', new_state)


def get_sql_debug():
    result = getattr(state, 'sql_debug', None)
    if result is not None:
        return result
    return getattr(settings, 'SQL_DEBUG', None)


@contextmanager
def no_sql_debug():
    """
    Context manager to temporarily suspend sql logging.

    This is useful inside the sql debug implementation to avoid infinite recursion.
    """
    old_state = get_sql_debug()
    set_sql_debug(SQL_DEBUG_LEVEL_OFF)
    yield
    set_sql_debug(old_state)


def sql_debug(msg, **extra):
    if get_sql_debug():
        if 'sql' not in extra:
            # If we don't do this we'll end up with infinite recursion back here
            extra['sql'] = ''
        log.log(level=IOMMI_SQL_LOG, msg=msg, extra=extra)


def sql_debug_log_to_request(**data):
    request = get_current_request()
    if request is not None:
        try:
            request.iommi_sql_debug_log.append(data)
        except AttributeError:
            request.iommi_sql_debug_log = [data]

    level = get_sql_debug()
    if level is False or level == SQL_DEBUG_LEVEL_WORST:
        return
    sql_debug_trace_sql(**data)


def sql_debug_trace_sql(sql, params=None, **kwargs):
    if params:
        sql %= safe_unicode_literal(params)
    if len(sql) > 10000:
        sql = '%s... [%d bytes sql]' % (re.sub(r'[\x00-\x08\x0b-\x1f\x80-\xff].*', '.', sql[:10000]), len(sql))
    else:
        sql = re.sub(r'[\x00-\x08\x0b-\x1f\x80-\xff]', '.', sql)

    if get_sql_debug() == SQL_DEBUG_LEVEL_ALL_WITH_STACKS:
        sql_debug(sql_debug_format_stack_trace(kwargs['frame']), extra={})

    kwargs['sql'] = True
    sql_debug(sql, extra=kwargs)
    return sql


def sql_debug_total_time():
    try:
        log = get_current_request().iommi_sql_debug_log
    except AttributeError:
        return 0

    return sum(x['duration'] for x in log)


def sql_debug_format_stack_trace(frame):
    base_path = os.path.abspath(os.path.join(settings.BASE_DIR, '..')) + "/"
    msg = []
    skip_template_code = False

    def skip_line(frame):
        filename = frame.f_code.co_filename
        return (
            '/lib/python' in filename
            or 'django/core' in filename
            or 'pydev/pydevd' in filename
            or 'gunicorn' in filename
        )

    while frame:
        if skip_line(frame):
            frame = frame.f_back
            continue

        file_name, line, fn = frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name

        file_name = file_name.replace(base_path, '')
        extra = ''
        if fn == '_resolve_lookup':
            f = frame
            while f.f_back and 'bit' not in f.f_locals:
                f = f.f_back
            if 'bit' in f.f_locals:
                extra = colored(f'(looking up: {f.f_locals["bit"]}) ', color='red')
        elif "django/template" in file_name:
            if skip_template_code:
                frame = frame.f_back
                continue
            skip_template_code = True
        elif skip_template_code:
            skip_template_code = False

        if not extra:
            extra = linecache.getline(file_name, line)

        msg.append(f'  File "{file_name}", line {line}, in {fn} => {extra.strip()}')

        frame = frame.f_back

    stack = "\n".join(msg[-20:]).rstrip()
    return stack


def fill_stacks(iommi_sql_debug_log):
    for x in iommi_sql_debug_log:
        x['stack'] = sql_debug_format_stack_trace(x['frame'])


def sql_debug_last_call(response):
    request = get_current_request()
    if get_sql_debug() == SQL_DEBUG_LEVEL_WORST and hasattr(
        request, 'iommi_sql_debug_log'
    ):  # hasattr check because process_request might not be called in case of an early redirect
        stacks = defaultdict(list)
        fill_stacks(request.iommi_sql_debug_log)
        for x in request.iommi_sql_debug_log:
            stacks[x['sql']].append(x)

        highscore = sorted([(len(logs), stack_trace, logs) for stack_trace, logs in stacks.items()])
        # Print the worst offenders
        number_of_offenders = getattr(settings, 'SQL_DEBUG_WORST_NUMBER_OF_OFFENDERS', 3)
        query_cutoff = getattr(settings, 'SQL_DEBUG_WORST_QUERY_CUTOFF', 4)
        num_suspicious = getattr(settings, 'SQL_DEBUG_WORST_SUSPICIOUS_CUTOFF', 3)
        for count, _, logs in highscore[-number_of_offenders:]:
            if count > num_suspicious:  # 3 times is ok-ish, more is suspicious
                sql_debug(f'------ {count} times: -------', bold=True)
                sql_debug(logs[0]['stack'], sql_trace=True)
                for x in logs[:query_cutoff]:
                    sql_debug_trace_sql(**x)
                if len(logs) > query_cutoff:
                    sql_debug(f'... and {len(logs) - query_cutoff:d} more unique statements\n')
        queries_per_using = defaultdict(int)
        for x in request.iommi_sql_debug_log:
            queries_per_using[x['using']] += 1

        sql_debug(
            f'Total number of SQL statements: {sum(queries_per_using.values())}, {queries_per_using.get("read-only")} read-only, {queries_per_using.get("summary")} summary\n'
        )

    if settings.DEBUG:
        total_sql_time = f" (sql time: {sql_debug_total_time():.3f}s)"
        duration = f' ({(datetime.now() - request.iommi_start_time).total_seconds():.3f}s)'
        sql_debug(
            msg=f'{request.META["REQUEST_METHOD"]} {request.get_full_path()} -> {response.status_code} {duration}{total_sql_time}'
        )
        sql_debug(f'{request.get_full_path()} -> {response.status_code}{duration}', fg='magenta')

    set_sql_debug(None)


class CursorDebugWrapper(django_db_utils.CursorWrapper):
    def _execute_and_log(self, *, f, **kwargs):
        frame = sys._getframe().f_back.f_back
        while "django/db" in frame.f_code.co_filename:
            frame = frame.f_back

        start = monotonic()
        try:
            return f(**kwargs)
        finally:
            stop = monotonic()
            duration = stop - start
            sql_debug_log_to_request(
                frame=frame,
                duration=duration,
                rowcount=self.cursor.rowcount,
                using=self.db.alias,
                **kwargs,
            )

    def execute(self, sql, params=None):
        return self._execute_and_log(f=super().execute, sql=sql, params=params)

    def executemany(self, sql, param_list):
        return self._execute_and_log(f=super().executemany, sql=sql, param_list=param_list)

    def __iter__(self):
        return iter(self.cursor)

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)


def make_debug_cursor(self, cursor):
    return CursorDebugWrapper(cursor, self)


connections[DEFAULT_DB_ALIAS].__class__.make_debug_cursor = make_debug_cursor

