# Based on https://www.djangosnippets.org/snippets/186/

import cProfile
import marshal
import os
import pstats
import subprocess
import sys
import threading
import time
from collections import (
    Counter,
    defaultdict,
)
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

try:
    # The engine behind the statistical sampling profiler that CPython ships as
    # `python -m profiling.sampling` (3.15), and behind `asyncio.tools`. That profiler is
    # only exposed as an out-of-process command line tool, but the unwinder underneath it
    # can read our own process, which is what we want here: it samples with effectively no
    # overhead in the profiled thread, as opposed to cProfile/yappi which slow a request
    # down by something like 5-10x and thereby distort what they are measuring.
    import _remote_debugging
except ImportError:
    _remote_debugging = None

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


# How often the sampler thread tries to grab a stack. The sampler has to hold the GIL
# for the bookkeeping between samples, so the effective rate is also bounded by the
# interpreter switch interval, hence lowering that for the duration of the profiling.
SAMPLING_INTERVAL = 0.0005
SAMPLING_SWITCH_INTERVAL = 0.00005


def _iter_thread_info(stack_trace):
    """Tolerate both shapes this private API has had: threads grouped per interpreter (3.15+) and flat (3.14)."""
    for item in stack_trace:
        threads = getattr(item, 'threads', None)
        if threads is None:
            yield item
        else:
            yield from threads


# Before 3.15 the unwinder can't walk out of a frame that was entered from C, so resuming
# a generator or calling a dunder from a C function ends the walk right there. Rendering an
# iommi page does both constantly: measured on a 200 row table, 83% of the sampled stacks
# came back truncated on 3.14, against 0% on 3.15. Self time would still be correct, but
# cumulative times and flame graphs would be actively misleading, so don't offer sampling
# at all on older versions.
SAMPLING_SUPPORTED = _remote_debugging is not None and sys.version_info >= (3, 15)


class SamplingProfiler:
    """Samples the stack of a single thread from a sidecar thread.

    Unlike a tracing profiler this doesn't hook into the interpreter at all, so the
    profiled code runs at full speed. The trade-off is that there are no call counts,
    only statistical time attribution.
    """

    def __init__(self, interval=SAMPLING_INTERVAL, switch_interval=SAMPLING_SWITCH_INTERVAL):
        self.interval = interval
        self.switch_interval = switch_interval
        # The OS level id, which is what the unwinder reports. Note that this is a
        # different number than threading.get_ident().
        self.thread_id = threading.get_native_id()
        self.unwinder = None
        self.stop_event = threading.Event()
        # stack (leaf first, as (filename, lineno, funcname) tuples) -> number of samples
        self.stacks = Counter()
        self.sample_count = 0
        self.error_count = 0
        self.elapsed = 0.0
        self.thread = threading.Thread(target=self._run, name='iommi-sampling-profiler', daemon=True)

    def start(self):
        """Start sampling, or return False if this interpreter can't sample itself usefully."""
        if not SAMPLING_SUPPORTED:
            return False
        try:
            self.unwinder = _remote_debugging.RemoteUnwinder(os.getpid(), all_threads=True)
        except Exception:
            # Reading our own memory can fail because it isn't permitted, or because this
            # build gets it wrong: on macOS the duplicate libpython mapping that `ctypes`
            # creates defeats the lookup entirely on 3.15.0a2 and older. Fall back to a
            # tracing profiler rather than serving an empty profile.
            return False
        self.thread.start()
        return True

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=1)

    @property
    def sample_interval(self):
        """Measured mean time per sample, so that the reported times add up to the wall time."""
        if not self.sample_count:
            return 0.0
        return self.elapsed / self.sample_count

    def _sample(self):
        for thread_info in _iter_thread_info(self.unwinder.get_stack_trace()):
            if thread_info.thread_id == self.thread_id:
                return thread_info.frame_info
        return None

    def _run(self):
        previous_switch_interval = sys.getswitchinterval()
        if self.switch_interval:
            sys.setswitchinterval(self.switch_interval)
        start = time.perf_counter()
        try:
            while not self.stop_event.is_set():
                try:
                    frames = self._sample()
                    if frames:
                        self.stacks[tuple((f.filename, f.lineno, f.funcname) for f in frames)] += 1
                        self.sample_count += 1
                except Exception:
                    # A thread can go away between being listed and being unwound, and the
                    # whole point of this tool is to not take the request down with it.
                    self.error_count += 1
                time.sleep(self.interval)
        finally:
            self.elapsed = time.perf_counter() - start
            sys.setswitchinterval(previous_switch_interval)


