# Based on https://www.djangosnippets.org/snippets/186/

import cProfile
import os
import pstats
import subprocess
import sys
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.http.response import (
    HttpResponseBase,
    StreamingHttpResponse,
)
from django.utils.html import escape

from iommi._web_compat import (
    HttpResponse,
    settings,
)
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
    def print_title(self):
        print(
            # language=HTML
            '''
                <thead>
                    <tr>
                        <th class="numeric"><a href="?_iommi_prof=ncalls">ncalls</a></th>
                        <th class="numeric"><a href="?_iommi_prof=tottime">tottime</a></th>
                        <th class="numeric">percall</th>
                        <th class="numeric"><a href="?_iommi_prof=cumtime">cumtime</a></th>
                        <th class="numeric">percall</th>
                        <th>function</th>
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


class Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Disable profiling early on /media requests since touching request.user will add a
        # "Vary: Cookie" header to the response.
        request.profiler_disabled = False
        for prefix in MEDIA_PREFIXES:
            if request.path.startswith(prefix):
                request.profiler_disabled = True
                break

        if not should_profile(request):
            return self.get_response(request)

        prof = cProfile.Profile()
        prof.enable()
        request._iommi_prof = [prof]

        response = self.get_response(request)

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
            for prof in request._iommi_prof:
                prof.disable()

            s = StringIO()
            ps = HTMLStats(*request._iommi_prof, stream=s)

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

            elif prof_command == 'snake':
                # noinspection PyPackageRequirements
                try:
                    import snakeviz  # noqa
                except ImportError:
                    return HttpResponse('You must `pip install snakeviz` to use this feature')

                with NamedTemporaryFile() as stats_dump:
                    ps.stream = stats_dump
                    ps.dump_stats(stats_dump.name)

                    subprocess.Popen(
                        [sys.executable, str(Path(sys.executable).parent / 'snakeviz'), stats_dump.name],
                        stdin=None,
                        stdout=None,
                        stderr=None,
                    )

                    # We need to wait a bit to give snakeviz time to read the file
                    from time import sleep

                    sleep(3)

                return HttpResponse(
                    'You should have gotten a new browser window with snakeviz opened to the profile data'
                )

            else:
                ps = ps.sort_stats(prof_command or 'cumulative')
                ps.print_stats()

                result = s.getvalue()

                # language=html
                start_html = '''
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
                        <a href="?_iommi_prof=graph">graph</a>
                        <a href="?_iommi_prof=snake">snakeviz</a>
                    </div>

                    <p></p>
                '''

                response.content = start_html.strip() + result

                response['Content-Type'] = 'text/html'

        return response
