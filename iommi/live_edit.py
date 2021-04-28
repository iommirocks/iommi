import json

import parso
from django.conf import settings
from django.http import HttpResponse
from django.utils import autoreload
from django.views.decorators.csrf import csrf_exempt
from tri_struct import Struct

from iommi import (
    Asset,
    html,
    Page,
    Part,
    render_if_needed,
)
from iommi._web_compat import mark_safe

orig_reload = getattr(autoreload, 'trigger_reload', None)


class Middleware:
    """
    The live edit middleware enables editing of the source code of views with as-you-type results, inside the web browser.

    Note: This middleware needs to go *first* in the middleware list.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if should_edit(request):
            return live_edit_view(request, callback, callback_args, callback_kwargs)


def should_edit(request):
    return settings.DEBUG and '_iommi_live_edit' in request.GET


def get_wrapped_view(view):
    if hasattr(view, '__iommi_target__'):
        view = view.__iommi_target__

    while hasattr(view, '__wrapped__'):
        view = view.__wrapped__

    return view


def include_decorators(node):
    while node.parent.type == 'decorated':
        node = node.parent
    return node


def find_node(*, name, node, node_type):
    """
    node_type should be either funcdef or classdef
    """
    if node.type == node_type:
        if getattr(node, 'name', Struct(value=None)).value == name:
            return node
    for child_node in getattr(node, 'children', []):
        r = find_node(node=child_node, name=name, node_type=node_type)
        if r is not None:
            return include_decorators(r)
    return None


def find_view(view, ast_of_entire_file):
    if isinstance(view, Part):
        return find_node(name=type(view).__name__, node=ast_of_entire_file, node_type='classdef')
    else:
        return find_node(name=view.__name__, node=ast_of_entire_file, node_type='funcdef')


# This class exists just to provide a way to style the page
class LiveEditPage(Page):
    pass


@csrf_exempt
def live_edit_view(request, view, args, kwargs):
    view = get_wrapped_view(view)
    # Read the old code
    try:
        # view is a function based view
        filename = view.__globals__['__file__']
    except AttributeError:
        # view is an iommi class
        from iommi.debug import filename_and_line_num_from_part

        filename, _ = filename_and_line_num_from_part(view)

    with open(filename) as f:
        entire_file = f.read()
        ast_of_entire_file = parso.parse(entire_file)

    is_unix_line_endings = '\r\n' not in entire_file

    ast_of_old_code = find_view(view, ast_of_entire_file)
    assert ast_of_old_code is not None

    flow_direction = request.GET.get('_iommi_live_edit') or 'column'
    assert flow_direction in ('column', 'row')

    if request.method == 'POST':
        try:
            code = request.POST['data'].replace('\t', '    ')
            if is_unix_line_endings:
                code = code.replace('\r\n', '\n')
            final_result = dangerous_execute_code(code, request, view, args, kwargs)

            if orig_reload is not None:
                # A little monkey patch dance to avoid one reload of the runserver when it's just us writing the code to disk
                # This only works in django 2.2+
                def restore_auto_reload(filename):
                    from django.utils import autoreload

                    print('Skipped reload')
                    autoreload.trigger_reload = orig_reload

                autoreload.trigger_reload = restore_auto_reload

            if isinstance(view, Part):
                ast_of_new_code = find_node(name=view.__class__.__name__, node=parso.parse(code), node_type='classdef')
            else:
                ast_of_new_code = find_node(name=view.__name__, node=parso.parse(code), node_type='funcdef')
            ast_of_old_code.children[:] = ast_of_new_code.children
            new_code = ast_of_entire_file.get_code()
            with open(filename, 'w') as f:
                f.write(new_code)

            return final_result
        except Exception as e:
            import traceback

            traceback.print_exc()
            error = str(e)
            if not error:
                error = str(e.__class__)
            return HttpResponse(json.dumps(dict(error=error)))

    return LiveEditPage(
        title='iommi live edit',
        h_tag__include=False,
        assets__code_editor=Asset.js(
            attrs=dict(
                src='https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/ace.js',
                integrity='sha512-GZ1RIgZaSc8rnco/8CXfRdCpDxRCphenIiZ2ztLy3XQfCbQUSCuk8IudvNHxkRA3oUg6q0qejgN/qqyG1duv5Q==',
                crossorigin='anonymous',
            ),
            after=-1,
        ),
        assets__live_edit_page_custom=Asset(
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
                    flex-flow: <<flow_direction>>;
                    height: 100%;
                }

                .container iframe {
                    flex: 1 1 auto;
                    border: 0;
                }

                .container #editor {
                    flex: 2 1 auto;
                }
            '''.replace(
                '<<flow_direction>>', flow_direction
            ),
        ),
        parts__result=html.iframe(attrs__id='result'),
        parts__editor=html.div(
            ast_of_old_code.get_code(),
            attrs__id='editor',
        ),
        parts__script=html.script(
            mark_safe(
                '''
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
                            // TODO: get scroll position and restore it
                            document.getElementById('result').srcdoc = foo.page;
                        }
                    }

                    function foo() {
                        iommi_debounce(update, 200)();
                    }

                    editor.session.on('change', foo);
                    editor.setFontSize(14);
                    editor.session.setUseWrapMode(true);

                    foo();
        '''
            )
        ),
    )


def dangerous_execute_code(code, request, view, args, kwargs):
    local_variables = {}
    if isinstance(view, Part):
        from importlib import import_module
        module = import_module(view.__module__)
        exec(code, module.__dict__, local_variables)
    else:
        exec(code, view.__globals__, local_variables)
    assert len(local_variables) == 1
    request.method = 'GET'
    request.GET = request.GET.copy()
    request.GET['_iommi_disable_debug_panel'] = ''
    new_view = list(local_variables.values())[0]
    if isinstance(new_view, type) and issubclass(new_view, Part):
        response = new_view().bind(request=request).render_to_response()
    else:
        response = new_view(request, *args, **kwargs)
    response = render_if_needed(request, response)
    final_result = HttpResponse(json.dumps(dict(page=response.content.decode())))
    return final_result
