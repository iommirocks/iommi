try:
    from django.utils.safestring import SafeText
    from django.test import RequestFactory

except ImportError:
    from jinja2 import Markup as SafeText  # noqa
    from .compat_flask import Jinja2RequestFactory as RequestFactory
