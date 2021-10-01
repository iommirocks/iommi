__version__ = '3.2.2'

from tri_declarative import LAST

from iommi._db_compat import (
    register_factory,
    setup_db_compat,
)
from iommi.action import Action
from iommi.asset import Asset
from iommi.base import MISSING
from iommi.form import (
    Field,
    Form,
    register_field_factory,
)
from iommi.fragment import (
    Fragment,
    Header,
    html,
)
from iommi.from_model import (
    register_search_fields,
)
from iommi.menu import (
    Menu,
    MenuItem,
)
from iommi.page import (
    Page,
)
from iommi.part import Part
from iommi.query import (
    Filter,
    Query,
    register_filter_factory,
)
from iommi.style import (
    register_style,
    Style,
)
from iommi.table import (
    Column,
    register_cell_formatter,
    register_column_factory,
    Table,
)

setup_db_compat()


def render_if_needed(request, response):
    if isinstance(response, Part):
        if not response._is_bound:
            response = response.bind(request=request)
        return response.render_to_response()
    else:
        return response


def middleware(get_response):
    def iommi_middleware(request):
        return render_if_needed(request, get_response(request))

    return iommi_middleware


__all__ = [
    'Action',
    'Asset',
    'Column',
    'Field',
    'Fragment',
    'Form',
    'Fragment',
    'Header',
    'Menu',
    'MenuItem',
    'middleware',
    'Page',
    'Part',
    'Query',
    'Table',
    'Filter',
    'LAST',
    'MISSING',
    'register_factory',
    'register_field_factory',
    'register_filter_factory',
    'register_column_factory',
    'register_cell_formatter',
    'register_style',
    'register_search_fields',
    'Style',
    'html',
]

default_app_config = 'iommi.apps.IommiConfig'
