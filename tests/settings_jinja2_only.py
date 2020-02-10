from .settings import *

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': TEMPLATE_DIRS,
        'APP_DIRS': True,
    },
]
