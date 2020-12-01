import json

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import autoreload
from tri_struct import Struct

from iommi import *
from iommi import render_if_needed
from iommi._web_compat import mark_safe
from tests.helpers import req
import parso

orig_reload = autoreload.trigger_reload


class Middleware:
    """
    The live edit middleware enables editing of the source code of views with as-you-type results, inside the web browser.

    Note: This middleware needs to go *first* in the middleware list.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def should_edit(self, request):
        return settings.DEBUG and '_iommi_live_edit' in request.GET

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if self.should_edit(request):
            while hasattr(callback, '__wrapped__'):
                callback = callback.__wrapped__

            if hasattr(callback, '__iommi_target__'):
                assert False, "Edit mode isn't supported for the as_view() style yet."

            return live_edit_view(request, callback)


def find_function(*, name, node):
    if getattr(node, 'name', Struct(value=None)).value == name:
        return node
    for child_node in getattr(node, 'children', []):
        r = find_function(node=child_node, name=name)
        if r is not None:
            return r
    return None


@csrf_exempt
def live_edit_view(request, view_func):
    # Read the old code
    filename = view_func.__globals__['__file__']
    with open(filename) as f:
        entire_file = f.read()
        ast_of_entire_file = parso.parse(entire_file)

    is_unix_line_endings = '\r\n' not in entire_file

    ast_of_old_code = find_function(name=view_func.__name__, node=ast_of_entire_file)

    if request.method == 'POST':
        try:

            # indent all the code once
            code = request.POST['data'].replace('\t', '    ')
            if is_unix_line_endings:
                code = code.replace('\r\n', '\n')

            local_variables = {}
            exec(code, view_func.__globals__, local_variables)
            assert len(local_variables) == 1
            request = req('get')
            response = list(local_variables.values())[0](request)
            response = render_if_needed(request, response)
            final_result = HttpResponse(json.dumps(dict(page=response.content.decode())))

            ast_of_new_code = find_function(name=view_func.__name__, node=parso.parse(code))

            ast_of_old_code.children[:] = ast_of_new_code.children

            # A little monkey patch dance to avoid one reload of the runserver when it's just us writing the code to disk
            def restore_auto_reload(filename):
                from django.utils import autoreload
                print('Skipped reload')
                autoreload.trigger_reload = orig_reload

            autoreload.trigger_reload = restore_auto_reload

            new_code = ast_of_entire_file.get_code()
            with open(filename, 'w') as f:
                f.write(new_code)

            return final_result
        except Exception as e:
            return HttpResponse(json.dumps(dict(error=str(e))))

    return Page(
        assets__code_editor=Asset.js(
            attrs=dict(
                src='https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/ace.js',
                integrity='sha512-GZ1RIgZaSc8rnco/8CXfRdCpDxRCphenIiZ2ztLy3XQfCbQUSCuk8IudvNHxkRA3oUg6q0qejgN/qqyG1duv5Q==',
                crossorigin='anonymous',
            ),
            after=-1,
        ),
        assets__custom=Asset(
            tag='style',
            text='''
            .container {
                padding: 0 !important;           
                margin: 0 !important;
                max-width: 100%;
            }

            html,
            body {
              height: 100%;
              margin: 0;
            }

            .container {
              display: flex;
              flex-flow: column;
              height: 100%;
            }

            .container iframe {
              flex: 5 1 auto;
            }
            .container div {
              flex: 1 1 auto;
            }
            nav {
                display: none;
            }
            '''
        ),

        parts__result=html.iframe(attrs__id='result', attrs__style=dict(width='100%', height='400px')),
        parts__editor=html.div(
            ast_of_old_code.get_code(),
            attrs=dict(
                style__height='500px',
                id='editor',
            ),
        ),

        parts__script=html.script(mark_safe('''
        function iommi_debounce(func, wait) {
            let timeout;

            return (...args) => {
                const fn = () => func.apply(this, args);

                clearTimeout(timeout);
                timeout = setTimeout(() => fn(), wait);
            };
        }

        var editor = ace.edit("editor");
        editor.setTheme("ace/theme/cobalt");
        editor.session.setMode("ace/mode/python");
        editor.setShowPrintMargin(false);

        async function update() {
            let form_data = new FormData();
            form_data.append('data', editor.getValue());

            let response = await fetch('', {
                method: 'POST',
                body: form_data
            });
            let foo = await response.json();
            if (foo.page) {
                document.getElementById('result').srcdoc = foo.page;
            }
        }


        function foo() {
            iommi_debounce(update, 200)();
        }

        editor.session.on('change', foo);
        editor.setFontSize(14);
        
        foo();
        ''')),
    )
