import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

TEMPLATE_DIRS = [
    os.path.join(BASE_DIR, 'tests'),
    os.path.join(BASE_DIR, 'iommi/form/templates'),
    os.path.join(BASE_DIR, 'iommi/query/templates'),
    os.path.join(BASE_DIR, 'iommi/django/templates'),
]

TEMPLATE_DEBUG = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATE_DIRS,
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': TEMPLATE_DEBUG,
        }
    }
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


class HighlightBrokenVariable:
    def __contains__(self, item):
        return True

    def __mod__(self, other):
        raise Exception(f'Tried to render non-existent variable {other}')


TEMPLATES[0]['OPTIONS']['string_if_invalid'] = HighlightBrokenVariable()
