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
from itertools import product
from pathlib import Path

import yaml


def _load_matrix():
    workflow_path = Path(__file__).parent / '.github' / 'workflows' / 'tests.yml'
    with open(workflow_path) as f:
        config = yaml.safe_load(f)

    matrix = config['jobs']['build']['strategy']['matrix']
    python_versions = matrix['python-version']
    django_versions = matrix['django-version']
    excludes = matrix.get('exclude', [])

    exclude_set = {
        (e['python-version'], e['django-version'])
        for e in excludes
    }

    combos = [
        (py, dj)
        for py, dj in product(python_versions, django_versions)
        if (py, dj) not in exclude_set
    ]

    return combos, python_versions[-1], django_versions[-1]


MATRIX, LATEST_PYTHON, LATEST_DJANGO = _load_matrix()

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
        '--with', 'pytest==8.1.1',
        '--with', 'pytest-django==4.8.0',
        '--with', 'pytest-xdist==3.8.0',
        '--isolated',
    ]
    env_override = {}
    if jinja2:
        cmd += ['--with', 'jinja2']
        env_override['DJANGO_SETTINGS_MODULE'] = 'tests.settings_jinja2_only'

    cmd.extend([
        'pytest',
        '-n', 'auto',
    ])

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
            status = run(python_version, django_version)
            if status != 0:
                failed.append(f'Python {python_version} | Django {django_version}')

        if failed:
            print('\nFailed combinations:')
            for combo in failed:
                print(f'  {combo}')
            sys.exit(1)

        print('\nAll combinations passed!')
    else:
        status = run(args.python, args.django, jinja2=args.jinja2)
        sys.exit(status)