class SampleAggregate:
    """Sampled stacks folded per function, in the shape the pstats/flamegraph output needs."""

    def __init__(self, stacks):
        self.self_samples = Counter()
        self.cumulative_samples = Counter()
        self.edges = Counter()
        linenos = defaultdict(Counter)

        for stack, count in stacks.items():
            leaf_filename, leaf_lineno, leaf_funcname = stack[0]
            self.self_samples[(leaf_filename, leaf_funcname)] += count

            seen = set()
            callee = None
            for filename, lineno, funcname in stack:
                function = (filename, funcname)
                linenos[function][lineno] += count
                # Guard against counting recursive frames more than once per sample.
                if function not in seen:
                    seen.add(function)
                    self.cumulative_samples[function] += count
                if callee is not None:
                    self.edges[(function, callee)] += count
                callee = function

        # A sampled frame reports the line currently executing rather than the line the
        # function is defined on, so pick the most sampled line as the representative one.
        # For a leaf that's the hot line, for a caller it's the hot call site.
        self.keys = {
            function: (function[0], counter.most_common(1)[0][0], function[1]) for function, counter in linenos.items()
        }

    def to_pstats_dict(self, sample_interval):
        pdict = {}
        for function, cumulative in self.cumulative_samples.items():
            pdict[self.keys[function]] = (
                # There is no call count in sampled data, so the ncalls column shows the
                # number of samples the function was on the stack for instead.
                cumulative,
                cumulative,
                self.self_samples[function] * sample_interval,
                cumulative * sample_interval,
                {},
            )

        callers_per_callee = defaultdict(list)
        for (caller, callee), count in self.edges.items():
            callers_per_callee[callee].append((caller, count))

        for callee, callers in callers_per_callee.items():
            total = sum(count for _, count in callers)
            for caller, count in callers:
                # Spread the callee's numbers over its callers in proportion to how many of
                # its samples came in through each of them. Going by the raw counts instead
                # would overshoot for anything that appears more than once in a stack, which
                # in turn makes gprof2dot warn about impossible ratios.
                portion = count / total
                pdict[self.keys[callee]][4][self.keys[caller]] = (
                    count,
                    count,
                    self.self_samples[callee] * portion * sample_interval,
                    self.cumulative_samples[callee] * portion * sample_interval,
                )

        return pdict


class _StatsSource:
    """Enough of the cProfile.Profile interface for `pstats.Stats` to load a raw dict."""

    def __init__(self, stats):
        self.stats = stats

    def create_stats(self):
        pass


def _html_stats(pdict, stream):
    # `pstats` refuses to load an empty dict, and a request can finish before the sampler
    # got a single sample in.
    return HTMLStats(_StatsSource(pdict) if pdict else None, stream=stream)


