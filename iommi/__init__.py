__version__ = '7.11.1'

from functools import wraps

import django
from django.core.exceptions import ImproperlyConfigured

from iommi._db_compat import (
    register_factory,
    setup_db_compat,
)
from iommi.action import Action
from iommi.asset import Asset
from iommi.base import MISSING
from iommi.edit_table import (
    EditColumn,
    EditTable,
)
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
from iommi.sort_after import LAST
from iommi.style import (
    Style,
    register_style,
)
from iommi.table import (
    Column,
    Table,
    register_cell_formatter,
    register_column_factory,
)

setup_db_compat()


def render_if_needed(request, response):
    if isinstance(response, Part):
        return render_part(request, response)
    else:
        return response


def render_part(request, part: Part):
    try:
        if not part._is_bound:
            part = part.bind(request=request)
        return part.render_to_response()
    except Exception as e:
        filename, lineno = part._instantiated_at_info
        if filename is None:
            raise

        from iommi.synthetic_traceback import SyntheticException

        fake = SyntheticException(
            tb=[dict(filename=filename, f_lineno=lineno, function='<iommi declaration>', f_globals={}, f_locals={})]
        )

        raise e from fake


# noinspection PyPep8Naming
class middleware:
    def __init__(self, get_response):
        from django.db import connections

        self.get_response = get_response
        self.atomic_db_aliases = {db.alias for db in connections.all() if db.settings_dict['ATOMIC_REQUESTS']}

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.iommi_not_atomic_for = getattr(view_func, '_non_atomic_requests', set())

    def __call__(self, request):
        response = self.get_response(request)

        if isinstance(response, Part):
            from django.db import transaction

            render = render_part
            for alias in self.atomic_db_aliases:
                if alias not in request.iommi_not_atomic_for:
                    render = transaction.atomic(using=alias)(render)
            return render(request, response)

        return response


def iommi_render(view):
    @wraps(view)
    def inner(request, *args, **kwargs):
        result = view(request, *args, **kwargs)
        return render_if_needed(request, result)

    return inner


__all__ = [
    'Action',
    'Asset',
    'Column',
    'EditTable',
    'EditColumn',
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
    'iommi_render',
]

if django.VERSION[:2] < (3, 2):
    default_app_config = 'iommi.apps.IommiConfig'


try:
    from django.conf import settings

    if 'iommi' not in settings.INSTALLED_APPS:
        raise Exception("You must add 'iommi' to INSTALLED_APPS")
except ImproperlyConfigured:
    pass
