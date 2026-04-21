# Based on https://www.djangosnippets.org/snippets/186/

import cProfile
import marshal
import os
import pstats
import subprocess
import sys
import threading
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.template import (
    Context,
    Template,
)

try:
    import yappi
except ImportError:
    yappi = None

from asgiref.sync import (
    async_to_sync,
    iscoroutinefunction,
    markcoroutinefunction,
    sync_to_async,
)
from django.conf import settings
from django.http import HttpResponse
from django.http.response import (
    HttpResponseBase,
    StreamingHttpResponse,
)
from django.utils.html import escape

from iommi.debug import src_debug_url_builder

MEDIA_PREFIXES = ['/static/']

_dot_search_paths = [
    '/usr/bin/dot',
    '/usr/local/bin/dot',
]


def get_dot_path():
    for p in _dot_search_paths:
        if os.path.exists(p):
            return p
    return None


def should_profile(request):
    disabled = getattr(request, 'profiler_disabled', True)
    is_staff = hasattr(request, 'user') and request.user.is_staff

    return ('_iommi_prof' in request.GET or '_iommi_prof' in request.POST) and (
        (not disabled and is_staff) or settings.DEBUG
    )


def strip_extra_path(s, token):
    if token not in s:
        return s
    pre, _, post = s.rpartition(' ')
    post = post[post.rindex(token) + len(token) :]
    return f'{pre} {post}'


class HTMLStats(pstats.Stats):
    _get_params = None

    def _build_url(self, **overrides):
        params = self._get_params.copy() if self._get_params else {}
        params.update(overrides)
        from django.http import QueryDict
        qd = QueryDict(mutable=True)
        qd.update(params)
        return '?' + qd.urlencode()

    def print_title(self):
        ncalls_url = self._build_url(_iommi_prof='ncalls')
        tottime_url = self._build_url(_iommi_prof='tottime')
        cumtime_url = self._build_url(_iommi_prof='cumtime')
        print(
            # language=HTML
            f'''
                <thead>
                    <tr>
                        <th class="numeric"><a href="{ncalls_url}">ncalls</a></th>
                        <th class="numeric"><a href="{tottime_url}">tottime</a></th>
                        <th class="numeric">percall</th>
                        <th class="numeric"><a href="{cumtime_url}">cumtime</a></th>
                        <th class="numeric">percall</th>
                        <th>function</th>
                        <th></th>
                        <th>filename</th>
                        <th>lineno</th>
                    </tr>
                </thead>
            ''',
            file=self.stream,
        )

    def print_stats(self, *amount):
        for filename in self.files:
            print(filename, file=self.stream)
        if self.files:
            print(file=self.stream)
        indent = ' ' * 8
        for func in self.top_level:
            print(indent, func[2], file=self.stream)

        print(indent, self.total_calls, "function calls", end=' ', file=self.stream)
        if self.total_calls != self.prim_calls:
            print("(%d primitive calls)" % self.prim_calls, end=' ', file=self.stream)
        print("in %.3f seconds" % self.total_tt, file=self.stream)
        print(file=self.stream)

        # this call prints...
        width, list = self.get_print_list(amount)

        print('<table>', file=self.stream)
        if list:
            self.print_title()
            limit = 280
            for func in list[:limit]:
                self.print_line(func)
            print(file=self.stream)
            print(file=self.stream)

        print('</table>', file=self.stream)
        return self

    def print_line(self, func):
        path, line_number, function_name = func

        base_dir = str(settings.BASE_DIR)
        should_bold = base_dir in path and '/site-packages/' not in path
        nice_path = path.replace(base_dir, '')
        nice_path = strip_extra_path(nice_path, '/site-packages')
        nice_path = strip_extra_path(nice_path, '/Python.framework/Versions')

        if should_bold:
            print('<tr class="own">', file=self.stream)
        else:
            print('<tr>', file=self.stream)

        def f8(x):
            return "%8.3f" % x

        cc, nc, tt, ct, callers = self.stats[func]
        c = str(nc)
        if nc != cc:
            c = c + '/' + str(cc)
        print(f'<td class="numeric">{c}</td>', file=self.stream)
        print(f'<td class="numeric">{f8(tt)}</td>', file=self.stream)
        if nc == 0:
            print('<td></td>', file=self.stream)
        else:
            print(f'<td>{f8(tt/nc)}</td>', file=self.stream)
        print(f'<td class="numeric">{f8(ct)}</td>', file=self.stream)
        if cc == 0:
            print('<td></td>', file=self.stream)
        else:
            print(f'<td class="numeric">{f8(ct/cc)}</td>', file=self.stream)

        if line_number and path:
            print(
                f'<td><a href="{src_debug_url_builder(path, line_number)}">{escape(function_name)}</a></td>',
                file=self.stream,
            )
        else:
            print(f'<td>{escape(function_name)}</td>', file=self.stream)

        from iommi import traversable
        if function_name in traversable.worst_offenders_candidates:
            print(f'<td><a href="?_iommi_func_worst_offender={escape(function_name)}">Worst offenders</a></td>', file=self.stream)
        else:
            print('<td></td>', file=self.stream)

        print(f'<td>{nice_path}</td>', file=self.stream)
        print(f'<td class="numeric">{line_number}</td>', file=self.stream)
        print('</tr>', file=self.stream)


