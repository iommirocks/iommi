import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# These overly specific paths are for jinja2
TEMPLATE_DIRS = [
    os.path.join(BASE_DIR, 'tests'),
    os.path.join(BASE_DIR, 'tests/templates'),
    os.path.join(BASE_DIR, 'iommi/templates'),
    os.path.join(BASE_DIR, 'docs/templates'),
]

TEMPLATE_DEBUG = True


class HighlightBrokenVariable:
    def __contains__(self, item):
        return True

    def __mod__(self, other):
        assert False, f'Tried to render non-existent variable {other}'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATE_DIRS,
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': TEMPLATE_DEBUG,
            'string_if_invalid': HighlightBrokenVariable(),
            'context_processors': [
                'tests.context_processors.context_processor_is_called',
            ],
        },
    },
]

SECRET_KEY = "foobar"

ROOT_URLCONF = 'tests.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

USE_TZ = False

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
]

IOMMI_DEFAULT_STYLE = 'test'

MIDDLEWARE = [
    'iommi.live_edit.Middleware',
    'iommi.sql_trace.Middleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'iommi.middleware',
    'iommi.profiling.Middleware',
]


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'iommi',
    'tests',
    'docs',
]


DATETIME_FORMAT = r'\d\a\t\e\t\i\m\e\: N j, Y, P'
DATE_FORMAT = r'\d\a\t\e\: N j, Y'
TIME_FORMAT = r'\t\i\m\e\: P'

USE_L10N = False
