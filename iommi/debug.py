from os.path import (
    isabs,
    join,
)

from django.conf import settings
from tri_struct import Struct

from iommi._web_compat import (
    format_html,
    HttpRequest,
    Template,
    mark_safe,
)
from iommi.member import Members
from iommi.traversable import (
    bound_members,
    declared_members,
    PathNotFoundException,
    Traversable,
)


def iommi_debug_on():
    return getattr(settings, 'IOMMI_DEBUG', settings.DEBUG)


def endpoint__debug_tree(endpoint, **_):
    root = endpoint._parent._parent
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
        base_type_name = type_name
        if isinstance(node, Members) and node._declared_members:
            if name == 'parts':
                member_type = 'Part'
            else:
                member_type = type(list(declared_members(node).values())[0]).__name__
            type_name = f'Members[{member_type}]'

        yield Struct(
            name=name,
            obj=node,
            type=type_name,
            base_type=base_type_name,
            path=p,
            dunder_path='__'.join(path),
            included=is_bound
        )

        if isinstance(node, dict):
            children = list(node.items())
        elif isinstance(node, Traversable):
            children = [
                (
                    k,
                    bound_members(node).get(k, v)
                )
                for k, v in declared_members(node).items()
            ]
        else:
            return

        for k, v in children:
            yield from rows(v, name=k, path=path + [k])

    from iommi import (
        Column,
        Table,
    )

    def dunder_path__format(row, **_):
        if row.dunder_path is None:
            return ''
        prefix = row.dunder_path.rpartition('__')[0]
        return format_html(
            '<span class="full-path">{prefix}{separator}</span>{name}',
            prefix=prefix,
            separator='__' if prefix else '',
            name=row.name
        )

    class TreeTable(Table):
        class Meta:
            template = Template("""
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
            """)
            sortable = False
            row__attrs__class__included = (lambda row, **_: row.included)
            page_size = None

        dunder_path = Column(
            cell__value=lambda row, **_: row.dunder_path,
            cell__format=dunder_path__format,
        )
        path = Column()
        type = Column(
            cell__url=lambda row, **_: f'https://docs.iommi.rocks/en/latest/{row.base_type}.html' if row.base_type else None
        )
        included = Column.boolean()

    request = HttpRequest()
    request.method = 'GET'
    if hasattr(root._request, 'user'):
        request.user = root._request.user

    return TreeTable(rows=rows(root)).bind(request=request)


def local_debug_url_builder(filename, lineno):
    if not isabs(filename):
        filename = join(settings.BASE_DIR, filename)
    if hasattr(settings, 'DEBUG_URL_MAPPING'):
        filename = filename.replace(*settings.DEBUG_URL_MAPPING)
    return "pycharm://open?file=%s" % (filename,) + ('' if lineno is None else "&line=%d" % (lineno,))


def src_debug_url_builder(filename, lineno=None):
    debug_url_builder = getattr(settings, 'IOMMI_DEBUG_URL_BUILDER', local_debug_url_builder)
    return debug_url_builder(filename, lineno)


def iommi_debug_panel(part):
    frame = part._instantiated_at_frame
    filename = None
    lineno = None
    for _ in range(100):
        frame = frame.f_back
        if frame is None:
            break
        module_name = frame.f_globals.get('__name__')

        if not module_name.startswith('iommi.admin'):
            if module_name in ('tri_declarative', 'iommi', ) or module_name.startswith('iommi.') or module_name.startswith('django.'):
                continue
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        break

    if filename is None or filename.endswith('urls.py'):
        import inspect
        if not inspect.getmodule(type(part)).__name__.startswith('iommi.'):
            filename = inspect.getsourcefile(type(part))
            lineno = inspect.getsourcelines(type(part))[-1]

    if filename is None:
        return ''

    source_url = src_debug_url_builder(filename, lineno)
    if not source_url:
        return ''
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


    from iommi.menu import DebugMenu
    return DebugMenu(sub_menu__code__url=source_url).bind(request=part.get_request()).__html__() + mark_safe(f'<script>{script}</script>')
