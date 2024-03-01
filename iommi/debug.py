import inspect
import sys
from os.path import (
    dirname,
    isabs,
    join,
)

from django.http import HttpResponse
from django.template.loader import get_template

from iommi._web_compat import (
    HttpRequest,
    Template,
    format_html,
    mark_safe,
)
from iommi.base import items
from iommi.member import (
    MemberBinder,
    Members,
)
from iommi.struct import Struct
from iommi.traversable import (
    PathNotFoundException,
    Traversable,
    declared_members,
)

from ._web_compat import settings


def iommi_debug_on():
    return getattr(settings, 'IOMMI_DEBUG', settings.DEBUG)


def dunder_path__format(row, **_):
    if row.dunder_path is None:
        return ''
    prefix = row.dunder_path.rpartition('__')[0]
    return format_html(
        '<span class="full-path">{prefix}{separator}</span>{name}',
        prefix=prefix,
        separator='__' if prefix else '',
        name=row.name,
    )


def endpoint__debug_tree(endpoint, **_):
    root = endpoint.iommi_root()
    assert root._is_bound

    def rows(node, name='', path=None):
        if path is None:
            path = []
        is_struct = type(node) is Struct
        is_bound = getattr(node, '_is_bound', False)

        try:
            p = node.iommi_path if is_bound else None
        except PathNotFoundException:
            p = None

        type_name = type(node).__name__ if not is_struct else None
        prefix = ''
        if isinstance(node, Members):
            if node._declared_members:
                type_name = node._cls.__name__
                prefix = 'Contains '
            else:
                return

        children = []
        if isinstance(node, dict):
            children = list(node.items())
        elif isinstance(node, Traversable):
            children = []
            for k, v in items(declared_members(node)):
                if node._bound_members is not None and isinstance(node._bound_members.get(k, None), MemberBinder):
                    node._bound_members[k]._force_bind_all()
                children.append((k, (node._bound_members or {}).get(k, v)))

        if (isinstance(node, Members) or isinstance(node, dict)) and not children:
            return

        display_name = type_name
        shortcut_stack = getattr(node, 'iommi_shortcut_stack', None)
        shortcut = shortcut_stack[0] if shortcut_stack else None
        if shortcut:
            display_name = f'{type_name}.{shortcut}'
        yield Struct(
            name=name,
            obj=node,
            prefix=prefix,
            type_name=type_name,
            display_name=display_name,
            shortcut=shortcut,
            path=p,
            dunder_path='__'.join(path),
            included=is_bound,
        )

        for k, v in children:
            yield from rows(v, name=k, path=path + [k])

    from iommi import (
        Column,
        Table,
    )

    class TreeTable(Table):
        class Meta:
            template = Template(
                """
                <style>
                    .full-path {
                        opacity: 0.0;
                    }
                    tr:hover .full-path {
                        opacity: 0.6;
                    }

                    tr {
                        opacity: 0.4;
                    }
                    tr.included {
                        opacity: 1;
                    }

                </style>

                {% include "iommi/table/table.html" %}
            """
            )
            sortable = False
            page_size = None

            @staticmethod
            def row__attrs__class__included(row, **_):
                return row.included

        dunder_path = Column(
            cell__value=lambda row, **_: row.dunder_path,
            cell__format=dunder_path__format,
        )
        path = Column()
        type = Column(
            attr='type_name',
            cell__format=lambda row, **_: (
                format_html(
                    '{prefix}<a href="https://docs.iommi.rocks/en/latest/{type_name}.html{anchor}">{display_name}</a>',
                    prefix=row.prefix,
                    type_name=row.type_name,
                    anchor=f'#{row.shortcut.replace("_", "-")}' if row.shortcut else '',
                    display_name=row.display_name,
                )
                if row.type_name
                else ''
            ),
        )
        included = Column.boolean()

    request = HttpRequest()
    request.method = 'GET'
    request.META = root._request.META
    if hasattr(root._request, 'user'):
        request.user = root._request.user

    return TreeTable(rows=rows(root)).bind(request=request)


def endpoint__debug_templates_used(endpoint, request, **_):
    root = endpoint.iommi_root()
    from iommi.part import render_root
    render_root(part=root)

    def url_for_template(t):
        if isinstance(t, str):
            t = get_template(t).origin.name
        else:
            t = t.origin.name

        return local_debug_url_builder(t, 1)

    links = [
        format_html('<li><a href="{}">{}</a></li>', url_for_template(t), t)
        for t in request.iommi_used_templates
    ]
    links = format_html('{}' * len(links), *links)
    return HttpResponse(format_html('''
        <html>
            <head>
                <style>
                </style>
            </head>
            <body>
                <ul>
                    {}
                </ul>
            </body>
        </html>
        ''', links))


def local_debug_url_builder(filename, lineno):
    if not isabs(filename):
        filename = join(settings.BASE_DIR, filename)
    if hasattr(settings, 'IOMMI_DEBUG_URL_MAPPING'):
        filename = filename.replace(*settings.IOMMI_DEBUG_URL_MAPPING)
    return f"pycharm://open?file={filename}" + ('' if lineno is None else f"&line={lineno:d}")


def src_debug_url_builder(filename, lineno=None):
    debug_url_builder = getattr(settings, 'IOMMI_DEBUG_URL_BUILDER', local_debug_url_builder)
    return debug_url_builder(filename, lineno)


