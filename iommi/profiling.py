# Based on https://www.djangosnippets.org/snippets/186/

import cProfile
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from iommi._web_compat import HttpResponse
from ._web_compat import settings

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

    return '_iommi_prof' in request.GET and ((not disabled and is_staff) or settings.DEBUG)


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

        if should_profile(request):
            prof = cProfile.Profile()
            prof.enable()
        else:
            prof = None

        response = self.get_response(request)

        if prof is not None:
            response = HttpResponse()
            prof.disable()

            import pstats

            s = StringIO()
            ps = pstats.Stats(prof, stream=s).sort_stats(request.GET.get('_iommi_prof') or 'cumulative')
            ps.print_stats()

            stats_str = s.getvalue()

            if 'graph' in request.GET:
                with NamedTemporaryFile() as stats_dump:
                    ps.stream = stats_dump
                    ps.dump_stats(stats_dump.name)

                    gprof2dot_path = Path(sys.executable).parent / 'gprof2dot'
                    if not gprof2dot_path.exists():
                        raise Exception('gprof2dot not found. Please install it to use the graph feature.')

                    gprof2dot = subprocess.Popen(
                        (sys.executable, gprof2dot_path, '-f', 'pstats', stats_dump.name), stdout=subprocess.PIPE
                    )

                    response['Content-Type'] = 'image/svg+xml'

                    dot_path = get_dot_path()
                    if dot_path:
                        response.content = subprocess.check_output((dot_path, '-Tsvg'), stdin=gprof2dot.stdout)
                    else:
                        response['Content-Type'] = 'text/plain'
                        response['Content-Disposition'] = "attachment; filename=gprof2dot-graph.txt"
                        response.content = subprocess.check_output('tee', stdin=gprof2dot.stdout)

            else:
                limit = 280
                result = []

                def strip_extra_path(s, token):
                    if token not in s:
                        return s
                    pre, _, post = s.rpartition(' ')
                    post = post[post.rindex(token) + len(token) :]
                    return f'{pre} {post}'

                base_dir = str(settings.BASE_DIR)
                for line in stats_str.split("\n")[:limit]:
                    should_bold = base_dir in line and '/site-packages/' not in line
                    line = line.replace(base_dir, '')
                    line = strip_extra_path(line, '/site-packages')
                    line = strip_extra_path(line, '/Python.framework/Versions')
                    if should_bold:
                        line = f'<b>{line}</b>'

                    line = line.replace(' ', '&nbsp;')
                    result.append(line)

                start_html = '''
                <style>
                    html {
                        font-family: monospace; 
                        white-space: nowrap;
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
                <div>'''
                lines_html = "<br />\n".join(result)
                end_html = '</div>'

                response.content = start_html + lines_html + end_html

                response['Content-Type'] = 'text/html'

        return response
