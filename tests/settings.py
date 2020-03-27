import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# These overly specific paths are for jinja2
TEMPLATE_DIRS = [
    os.path.join(BASE_DIR, 'tests'),
    os.path.join(BASE_DIR, 'tests/templates'),
    os.path.join(BASE_DIR, 'iommi/templates'),
]

TEMPLATE_DEBUG = True


class HighlightBrokenVariable:
    def __contains__(self, item):
        return True

    def __mod__(self, other):
        raise Exception(f'Tried to render non-existent variable {other}')


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATE_DIRS,
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': TEMPLATE_DEBUG,
            'string_if_invalid': HighlightBrokenVariable(),
        }
    },
]

SECRET_KEY = "foobar"
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'iommi',
    'tests',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

IOMMI_DEFAULT_STYLE = 'test'
