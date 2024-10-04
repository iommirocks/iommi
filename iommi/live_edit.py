import inspect
import json
from pathlib import Path

from django.conf import settings
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
)
from django.utils import autoreload
from django.views.decorators.csrf import csrf_exempt

from iommi import (
    Asset,
    Page,
    Part,
    Style,
    html,
    render_if_needed,
    render_part,
)
from iommi._web_compat import mark_safe
from iommi.base import get_wrapped_view, items
from iommi.struct import Struct
from iommi.style import (
    get_global_style,
    register_style,
)

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
            return live_edit_dispatch(request)(
                request=request, view=callback, args=callback_args, kwargs=callback_kwargs
            )


def live_edit_dispatch(request):
    return {
        '': live_edit_view,
        'stop': live_edit_view,
        'style_showcase': style_showcase,
        'style_editor__edit': style_editor__edit,
        'style_editor__new': style_editor__new,
        'style_editor': style_editor__select,
    }[request.GET['_iommi_live_edit']]


def should_edit(request):
    return settings.DEBUG and '_iommi_live_edit' in request.GET


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


def get_class_ast(cls):
    import parso

    filename = inspect.getsourcefile(cls)
    with open(filename) as f:
        entire_file = f.read()

    is_unix_line_endings = '\r\n' not in entire_file

    ast_of_entire_file = parso.parse(entire_file)
    return (
        find_node(name=cls.__name__, node=ast_of_entire_file, node_type='classdef'),
        is_unix_line_endings,
        ast_of_entire_file,
        filename,
    )


def create_response_for_view(new_view, request, args, kwargs, **_):
    if isinstance(new_view, type) and issubclass(new_view, Part):
        response = new_view().as_view()(request, *args, **kwargs)
    else:
        response = new_view(request, *args, **kwargs)
    return render_if_needed(request, response)


def get_ast(view):
    import parso

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

    if ast_of_old_code is None:
        return get_class_ast(view.__class__)

    return ast_of_old_code, is_unix_line_endings, ast_of_entire_file, filename


def live_edit_post_handler(request, code, view, filename, create_response, write_new_code_to_disk, **params):
    try:
        final_result = dangerous_execute_code(
            code, request, view, create_response=create_response, args=params['args'], kwargs=params['kwargs']
        )

        if orig_reload is not None:
            # A little monkey patch dance to avoid one reload of the runserver when it's just us writing the code to disk
            # This only works in django 2.2+
            def restore_auto_reload(filename):
                from django.utils import autoreload

                print('Skipped reload')
                autoreload.trigger_reload = orig_reload

            autoreload.trigger_reload = restore_auto_reload

        write_new_code_to_disk(code=code, filename=filename, view=view, **params)

        return final_result
    except Exception as e:
        import traceback

        traceback.print_exc()
        error = str(e)
        if not error:
            error = str(e.__class__)
        return HttpResponse(json.dumps(dict(error=error)))


def write_new_code_to_disk_for_view(ast_of_entire_file, ast_of_old_code, code, filename, view, **_):
    import parso

    if isinstance(view, Part):
        ast_of_new_code = find_node(name=view.__class__.__name__, node=parso.parse(code), node_type='classdef')
    else:
        ast_of_new_code = find_node(name=view.__name__, node=parso.parse(code), node_type='funcdef')
    ast_of_old_code.children[:] = ast_of_new_code.children
    new_code = ast_of_entire_file.get_code()
    with open(filename, 'w') as f:
        f.write(new_code)


@csrf_exempt
def live_edit_view(request, view, args=None, kwargs=None):
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    try:
        import parso
    except ImportError:
        return HttpResponse('Live edit requires parso. Please `pip install parso`.')

    view = get_wrapped_view(view)
    # Read the old code
    try:
        # view is a function based view
        filename = view.__globals__['__file__']
    except AttributeError:
        # view is an iommi class
        from iommi.debug import filename_and_line_num_from_part

        filename, _ = filename_and_line_num_from_part(view)

    def build_params(entire_file, **_):
        ast_of_entire_file = parso.parse(entire_file)

        ast_of_old_code = find_view(view, ast_of_entire_file)
        assert ast_of_old_code is not None
        return dict(
            ast_of_entire_file=ast_of_entire_file,
            ast_of_old_code=ast_of_old_code,
        )

    flow_direction = request.GET.get('_iommi_live_edit_flow') or 'column'

    if request.GET.get('_iommi_live_edit') == 'stop':
        Path(filename).touch()
        return HttpResponseRedirect('.')
    assert flow_direction in ('column', 'row')

    return live_edit_view_impl(
        request,
        view=view,
        filename=filename,
        build_params=build_params,
        create_response=create_response_for_view,
        get_code=lambda ast_of_old_code, **_: ast_of_old_code.get_code(),
        write_new_code_to_disk=write_new_code_to_disk_for_view,
        flow_direction=flow_direction,
        args=args,
        kwargs=kwargs,
    )


