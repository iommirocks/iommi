__version__ = '0.2.0'

from tri_declarative import LAST
from iommi._db_compat import (
    setup_db_compat,
    register_factory,
)
from iommi.action import Action
from iommi.base import (
    MISSING,
    Part,
)
from iommi.form import (
    Field,
    Form,
    register_field_factory,
)
from iommi.page import (
    Fragment,
    html,
    Page,
)
from iommi.query import (
    Query,
    Variable,
    register_variable_factory,
)
from iommi.table import (
    Column,
    Table,
    register_column_factory,
    register_cell_formatter,
)
from iommi.menu import (
    Menu,
    MenuItem,
)
from iommi.style import register_style
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
    'MISSING',
    'Page',
    'Part',
    'Query',
    'Table',
    'Variable',
    'LAST',
    'register_factory',
    'register_field_factory',
    'register_variable_factory',
    'register_column_factory',
    'register_cell_formatter',
    'register_style',
]

default_app_config = 'iommi.django_app.IommiConfig'
