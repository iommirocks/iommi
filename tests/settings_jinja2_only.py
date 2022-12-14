from .settings import *  # noqa: F403

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': TEMPLATE_DIRS,  # noqa: F405
        'APP_DIRS': True,
    },
]
