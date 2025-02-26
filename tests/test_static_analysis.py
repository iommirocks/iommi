import re
from os import walk
from pathlib import Path

from django.conf import settings
from iommi.sql_trace import format_clickable_filename


def check_line_import_datetime(line, **_):
    if line.startswith('import datetime'):
        return 'Importing datetime as a module is not allowed. Please use `from datetime import ...` to import the symbol you need.'


def check_line_datetime_now(line, **_):
    if 'datetime.now()' in line:
        return "Don't use `datetime.now()`, you should use `django.timezone.now`"
    if 'datetime.utcnow()' in line:
        return "Don't use `datetime.utcnow()`, you should use `django.timezone.now`"


def check_only_use_gettext_lazy(line, **_):
    if re.match(r'.*\bgettext\b.*', line):
        return 'Always use gettext_lazy, never gettext. Using gettext can cause issues in a multi-language app situation.'


def test_static_analysis():

    checks = [
        v
        for k, v in globals().items()
        if k.startswith('check_line_')
    ]

    errors = []

    for root, dirs, files in walk(settings.BASE_DIR):
        dirs[:] = [
            x for x in dirs
            if not x.startswith('.') and x not in ['venv', 'node_modules', 'migrations', 'mutants', 'build']
        ]

        for filename in files:
            if not filename.endswith('.py'):
                continue

            if filename in ['build_test_branch.py']:
                continue

            full_path = str(Path(root, filename))

            if full_path == __file__:
                continue

            with open(full_path) as f:
                for i, line in enumerate(f.readlines(), start=1):
                    for check in checks:
                        message = check(line)
                        if message:
                            errors.append((full_path, i, line, message))

    if errors:
        print()

        for filename, i, line, message in errors:
            print(message)
            print(format_clickable_filename(filename, i, None))

        assert False
