from os.path import (
    isabs,
    join,
)

from django.conf import settings
from django.http import HttpRequest
from django.utils.html import format_html
from tri_struct import Struct

from iommi._web_compat import Template
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

    def dunder_path__value(row, **_):
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

        dunder_path = Column(
            cell__value=dunder_path__value,
        )
        path = Column()
        type = Column(
            cell__url=lambda row, **_: f'https://docs.iommi.rocks/en/latest/{row.base_type}.html' if row.base_type else None
        )
        included = Column.boolean()

    request = HttpRequest()
    request.method = 'GET'

    return TreeTable(rows=rows(root)).bind(request=request).render_to_response()


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
    source_url = None
    for _ in range(100):
        frame = frame.f_back
        module_name = frame.f_globals.get('__name__')
        if frame is None:
            break

        if module_name in ('tri_declarative', 'iommi', ) or module_name.startswith('iommi.'):
            continue
        source_url = src_debug_url_builder(frame.f_code.co_filename, frame.f_lineno)
        break

    if not source_url:
        return ''

    from iommi.menu import DebugMenu
    return DebugMenu(sub_menu__code__url=source_url).bind(request=part.get_request()).__html__()