def _sampling_generate_folded_data(stacks, aggregate, sample_interval, threshold):
    total_samples = sum(stacks.values())
    if not total_samples:
        return ''

    lines = []
    for stack, count in stacks.items():
        if count / total_samples < threshold:
            continue
        microseconds = int(count * sample_interval * 1_000_000)
        if microseconds <= 0:
            continue
        # Root first, and using the representative line number per function so the same
        # function doesn't end up as several sibling boxes just because it was sampled at
        # different call sites.
        trace = [
            f'{funcname} ({aggregate.keys[(filename, funcname)][0]}:{aggregate.keys[(filename, funcname)][1]})'
            for filename, _, funcname in reversed(stack)
        ]
        lines.append(f'{";".join(trace)} {microseconds}')

    return '\n'.join(lines)


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
    # Set for sampled data, where call counts don't exist and the percall columns would
    # be meaningless.
    sampling = False
    sample_count = 0

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
        if self.sampling:
            percall_columns = ''
            first_column = f'<th class="numeric"><a href="{ncalls_url}">samples</a></th>'
        else:
            # language=HTML
            percall_columns = '<th class="numeric">percall</th>'
            first_column = f'<th class="numeric"><a href="{ncalls_url}">ncalls</a></th>'
        print(
            # language=HTML
            f'''
                <thead>
                    <tr>
                        {first_column}
                        <th class="numeric"><a href="{tottime_url}">tottime</a></th>
                        {percall_columns}
                        <th class="numeric"><a href="{cumtime_url}">cumtime</a></th>
                        {percall_columns}
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

        if self.sampling:
            print(indent, self.sample_count, "samples", end=' ', file=self.stream)
        else:
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
        if not self.sampling:
            if nc == 0:
                print('<td></td>', file=self.stream)
            else:
                print(f'<td>{f8(tt/nc)}</td>', file=self.stream)
        print(f'<td class="numeric">{f8(ct)}</td>', file=self.stream)
        if not self.sampling:
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

                threshold = float(request.GET.get('_iommi_prof_threshold', 0.00001)) / 100
                if hasattr(request, '_iommi_sample_aggregate'):
                    sampling_profiler = request._iommi_sampling_profiler
                    folded_data = _sampling_generate_folded_data(
                        sampling_profiler.stacks,
                        request._iommi_sample_aggregate,
                        sampling_profiler.sample_interval,
                        threshold,
                    )
                elif hasattr(request, '_iommi_yappi_func_stats'):
                    folded_data = _yappi_generate_folded_data(request._iommi_yappi_func_stats, threshold)
                else:
                    return HttpResponse('You must `pip install yappi` to use the flamegraph feature')

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
        sampling_profiler = SamplingProfiler()
        if sampling_profiler.start():
            request._iommi_sampling_profiler = sampling_profiler
            request._iommi_prof = True
        elif yappi is not None:
            yappi.set_clock_type("wall")
            yappi.clear_stats()
            yappi.start(builtins=True)
            request._iommi_prof = True
        else:
            prof = cProfile.Profile()
            prof.enable()
            request._iommi_prof = [prof]

    @staticmethod
    def _stop_profiling(request):
        # The sampler is a real thread that has lowered the interpreter switch interval, so
        # it must be stopped even if the view blew up.
        sampling_profiler = getattr(request, '_iommi_sampling_profiler', None)
        if sampling_profiler is not None:
            sampling_profiler.stop()

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
        sampling_profiler = getattr(request, '_iommi_sampling_profiler', None)
        if sampling_profiler is not None:
            sampling_profiler.stop()
            aggregate = SampleAggregate(sampling_profiler.stacks)
            sample_interval = sampling_profiler.sample_interval
            request._iommi_sample_aggregate = aggregate
            ps = _html_stats(aggregate.to_pstats_dict(sample_interval), stream)
            ps.sampling = True
            ps.sample_count = sampling_profiler.sample_count
        elif yappi is not None:
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
        try:
            response = self.get_response(request)
        finally:
            self._stop_profiling(request)
        return self._process_response(request, response)

    def _sync_profile(self, request):
        if not should_profile(request):
            return async_to_sync(self.get_response)(request)
        if getattr(request, '_iommi_view_is_async', False):
            return HttpResponse('Profiling is not supported for async views. Use an async-aware profiler instead.')
        self._start_profiling(request)
        try:
            response = async_to_sync(self.get_response)(request)
        finally:
            self._stop_profiling(request)
        return self._process_response(request, response)

    async def __acall__(self, request):
        self._setup_request(request)
        return await sync_to_async(self._sync_profile)(request)
