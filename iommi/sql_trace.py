import itertools
import linecache
import logging
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

from django.conf import settings
from django.db import connections
from django.db.backends import utils as django_db_utils
from django.db.utils import DEFAULT_DB_ALIAS
from django.http import HttpResponse

from iommi._web_compat import format_html
from iommi.attrs import render_style
from iommi.thread_locals import (
    get_current_request,
    set_current_request,
)


def no_coloring(text, color=None, on_color=None, attrs=None):
    return text


try:
    from termcolor import colored
except ImportError:
    colored = no_coloring


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


def linkify(s):
    from iommi.debug import src_debug_url_builder

    r = []
    for line in s.split('\n'):
        match = re.search(r'( *)File "(.*)", line (\d+), in (.*)', line)
        if match:
            starting_space = match.group(1)
            filename = match.group(2)
            lineno = int(match.group(3))
            function_name = match.group(4)
            r.append(
                format_html(
                    '{}File "<a href="{}">{}</a> ", line {}, in {}\n',
                    starting_space,
                    src_debug_url_builder(filename, lineno),
                    filename,
                    lineno,
                    function_name,
                )
            )

    return format_html('{}' * len(r), *r)


class Middleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.prof = None

    def __call__(self, request):
        set_current_request(request)
        request.iommi_start_time = datetime.now()
        sql_trace = request.GET.get('_iommi_sql_trace')

        if sql_trace is None:
            sql_trace = get_sql_debug()

        if sql_trace == '':
            sql_trace = SQL_DEBUG_LEVEL_WORST

        assert sql_trace in SQL_DEBUG_LEVELS

        old_state = get_sql_debug()
        set_sql_debug(sql_trace)
        try:
            request.iommi_sql_debug_log = []

            response = self.get_response(request)

            sql_debug_last_call(response)

            if '_iommi_sql_trace' not in request.GET:
                return response

            if not settings.DEBUG and not request.user.is_staff:
                return response

            if sql_trace is not None:
                iommi_sql_debug_log = getattr(request, 'iommi_sql_debug_log', None)
                if iommi_sql_debug_log is not None:
                    total_duration = float(sum(x['duration'] for x in iommi_sql_debug_log))
                    result = [
                        # language=HTML
                        '''
                            <style>
                                a, span {
                                    box-sizing: border-box;
                                }
                                @media (prefers-color-scheme: dark) {
                                    html {
                                        background-color: black;
                                        color: #bbb;
                                    }
                                    b {
                                        color: white;
                                    }
                                }
                            </style>
                        ''',
                        f'{len(iommi_sql_debug_log)} queries, {total_duration:.3} seconds total<br><br>',
                    ]

                    if total_duration:
                        color = '#4f4fff'
                        for i, x in enumerate(iommi_sql_debug_log):
                            proportion = x["duration"] / total_duration * 100
                            result.append(
                                f'<a href="#query_{i}" style="display: inline-block; height: 30px; width: {proportion}%; background-color: {color}; border-left: 1px solid black" title="{x["duration"]:.3}s"></a>'
                            )

                        result.append('<br><br>By group:<br>')

                        for k, group in itertools.groupby(iommi_sql_debug_log, key=lambda x: x['sql']):
                            group = list(group)
                            duration = sum(x["duration"] for x in group)
                            proportion = duration / total_duration * 100
                            k = k.replace('>', '&gt;')
                            result.append(
                                format_html(
                                    '<span style="display: inline-block; height: 30px; width: {}%; background-color: {}; border-left: 1px solid black" title="{} queries. Ran {}s, like {}"></span>',
                                    proportion,
                                    color,
                                    len(group),
                                    f'{duration:.3}',
                                    k,
                                )
                            )

                    result.append('<p></p><pre>')

                    for i, x in enumerate(iommi_sql_debug_log):
                        sql = x['sql']
                        if x['params']:
                            sql %= safe_unicode_literal(x['params'])

                        result.append(f'<a name="query_{i}">')
                        result.append(format_sql(sql, duration=x['duration']))
                        if sql_trace == SQL_DEBUG_LEVEL_ALL_WITH_STACKS:
                            result.append('\n\n')
                            result.append(linkify(x['stack']))
                        result.append('\n\n')
                    result.append('</pre>')
                    return HttpResponse(''.join(result))

            return response
        finally:
            set_sql_debug(old_state)


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
    base_colors = {
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
                if _first and token in base_colors:
                    _first = False
                    fg = base_colors[token]
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
    sentinel = object()
    result = getattr(state, 'sql_debug', sentinel)
    if result is not sentinel:
        return result
    return getattr(settings, 'SQL_DEBUG', SQL_DEBUG_LEVEL_WORST)


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
        sql_debug(kwargs['stack'], extra={})

    kwargs['sql'] = True
    sql_debug(sql, extra=kwargs)

    if get_sql_debug() == SQL_DEBUG_LEVEL_ALL_WITH_STACKS:
        sql_debug('\n', extra=kwargs)
    return sql


def sql_debug_total_time():
    try:
        log = get_current_request().iommi_sql_debug_log
    except AttributeError:
        return 0

    return sum(x['duration'] for x in log)


def get_line_cached_on_request(file_name, line):
    request = get_current_request()

    if not request:
        return linecache.getline(file_name, line)

    if not hasattr(request, '_iommi_line_cache'):
        request._iommi_line_cache = {}

    if file_name not in request._iommi_line_cache:
        request._iommi_line_cache[file_name] = linecache.getlines(file_name)

    if not request._iommi_line_cache[file_name]:
        return ''
    return request._iommi_line_cache[file_name][line - 1]


def format_clickable_filename(file_name, line, fn, extra=None):
    if not extra:
        if line is not None:
            extra = get_line_cached_on_request(file_name, line)

    if extra is None:
        extra = '<unknown>'
    if file_name is None:
        file_name = '<unknown>'
    if line is None:
        line = '<unknown>'
    if fn is None:
        fn = '<unknown>'

    return f'  File "{file_name}", line {line}, in {fn} => {extra.strip()}'.rstrip()


def sql_debug_format_stack_trace(frame):
    if frame is None:
        return None

    lines = []
    skip_template_code = False

    def skip_line(frame):
        filename = frame.f_code.co_filename
        return (
            '/lib/python' in filename
            or 'django/core' in filename
            or 'pydev/pydevd' in filename
            or 'gunicorn' in filename
            or 'iommi/iommi/declarative/dispatch.py' in filename
            or 'iommi/iommi/member.py' in filename
        )

    while frame:
        if skip_line(frame):
            frame = frame.f_back
            continue

        file_name, line, fn = frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name
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

        lines.append(format_clickable_filename(file_name, line, fn, extra))

        frame = frame.f_back

    stack = "\n".join(lines).rstrip()
    return stack


def sql_debug_last_call(response):
    request = get_current_request()
    if get_sql_debug() == SQL_DEBUG_LEVEL_WORST and hasattr(
        request, 'iommi_sql_debug_log'
    ):  # hasattr check because process_request might not be called in case of an early redirect
        stacks = defaultdict(list)
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
                if hasattr(response, 'iommi_part'):
                    from iommi.debug import filename_and_line_num_from_part

                    filename, lineno = filename_and_line_num_from_part(response.iommi_part)
                    sql_debug('From source:')
                    sql_debug(
                        format_clickable_filename(filename, lineno, str(response.iommi_part._name)), sql_trace=True
                    )
                    sql_debug('With Stack:')
                sql_debug(logs[-1]['stack'], sql_trace=True)
                for x in logs[:query_cutoff]:
                    sql_debug_trace_sql(**x)
                if len(logs) > query_cutoff:
                    sql_debug(f'... and {len(logs) - query_cutoff:d} more unique statements\n')
        queries_per_using = defaultdict(int)
        for x in request.iommi_sql_debug_log:
            queries_per_using[x['using']] += 1

        sql_debug(f'Total number of SQL statements: {sum(queries_per_using.values())}\n')

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
        if get_sql_debug() is not None:
            frame = sys._getframe().f_back.f_back
            while "django/db" in frame.f_code.co_filename:
                frame = frame.f_back
        else:
            frame = None

        start = monotonic()
        try:
            return f(**kwargs)
        finally:
            stop = monotonic()
            duration = stop - start
            sql_debug_log_to_request(
                stack=sql_debug_format_stack_trace(frame),
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
