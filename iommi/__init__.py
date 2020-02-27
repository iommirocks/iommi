__version__ = '0.3.0'

from tri_declarative import LAST

from iommi._db_compat import (
    register_factory,
    setup_db_compat,
)
from iommi.action import Action
from iommi.base import MISSING
from iommi.form import (
    Field,
    Form,
    register_field_factory,
)
from iommi.menu import (
    Menu,
    MenuItem,
)
from iommi.page import (
    Fragment,
    html,
    Page,
)
from iommi.part import Part
from iommi.query import (
    Query,
    register_filter_factory,
    Filter,
)
from iommi.style import register_style
from iommi.table import (
    Column,
    register_cell_formatter,
    register_column_factory,
    Table,
)

setup_db_compat()


def middleware(get_response):
    def iommi_middleware(request):

        response = get_response(request)
        if isinstance(response, Part):
            return response.bind(request=request).render_to_response()
        else:
            return response

    return iommi_middleware


__all__ = [
    'Action',
    'Column',
    'Field',
    'Form',
    'Fragment',
    'html',
    'Menu',
    'MenuItem',
    'middleware',
    'Page',
    'Query',
    'Table',
    'Filter',
    'LAST',
    'register_factory',
    'register_field_factory',
    'register_filter_factory',
    'register_column_factory',
    'register_cell_formatter',
    'register_style',
]

default_app_config = 'iommi.django_app.IommiConfig'
