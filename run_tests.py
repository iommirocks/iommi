#!/usr/bin/env python3
"""
Run tests using uv.

Examples:
  python run_tests.py                          # latest Python + Django
  python run_tests.py --python=3.11            # latest Django, specific Python
  python run_tests.py --python=3.12 --django=4.2 --jinja2
  python run_tests.py --all                    # full matrix
"""
import argparse
import os
import subprocess
import sys

MATRIX = [
    ('3.11', '3.2'),
    ('3.11', '4.0'),
    ('3.11', '4.1'),
    ('3.11', '4.2'),
    ('3.11', '5.0'),
    ('3.11', '5.2'),
    ('3.12', '3.2'),
    ('3.12', '4.0'),
    ('3.12', '4.1'),
    ('3.12', '4.2'),
    ('3.12', '5.0'),
    ('3.12', '5.2'),
    ('3.12', '6.0'),
    ('3.13', '4.1'),
    ('3.13', '4.2'),
    ('3.13', '5.0'),
    ('3.13', '5.2'),
    ('3.13', '6.0'),
    ('3.14', '6.0'),
]

LATEST_PYTHON = '3.14'
LATEST_DJANGO = '6.0'

DJANGO_CONSTRAINTS = {
    '3.2': 'Django>=3.2,<3.3',
    '4.0': 'Django>=4.0,<4.1',
    '4.1': 'Django>=4.1,<4.2',
    '4.2': 'Django>=4.2,<4.3',
    '5.0': 'Django>=5.0,<5.1',
    '5.2': 'Django>=5.2,<5.3',
    '6.0': 'Django>=6.0,<6.1',
}


def run(python_version, django_version, jinja2=False):
    cmd = [
        'uv', 'run',
        '-p', python_version,
        '--with', DJANGO_CONSTRAINTS[django_version],
        '--isolated',
    ]
    env_override = {}
    if jinja2:
        cmd += ['--with', 'jinja2']
        env_override['DJANGO_SETTINGS_MODULE'] = 'tests.settings_jinja2_only'

    cmd.append('pytest')

    return subprocess.run(cmd, env={**os.environ, **env_override}).returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run iommi tests via uv')
    parser.add_argument('--python', default=LATEST_PYTHON, metavar='VERSION')
    parser.add_argument('--django', default=LATEST_DJANGO, metavar='VERSION')
    parser.add_argument('--jinja2', action='store_true')
    parser.add_argument('--all', dest='all', action='store_true', help='Run the full test matrix')
    args = parser.parse_args()

    if args.all:
        failed = []
        for python_version, django_version in MATRIX:
            print(f'\n=== Python {python_version} | Django {django_version} ===', flush=True)
            if run(python_version, django_version) != 0:
                failed.append(f'Python {python_version} | Django {django_version}')

        print('\n=== Python 3.12 | Django 4.2 | jinja2 ===', flush=True)
        if run('3.12', '4.2', jinja2=True) != 0:
            failed.append('Python 3.12 | Django 4.2 | jinja2')

        if failed:
            print('\nFailed combinations:')
            for combo in failed:
                print(f'  {combo}')
            sys.exit(1)

        print('\nAll combinations passed!')
    else:
        sys.exit(run(args.python, args.django, jinja2=args.jinja2))
