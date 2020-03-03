# Based on https://www.djangosnippets.org/snippets/186/

import cProfile
import os
import subprocess
from io import StringIO
from tempfile import NamedTemporaryFile

from django.conf import settings

from iommi._web_compat import HttpResponse

MEDIA_PREFIXES = ['/static/']


class ProfileMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.prof = None

    def process_view(self, request, callback, callback_args, callback_kwargs):
        disabled = getattr(request, 'profiler_disabled', True)
        is_staff = hasattr(request, 'user') and request.user.is_staff

        if 'prof' in request.GET and not disabled and is_staff:
            return self.prof.runcall(callback, request, *callback_args, **callback_kwargs)

    def __call__(self, request):
        # Disable profiling early on /media requests since touching request.user will add a
        # "Vary: Cookie" header to the response.
        request.profiler_disabled = False
        for prefix in MEDIA_PREFIXES:
            if request.path.startswith(prefix):
                request.profiler_disabled = True
                break
        if not request.profiler_disabled and (settings.DEBUG or request.user.is_staff) and 'prof' in request.GET:
            self.prof = cProfile.Profile()
            self.prof.enable()

        response = self.get_response(request)

        disabled = getattr(request, 'profiler_disabled', True)
        is_staff = hasattr(request, 'user') and request.user.is_staff

        if 'prof' in request.GET and not disabled and is_staff:
            response = HttpResponse()
            self.prof.disable()

            import pstats
            s = StringIO()
            ps = pstats.Stats(self.prof, stream=s).sort_stats(request.GET.get('prof') or 'cumulative')
            ps.print_stats()

            stats_str = s.getvalue()

            if 'graph' in request.GET:
                with NamedTemporaryFile() as stats_dump:
                    ps.stream = stats_dump
                    ps.dump_stats(stats_dump.name)

                    gprof2dot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin', 'profiling', 'gprof2dot.py')
                    gprof2dot = subprocess.Popen(('python', gprof2dot_path, '-f', 'pstats', stats_dump.name), stdout=subprocess.PIPE)

                    response['Content-Type'] = 'image/svg+xml'
                    if os.path.exists('/usr/bin/dot'):
                        response.content = subprocess.check_output(('/usr/bin/dot', '-Tsvg'), stdin=gprof2dot.stdout)
                    elif os.path.exists('/usr/local/bin/dot'):
                        response.content = subprocess.check_output(('/usr/local/bin/dot', '-Tsvg'), stdin=gprof2dot.stdout)
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
                    post = post[post.rindex(token) + len(token):]
                    return f'{pre} {post}'

                for line in stats_str.split("\n")[:limit]:
                    should_bold = settings.BASE_DIR in line and '/site-packages/' not in line or '/tri/' in line
                    line = line.replace(settings.BASE_DIR, '')
                    line = strip_extra_path(line, '/site-packages')
                    line = strip_extra_path(line, '/Python.framework/Versions')
                    if should_bold:
                        line = f'<b>{line}</b>'

                    line = line.replace(' ', '&nbsp;')
                    result.append(line)

                response.content = '<div style="font-family: monospace; white-space: nowrap">%s</div' % "<br />\n".join(result)

                response['Content-Type'] = 'text/html'

        return response
