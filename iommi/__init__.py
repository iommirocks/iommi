__version__ = '0.6.2'

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
    Header,
    html,
    Page,
)
from iommi.part import Part
from iommi.query import (
    Filter,
    Query,
    register_filter_factory,
)
from iommi.style import register_style
from iommi.table import (
    Column,
    register_cell_formatter,
    register_column_factory,
    Table,
)
from iommi.from_model import (
    register_name_field,
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
    'Header',
    'html',
    'Menu',
    'MenuItem',
    'middleware',
    'Page',
    'Part',
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
    'register_name_field',
]

default_app_config = 'iommi.django_app.IommiConfig'
