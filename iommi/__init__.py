__version__ = '6.2.0'

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
        try:
            if not response._is_bound:
                response = response.bind(request=request)
            return response.render_to_response()
        except Exception as e:
            filename, lineno = response._instantiated_at_info
            from iommi.synthetic_traceback import SyntheticException

            fake = SyntheticException(
                tb=[dict(filename=filename, f_lineno=lineno, function='<iommi declaration>', f_globals={}, f_locals={})]
            )

            raise e from fake
    else:
        return response


class middleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.non_atomic_requests = set()

    def process_view(self, request, view_func, view_args, view_kwargs):
        self.non_atomic_requests = getattr(view_func, '_non_atomic_requests', set())

    def __call__(self, request):
        response = self.get_response(request)

        if isinstance(response, Part):
            from django.db import connections, transaction

            render = render_if_needed
            for db in connections.all():
                if db.settings_dict['ATOMIC_REQUESTS'] and db.alias not in self.non_atomic_requests:
                    render = transaction.atomic(using=db.alias)(render)
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
except ImproperlyConfigured:
    pass
else:
    if 'iommi' not in settings.INSTALLED_APPS:
        raise Exception("You must add 'iommi' to INSTALLED_APPS")