def _yappi_generate_folded_data(func_stats, threshold):
    """Generate folded stack data directly from yappi's native tree.

    Walks yappi's parent-child relationships directly, avoiding
    any key format mismatches from pstats conversion.
    """
    stats_by_idx = {}
    for stat in func_stats:
        stats_by_idx[stat.index] = stat

    if not stats_by_idx:
        return ''

    # Use the function with the highest ttot as root.
    # Django's middleware cycle (inner → middleware → inner → ...)
    # means no function is truly "unparented", so we pick the top one.
    root = max(func_stats, key=lambda s: s.ttot)
    total_time = root.ttot
    if total_time <= 0:
        return ''

    lines = []
    visited = set()

    def format_frame(stat):
        return f'{stat.name} ({stat.module}:{stat.lineno})'

    def walk(stat, trace):
        for child in sorted(stat.children, key=lambda c: -c.ttot):
            edge = (stat.index, child.index)
            if edge in visited:
                continue

            if child.ttot / total_time < threshold:
                continue

            visited.add(edge)

            child_stat = stats_by_idx.get(child.index)
            child_trace = trace + (format_frame(child),)
            count = int(child.tsub * 1_000_000)
            if count > 0:
                lines.append(f'{";".join(child_trace)} {count}')

            if child_stat is not None:
                walk(child_stat, child_trace)

    root_trace = (format_frame(root),)
    count = int(root.tsub * 1_000_000)
    if count > 0:
        lines.append(f'{";".join(root_trace)} {count}')
    walk(root, root_trace)

    return '\n'.join(lines)


