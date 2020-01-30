__version__ = '0.1.0'

from iommi._db_compat import setup_db_compat
from iommi.action import Action
from iommi.base import (
    MISSING,
    PagePart,
)
from iommi.form import (
    Field,
    Form,
)
from iommi.page import (
    html,
    Page,
)
from iommi.query import (
    Query,
    Variable,
)
from iommi.table import (
    Column,
    Table,
)
setup_db_compat()


def middleware(get_response):
    def iommi_middleware(request):

        response = get_response(request)
        if isinstance(response, PagePart):
            return response.bind(request=request).render_to_response()
        else:
            return response

    return iommi_middleware


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
]