def live_edit_view_impl(
    request,
    view,
    filename,
    build_params,
    get_code,
    create_response,
    write_new_code_to_disk,
    flow_direction,
    args,
    kwargs,
):
    with open(filename) as f:
        entire_file = f.read()

    is_unix_line_endings = '\r\n' not in entire_file

    params = {
        'entire_file': entire_file,
        'is_unix_line_endings': is_unix_line_endings,
        'view': view,
        'filename': filename,
        'request': request,
        'create_response': create_response,
        'write_new_code_to_disk': write_new_code_to_disk,
        'args': args,
        'kwargs': kwargs,
    }
    params = {
        **params,
        **build_params(**params),
    }

    if request.method == 'POST':
        code = request.POST['data'].replace('\t', '    ')
        if is_unix_line_endings:
            code = code.replace('\r\n', '\n')
        params['code'] = code
        return live_edit_post_handler(**params)

    code = get_code(**params)

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
            # language=css
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

                .container #editor_and_error {
                    flex: 2 1 auto;
                }

                #editor {
                    height: 90% !important;
                }

                #error {
                    height: 10% !important;
                }
            '''.replace('<<flow_direction>>', flow_direction),
        ),
        iommi_style='bootstrap',
        parts__result=html.iframe(attrs__id='result'),
        parts__editor_and_error=html.div(
            attrs__id='editor_and_error',
            children=dict(
                editor=html.div(
                    code,
                    attrs__id='editor',
                ),
                error=html.div(attrs__id='error'),
            ),
        ),
        parts__script=html.script(
            mark_safe(
                # language=javascript
                '''
                    var editor = ace.edit("editor");
                    editor.setTheme("ace/theme/cobalt");
                    editor.session.setMode("ace/mode/python");
                    editor.setShowPrintMargin(false);

                    async function update() {
                        if (window.iommi_live_edit_updating) {
                            return;
                        }

                        window.iommi_live_edit_updating = true;
                        window.iommi_live_edit_needs_update = false;

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
                        document.getElementById('error').innerText = foo.error || '';
                        window.iommi_live_edit_updating = false;
                    }

                    setInterval(() => {
                        if (!window.iommi_live_edit_needs_update) {
                            return;
                        }
                        update();
                    }, 200)

                    window.iommi_live_edit_updating = false;
                    window.iommi_live_edit_needs_update = true;

                    editor.session.on('change', () => {window.iommi_live_edit_needs_update = true});
                    editor.setFontSize(14);
                    editor.session.setUseWrapMode(true);
                '''
            )
        ),
    )


def dangerous_execute_code(code, request, view, args, kwargs, create_response=create_response_for_view):
    local_variables = {}
    if isinstance(view, Part):
        from importlib import import_module

        module = import_module(view.__module__)
        exec(code, module.__dict__, local_variables)
    elif isinstance(view, Style):
        frame = view._instantiated_at_frame.f_back
        exec(code, frame.f_globals, local_variables)
    else:
        exec(code, view.__globals__, local_variables)
    request.method = 'GET'
    request.GET = request.GET.copy()
    request.GET['_iommi_disable_debug_panel'] = ''
    new_view = list(local_variables.values())[0]
    response = create_response(new_view, request=request, args=args, kwargs=kwargs, local_variables=local_variables)
    final_result = HttpResponse(json.dumps(dict(page=response.content.decode())))
    return final_result


def style_showcase(request, style=None, **_):
    from django.contrib.auth.models import User

    if style is None:
        from iommi.style import DEFAULT_STYLE

        style = getattr(settings, 'IOMMI_DEFAULT_STYLE', DEFAULT_STYLE)

    class DummyRow:
        def __init__(self, idx):
            self.idx = idx

        def __getattr__(self, attr):
            _, _, shortcut = attr.partition('column_of_type_')
            s = f'{shortcut} #{self.idx}'
            if shortcut == 'link' or attr == 'link':

                class Link:
                    def get_absolute_url(self):
                        return '#'

                    def __str__(self):
                        return 'title'

                return Link()
            if shortcut == 'number':
                return f'{self.idx}'
            return s

        @staticmethod
        def get_absolute_url():
            return '#'

    from iommi import (
        Action,
        Column,
        Field,
        Form,
        Header,
        Menu,
        MenuItem,
        Table,
    )

    return Page(
        iommi_style=style,
        parts=dict(
            title=Header('Style showcase'),
            menu__children=dict(
                menu_title=html.h2('Menu'),
                menu=Menu(
                    sub_menu=dict(
                        active=MenuItem(url=request.get_full_path()),  # full path do make this item active
                        inactive=MenuItem(),
                    )
                ),
            ),
            h_tags=html.div(
                children=dict(
                    h1=Header(tag='h1', children__text='h1'),
                    h2=Header(tag='h2', children__text='h2'),
                    h3=Header(tag='h3', children__text='h3'),
                    h4=Header(tag='h4', children__text='h4'),
                ),
            ),
            form=Form(
                title='Form',
                fields=dict(
                    text=Field.text(initial='initial'),
                    boolean=Field.boolean(),
                    boolean_selected=Field.boolean(initial=True),
                    radio=Field.radio(choices=['a', 'b', 'c'], initial='b'),
                    integer=Field.integer(initial=123),
                ),
                actions__submit__post_handler=lambda **_: None,
                actions__secondary=Action.button(),
                actions__delete=Action.delete(display_name='Delete'),
                actions__icon=Action.icon('trash', display_name='Icon', attrs__href='#'),
            ),
            table=Table(
                title='Table',
                model=User,
                columns={
                    t.__name__: dict(call_target=t, display_name=t.__name__)
                    for t in [
                        Column.select,
                        Column.edit,
                        Column.delete,
                        Column.boolean,
                        Column.text,
                        Column.number,
                        Column.link,
                        Column.icon,
                    ]
                },
                columns__text__filter__include=True,
                columns__number__filter__include=True,
                rows=[DummyRow(i) for i in range(10)],
                page_size=2,
            ),
        ),
    )


def style_editor__select(**_):
    from iommi import Action, Field, Form
    from iommi.style import _styles

    return Form(
        title='Select style to edit',
        fields__name=Field.choice(choices=[k for k, v in items(_styles) if not v.internal]),
        actions__edit=Action.primary(
            display_name='Edit',
            post_handler=lambda form, **_: HttpResponseRedirect(
                f'?_iommi_live_edit=style_editor__edit&name={form.fields.name.value}'
            )
            if form.is_valid()
            else None,
        ),
        actions__new_style__attrs__href='?_iommi_live_edit=style_editor__new',
    )


@csrf_exempt
def style_editor__edit(request, **_):
    name = request.GET.get('name', request.POST.get('name'))
    assert name is not None
    style = get_global_style(name)
    filename = style._instantiated_at_frame.f_back.f_code.co_filename

    def create_response(view, local_variables, **_):
        view._instantiated_at_frame = (
            style._instantiated_at_frame
        )  # otherwise we end up at <string> which is not what we want
        style_editor_name = 'style_editor'
        with register_style(style_editor_name, style=local_variables[name], allow_overwrite=True):
            return render_part(
                request,
                style_showcase(request, style=style_editor_name),
            )

    def write_new_code_to_disk(code, **_):
        with open(filename, 'w') as f:
            f.write(code)

    return live_edit_view_impl(
        request,
        view=style,  # TODO: rename view.. "subject"?
        filename=filename,
        build_params=lambda **_: {},
        get_code=lambda entire_file, **_: entire_file,
        create_response=create_response,
        write_new_code_to_disk=write_new_code_to_disk,
        flow_direction='row',
        args=[],
        kwargs={},
    )


def style_editor__new(**_):
    from iommi import (
        Field,
        Form,
        Header,
    )

    def new_style(form, **_):
        if not form.is_valid():
            return

        base, _, new = form.fields.module.value.rpartition('.')
        module = __import__(base, fromlist=['_silly_importlib'])
        target_filename = Path(module.__file__).parent / (new + '.py')
        if target_filename.exists():
            form.add_error(f'File {target_filename} already exists')

        with open(target_filename, 'w') as f:
            f.write(
                f'''
from iommi.style import Style
from iommi.style_base import base
from iommi.asset import Asset

{new} = Style(
    base,
)
'''
            )
            return Page(
                parts=dict(
                    title=Header('Style created... now what?'),
                    message=html.p(
                        f'''
                            The style file was written to {target_filename}.
                            Now you need to register this style in order to edit it. This is
                            typically done by adding `register_style('{new}')` into `on_ready`
                            of your `AppConfig`.
                        '''
                    ),
                    message2=html.p("When you've done that, you can proceed to "),
                    edit=html.a('edit it', attrs__href=f'?_iommi_live_edit=style_editor__edit&name={new}'),
                ),
            )

    return Form(
        title='Create new style',
        fields=dict(
            module=Field(),  # TODO: can we guess this in a smart way? maybe look at settings.__module__?
        ),
        actions__submit__post_handler=new_style,
    )
