try:
    from django.test import RequestFactory
    from django.utils.safestring import SafeText

except ImportError:
    from jinja2 import Markup as SafeText  # noqa: F401

    from .compat_flask import Jinja2RequestFactory as RequestFactory  # noqa: F401
