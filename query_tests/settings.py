import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

TEMPLATE_DEBUG = True

SECRET_KEY = "foobar"
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'tests'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

MIDDLEWARE_CLASSES = []
