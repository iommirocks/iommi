import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = "foobar"
INSTALLED_APPS = [
    'tri.tables',
    'tests'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
