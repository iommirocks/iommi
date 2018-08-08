#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
from setuptools import setup, find_packages, Command
from io import open

readme = open('README.rst', encoding='utf8').read()
history = open('HISTORY.rst', encoding='utf8').read().replace('.. :changelog:', '')


def read_reqs(name):
    with open(os.path.join(os.path.dirname(__file__), name), encoding='utf8') as f:
        return [line for line in f.read().split('\n') if line and not line.strip().startswith('#')]


def read_version():
    with open(os.path.join('lib', 'tri/table', '__init__.py'), encoding='utf8') as f:
        m = re.search(r'''__version__\s*=\s*['"]([^'"]*)['"]''', f.read())
        if m:
            return m.group(1)
        raise ValueError("couldn't find version")


class Tag(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from subprocess import call
        version = read_version()
        errno = call(['git', 'tag', '--annotate', version, '--message', 'Version %s' % version])
        if errno == 0:
            print("Added tag for version %s" % version)
        raise SystemExit(errno)


class ReleaseCheck(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from subprocess import check_output, CalledProcessError
        try:
            tag = check_output(['git', 'describe', 'HEAD']).strip().decode('utf8')
        except CalledProcessError:
            tag = ''
        version = read_version()
        if tag != version:
            print('Missing %s tag on release' % version)
            raise SystemExit(1)

        current_branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip().decode('utf8')
        if current_branch != 'master':
            print('Only release from master')
            raise SystemExit(1)

        print("Ok to distribute files")


# NB: _don't_ add namespace_packages to setup(), it'll break
#     everything using imp.find_module
setup(
    name='tri.table',
    version=read_version(),
    description='tri.table is a library to make full featured HTML tables easily',
    long_description=readme + '\n\n' + history,
    author='Anders Hovmöller',
    author_email='anders.hovmoller@trioptima.com',
    url='https://github.com/TriOptima/tri.table',
    packages=find_packages('lib'),
    package_dir={'': 'lib'},
    include_package_data=True,
    install_requires=['Django >= 1.8'] + read_reqs('requirements.txt'),
    license="BSD",
    zip_safe=False,
    keywords='tri.table',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    cmdclass={'tag': Tag,
              'release_check': ReleaseCheck},
)