class Middleware:
    async_capable = True
    sync_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def _setup_request(self, request):
        # Disable profiling early on /media requests since touching request.user will add a
        # "Vary: Cookie" header to the response.
        request.profiler_disabled = False
        for prefix in MEDIA_PREFIXES:
            if request.path.startswith(prefix):
                request.profiler_disabled = True
                break

    def _process_response(self, request, response):
        if not isinstance(response, HttpResponseBase):
            assert False, f'Got a response of type {type(response)}, expected an HttpResponse object. Middlewares are in the wrong order.'

        if getattr(request, '_iommi_func_worst_offender', None):
            s = StringIO()
            for stack, count in sorted(request._iommi_func_worst_offender.items(), key=lambda x: -x[1]):
                if count <= 1:
                    break

                print(f'----- {count} -----', file=s)
                print(stack, file=s)
                print(file=s)

            return HttpResponse(s.getvalue(), content_type='text/plain')

        if request._iommi_prof:
            if isinstance(response, StreamingHttpResponse):
                # consume the entire streaming response, redirecting to stdout
                for line in response.streaming_content:
                    print(line.decode(), file=sys.__stdout__)

            response = HttpResponse()

            s = StringIO()
            ps = self._build_stats(request, s)

            prof_command = request.GET.get('_iommi_prof')

            if prof_command == 'graph':
                with NamedTemporaryFile() as stats_dump:
                    ps.stream = stats_dump
                    ps.dump_stats(stats_dump.name)

                    gprof2dot_path = Path(sys.executable).parent / 'gprof2dot'
                    if not gprof2dot_path.exists():
                        raise Exception('gprof2dot not found. Please install it to use the graph feature.')

                    with subprocess.Popen(
                        (sys.executable, gprof2dot_path, '-f', 'pstats', stats_dump.name), stdout=subprocess.PIPE
                    ) as gprof2dot:
                        response['Content-Type'] = 'image/svg+xml'

                        dot_path = get_dot_path()
                        if dot_path:
                            response.content = subprocess.check_output((dot_path, '-Tsvg'), stdin=gprof2dot.stdout)
                        else:
                            response['Content-Type'] = 'text/plain'
                            response['Content-Disposition'] = "attachment; filename=gprof2dot-graph.txt"
                            response.content = subprocess.check_output('tee', stdin=gprof2dot.stdout)

                        gprof2dot.wait()

            elif prof_command == 'flame':
                from django.templatetags.static import static

                if not hasattr(request, '_iommi_yappi_func_stats'):
                    return HttpResponse('You must `pip install yappi` to use the flamegraph feature')

                threshold = float(request.GET.get('_iommi_prof_threshold', 0.00001)) / 100
                folded_data = _yappi_generate_folded_data(request._iommi_yappi_func_stats, threshold)

                formatter_url = 'pycharm://open?file={filename}&line={lineno}'

                base_dir_css = str(settings.BASE_DIR).replace('\\', '\\\\').replace('"', '\\"')

                # language=html
                response.content = f'''\
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>iommi profiler</title>
        <style>
            html {{ color-scheme: light dark; }}
            body {{ background: light-dark(white, #1e1e1e); color: light-dark(black, #ccc); }}
            .flame-graph span[title] {{
                background-color: light-dark(#d0d0d0, #404040);
                border-radius: 3px;
                margin: 1px;
            }}
            .flame-graph span[title*="/site-packages/"] {{
                background-color: light-dark(#f5d58d, #5a4420);
            }}
            .flame-graph span[title*="{base_dir_css}"]:not([title*="/site-packages/"]) {{
                background-color: light-dark(#a8d5a8, #305830);
            }}
            .legend {{ display: flex; gap: 16px; padding: 8px 12px; font-family: monospace; font-size: 12px; }}
            .legend-swatch {{ display: inline-block; width: 12px; height: 12px; border-radius: 2px; margin-right: 4px; vertical-align: middle; }}
            .legend-project {{ background-color: light-dark(#a8d5a8, #305830); }}
            .legend-thirdparty {{ background-color: light-dark(#f5d58d, #5a4420); }}
            .legend-stdlib {{ background-color: light-dark(#d0d0d0, #404040); }}
        </style>
    </head>
    <body>
        <div class="legend">
            <span><span class="legend-swatch legend-project"></span>project</span>
            <span><span class="legend-swatch legend-thirdparty"></span>third-party</span>
            <span><span class="legend-swatch legend-stdlib"></span>stdlib</span>
        </div>
        <div id="elm"></div>
        <script src="{static('js/flame_graph.js')}"></script>
        <script>
            Elm.Main.init({{
                node: document.getElementById('elm'),
                flags: {{
                    data: {folded_data!r},
                    urlFormat: {formatter_url!r}
                }}
            }});
        </script>
    </body>
</html>'''
                response['Content-Type'] = 'text/html'

            else:
                ps = ps.sort_stats(prof_command or 'cumulative')
                ps.print_stats()

                result = s.getvalue()

                preserved_params = request.GET.copy()
                preserved_params['_iommi_prof'] = 'flame'
                flame_url = '?' + preserved_params.urlencode()
                preserved_params['_iommi_prof'] = 'graph'
                graph_url = '?' + preserved_params.urlencode()

                # language=html
                start_html = Template('''
                    <style>
                        html {
                            font-family: monospace;
                            white-space: pre-line;
                        }

                        div, table {
                            white-space: normal;
                        }

                        td, th {
                            white-space: nowrap;
                            padding-right: 0.5rem;
                            color: #666;
                        }

                        th {
                            text-align: left;
                        }

                        .numeric {
                            text-align: right;
                        }

                        .own td {
                            font-weight: bold;
                            color: black;
                        }

                        @media (prefers-color-scheme: dark) {
                            html {
                                background-color: black;
                                color: #bbb;
                            }
                            td, th {
                                color: #888;
                            }

                            .own td {
                                color: white;
                            }

                            a {
                                color: #1d5aff;
                            }
                            a:visited {
                                color: #681dff;
                            }
                        }
                    </style>

                    <div>
                        <a href="{{ flame_url }}">flamegraph</a>
                        <a href="{{ graph_url }}">graph</a>
                    </div>

                    <p></p>
                ''').render(
                    Context(
                        dict(
                            flame_url=flame_url,
                            graph_url=graph_url,
                        )
                    )
                )

                response.content = start_html.strip() + result

                response['Content-Type'] = 'text/html'

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        request._iommi_view_is_async = iscoroutinefunction(view_func)

    @staticmethod
    def _start_profiling(request):
        if yappi is not None:
            yappi.set_clock_type("wall")
            yappi.clear_stats()
            yappi.start(builtins=True)
            request._iommi_prof = True
        else:
            prof = cProfile.Profile()
            prof.enable()
            request._iommi_prof = [prof]

    @staticmethod
    def _yappi_stats_to_pstats_dict(func_stats):
        """Convert yappi func stats to a pstats-compatible dict.

        yappi's convert2pstats is broken on Python 3.13, so we
        build the dict directly.
        """
        pdict = {}
        for stat in func_stats:
            key = (stat.module, stat.lineno, stat.name)
            # tsub = time in function itself, ttot = cumulative time
            pdict[key] = (stat.nactualcall, stat.ncall, stat.tsub, stat.ttot, {})

        # Populate callers dicts from yappi children (which are callees)
        for stat in func_stats:
            caller_key = (stat.module, stat.lineno, stat.name)
            for child in stat.children:
                child_key = (child.module, child.lineno, child.name)
                if child_key in pdict:
                    pdict[child_key][4][caller_key] = (
                        child.nactualcall, child.ncall, child.tsub, child.ttot
                    )

        return pdict

    @staticmethod
    def _build_stats(request, stream):
        if yappi is not None:
            yappi.stop()

            # Find the current thread's yappi context ID
            current_tid = threading.current_thread().ident
            ctx_id = None
            for thread_stat in yappi.get_thread_stats():
                if thread_stat.tid == current_tid:
                    ctx_id = thread_stat.id
                    break

            if ctx_id is not None:
                func_stats = yappi.get_func_stats(filter={"ctx_id": ctx_id})
            else:
                func_stats = yappi.get_func_stats()

            request._iommi_yappi_func_stats = func_stats
            pdict = Middleware._yappi_stats_to_pstats_dict(func_stats)

            with NamedTemporaryFile(suffix='.prof', delete=False) as f:
                marshal.dump(pdict, f)
                f.flush()
                ps = HTMLStats(f.name, stream=stream)
            os.unlink(f.name)
            yappi.clear_stats()
        else:
            for prof in request._iommi_prof:
                prof.disable()
            ps = HTMLStats(*request._iommi_prof, stream=stream)
        return ps

    def __call__(self, request):
        if iscoroutinefunction(self):
            return self.__acall__(request)
        self._setup_request(request)
        if not should_profile(request):
            return self.get_response(request)
        self._start_profiling(request)
        response = self.get_response(request)
        return self._process_response(request, response)

    def _sync_profile(self, request):
        if not should_profile(request):
            return async_to_sync(self.get_response)(request)
        if getattr(request, '_iommi_view_is_async', False):
            return HttpResponse('Profiling is not supported for async views. Use an async-aware profiler instead.')
        self._start_profiling(request)
        response = async_to_sync(self.get_response)(request)
        return self._process_response(request, response)

    async def __acall__(self, request):
        self._setup_request(request)
        return await sync_to_async(self._sync_profile)(request)
