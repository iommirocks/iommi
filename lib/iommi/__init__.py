__version__ = '0.1.1'

from iommi._db_compat import (
    setup_db_compat,
    register_factory,
)
from iommi.action import Action
from iommi.base import (
    MISSING,
    PagePart,
)
from iommi.form import (
    Field,
    Form,
    register_field_factory,
)
from iommi.page import (
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
from iommi.style import register_style
setup_db_compat()


def middleware(get_response):
    def iommi_middleware(request):

        response = get_response(request)
        if isinstance(response, PagePart):
            return response.bind(request=request).render_to_response()
        else:
            return response

    return iommi_middleware


# TODO: make sure we have documentation for all this public API!
__all__ = [
    'Action',
    'Column',
    'Field',
    'Form',
    'html',
    'middleware',
    'MISSING',
    'Page',
    'PagePart',
    'Query',
    'Table',
    'Variable',
    'register_factory',
    'register_field_factory',
    'register_variable_factory',
    'register_column_factory',
    'register_cell_formatter',
    'register_style',
]

default_app_config = 'iommi.django_app.IommiConfig'