def should_ignore_frame(frame, env_paths):
    assert isinstance(env_paths, set)
    module_name = frame.f_globals.get('__name__')

    if not module_name:
        return False

    if module_name.startswith('iommi.admin'):
        return True

    if module_name.startswith('_pydev_bundle.'):
        return True

    base_module_name = module_name.partition('.')[0]
    if base_module_name in (
        'iommi.declarative',
        'iommi',
        'django',
    ):
        if not module_name.endswith('__tests'):
            return True

    for env_path in env_paths:
        if frame.f_code.co_filename.startswith(env_path):
            return True

    if frame.f_code.co_filename == '<string>':
        return True

    if join('helpers', 'pycharm') in frame.f_code.co_filename:
        return True

    return False


def get_instantiated_at_info(frame):
    import os

    env_paths = {dirname(os.__file__), dirname(dirname(sys.executable))}

    for _ in range(100):
        frame = frame.f_back
        if frame is None:
            break

        if should_ignore_frame(frame, env_paths):
            continue

        return frame.f_code.co_filename, frame.f_lineno
    return None, None


def filename_and_line_num_from_part(part):
    filename, line_num = getattr(part, '_instantiated_at_info', (None, None))
    if (filename, line_num) == (None, None) and isinstance(part, Traversable):
        # inspect.findsource() parses the full AST of the file, so beware the performance implications
        filename = inspect.getsourcefile(part.__class__)
        line_num = inspect.findsource(part.__class__)[1] + 1
        setattr(part, '_instantiated_at_info', (filename, line_num))
    return filename, line_num


def iommi_debug_panel(part):
    source_url = source_url_from_part(part)
    # language=js
    script = r"""
        window.iommi_start_pick = function() {
            window.iommi_pick_stack = [];

            function create(html) {
                let r = document.createElement('div');
                r.innerHTML = html;
                return r.firstChild;
            }

            window.iommi_close_pick_toolbar = function() {
                window.iommi_pick_stack.forEach(function(el) {
                    el[3].style.backgroundColor = el[2];
                });
                document.getElementById('iommi-pick-toolbar').remove()
            };

            function update_toolbar() {
                let toolbar = document.getElementById('iommi-pick-toolbar');
                if (!toolbar) {
                    return;
                }

                while(toolbar.firstChild) {
                    toolbar.removeChild(toolbar.firstChild);
                }

                toolbar.append(create('<div style="float: right" onclick="iommi_close_pick_toolbar()">close</div>'));
                for (let i in window.iommi_pick_stack) {
                    let x = window.iommi_pick_stack[i];
                    toolbar.append(create('<div style="background-color: ' + getColor(i) + '">' + x[0] + ' <a href="https://docs.iommi.rocks/en/latest/' + x[1] + '.html">' + x[1] + '</a></div>'));
                }
            }

            let with_iommi_path = document.querySelectorAll('*[data-iommi-path]');

            let colors = [
                'rgb(255, 255, 191)',
                'rgb(254, 224, 139)',
                'rgb(253, 174,  97)',
                'rgb(244, 109,  67)',
                'rgb(213,  62,  79)',
                'rgb(158,   1,  66)',
                'rgb(230, 245, 152)',
                'rgb(171, 221, 164)',
                'rgb(102, 194, 165)',
                'rgb( 50, 136, 189)',
                'rgb( 94,  79, 162)',
            ];

            function getColor(index) {
                return colors[Math.min(index, colors.length - 1)]
            }

            function mouseenter() {
                window.iommi_pick_stack.push([this.getAttribute('data-iommi-path'), this.getAttribute('data-iommi-type'), this.style.backgroundColor, this])
                this.style.backgroundColor = getColor(window.iommi_pick_stack.length-1);
                update_toolbar();
            }

            function mouseleave() {
                if (window.iommi_pick_stack.length) {
                    this.style.backgroundColor = window.iommi_pick_stack.pop()[2];
                    update_toolbar();
                }
            }
            function click() {
                document.querySelectorAll('*[data-iommi-path]').forEach(function (e) {
                    e.removeEventListener('mouseenter', mouseenter)
                    e.removeEventListener('mouseleave', mouseleave)
                    e.removeEventListener('click', click)
                });
            }

            with_iommi_path.forEach(function (e) {
                e.addEventListener('mouseenter', mouseenter);
                e.addEventListener('mouseleave', mouseleave);
                setTimeout(function(){
                    e.addEventListener('click', click);
                });
            });

            let toolbar = create('<div id="iommi-pick-toolbar" style="position: fixed; left: 0; bottom: 0; width: 100%; background-color: white; color: black; padding: 4px; border-top: 2px solid #1084ff; z-index: 200">');

            document.getElementsByTagName('body')[0].append(toolbar);
        };
    """

    from iommi.menu import get_debug_menu

    return get_debug_menu(sub_menu__code__url=source_url).bind(request=part.get_request()).__html__() + mark_safe(
        f'<script>{script}</script>'
    )


def source_url_from_part(part):
    filename, lineno = filename_and_line_num_from_part(part)
    if filename is not None:
        source_url = src_debug_url_builder(filename, lineno)
    else:
        source_url = None
    return source_url
