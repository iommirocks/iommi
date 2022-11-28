import re
from glob import glob
from io import StringIO
from pathlib import Path
from textwrap import dedent
from typing import get_type_hints

from iommi import (
    MISSING,
    Part,
)
from iommi.base import items
from iommi.declarative import get_declared
from iommi.declarative.namespace import (
    flatten,
    Namespace,
)
from iommi.shortcut import (
    get_shortcuts_by_name,
    is_shortcut,
)


def read_cookbook_links():
    result = []
    for filename in glob(str(Path(__file__).parent.parent / 'docs' / 'cookbook_*.rst')):
        with open(filename) as f:
            result.append((parse_cookbook_links(f.readlines()), Path(filename).stem))
    return result


def parse_cookbook_links(lines):
    link_marker = '.. _'
    anchors = [line.strip()[len(link_marker) :].rstrip(':') for line in lines if line.startswith(link_marker)]

    # TODO: validate that we only have anchors once

    return {x for x in anchors if not x.endswith('?')}


def validate_cookbook_links(cookbook_links):
    class_by_name = {x.__name__: x for x in get_default_classes()}

    for link, name in cookbook_links:
        if '.' in link:
            class_name, _, refinable_name = link.partition('.')
            assert class_name in class_by_name, f'{class_name} was not found in default_classes'
            getattr(class_by_name[class_name], refinable_name)


def get_default_classes():
    import iommi

    return [
        iommi.Table,
        iommi.Column,
        iommi.EditTable,
        iommi.EditColumn,
        iommi.Query,
        iommi.Filter,
        iommi.Form,
        iommi.fragment.Fragment,
        iommi.Field,
        iommi.Action,
        iommi.Page,
        iommi.Menu,
        iommi.MenuItem,
        iommi.Style,
        iommi.fragment.Header,
        iommi.Asset,
        # Private-ish APIs
        iommi.endpoint.Endpoint,
        iommi.part.Part,
        iommi.traversable.Traversable,
        iommi.member.Members,
        iommi.table.Cell,
        iommi.table.ColumnHeader,
        iommi.table.HeaderConfig,
        iommi.attrs.Attrs,
        iommi.table.ColumnHeader,
        iommi.fragment.Container,
    ]


def generate_api_docs_tests(directory, classes=None):  # pragma: no cover - this is tested by rtd anyway
    """
    Generate test files for declarative APIs

    :param directory: directory to write the .py files into
    :param classes: list of classes to generate tests for
    """
    print(f'generate_api_docs_tests("{directory}")')
    if classes is None:
        classes = get_default_classes()

    doc_by_filename = _generate_tests_from_class_docs(classes=classes)  # pragma: no mutate
    for filename, doc in doc_by_filename:  # pragma: no mutate
        # Avoid rewriting the files! If we do then pytest will redo the assertion rewriting which is very slow.
        try:
            with open(directory / filename) as f2:
                old_contents = f2.read()
            if old_contents == doc:
                continue
        except FileNotFoundError:
            pass
        with open(directory / filename, 'w') as f2:  # pragma: no mutate
            f2.write(doc)  # pragma: no mutate


def get_docs_callable_description(c):
    if getattr(c, '__name__', None) == '<lambda>':
        import inspect

        return inspect.getsource(c).strip()
    return c.__module__ + '.' + c.__name__


def get_methods_by_type_by_name(class_):
    function_type = type(get_methods_by_type_by_name)
    ignore_list = ['get_declared', 'set_declared', 'get_meta']

    r = {
        k: v
        for k, v in class_.__dict__.items()
        if not k.startswith('_') and k not in ignore_list and not is_shortcut(getattr(class_, k))
    }

    return {
        'Methods': {
            k: v
            for k, v in r.items()
            if isinstance(v, function_type)
        },
        'Static methods': {
            k: v
            for k, v in r.items()
            if isinstance(v, staticmethod)
        },
        'Class methods': {
            k: v
            for k, v in r.items()
            if isinstance(v, classmethod)
        },
    }


def docstring_param_dict(obj):
    doc = obj.__doc__
    if doc is None:
        return dict(text=None, params={})
    doc = dedent(doc)
    return dict(
        text=doc[: doc.find(':param')].strip() if ':param' in doc else doc.strip(),
        params=dict(re.findall(r":param (?P<name>\w+): (?P<text>.*)", doc)),
    )


def indent(levels, s):
    return (' ' * levels * 4) + s


def get_namespace(c):
    return Namespace(
        {
            k: getattr(c.__init__, '__iommi_with_defaults_kwargs', {}).get(k)
            for k, v in items(get_declared(c, 'refinable'))
        }
    )


def get_cookbook_name_by_refinable_name():
    cookbook_links = read_cookbook_links()
    validate_cookbook_links(cookbook_links)
    # TODO: validate that all cookbook links are actually linked somewhere. For example ".. _Column.cells_for_rows" isn't right now.
    cookbook_name_by_refinable_name = {}
    for links, name in cookbook_links:
        for link in links:
            cookbook_name_by_refinable_name[link] = name
    return cookbook_name_by_refinable_name


def _generate_tests_from_class_docs(classes):
    cookbook_name_by_refinable_name = get_cookbook_name_by_refinable_name()

    for c in classes:
        from io import StringIO

        f = StringIO()

        yield _generate_tests_from_class_doc(f, c, classes, cookbook_name_by_refinable_name)


def _generate_tests_from_class_doc(f, c, classes, cookbook_name_by_refinable_name):
    def w(levels, s):
        f.write(indent(levels, s))
        f.write('\n')

    def section(level, title, indent=0):
        underline = {0: '=', 1: '-', 2: '^', 3: '+'}[level] * len(title)
        w(indent, title)
        w(indent, underline)
        w(indent, '')

    w(
        0,
        '''
# NOTE: this file is automatically generated

from iommi import *
from iommi.admin import Admin
from django.urls import (
    include,
    path,
)
from django.db import models
from tests.helpers import req, user_req, staff_req, show_output
from docs.models import *
request = req('get')


# language=rst
"""
    ''',
    )

    section(0, c.__name__, indent=0)

    class_doc = docstring_param_dict(c)
    constructor_doc = docstring_param_dict(c.__init__)

    if c.__base__ in classes:
        w(0, f'Base class: :doc:`{c.__base__.__name__}`')
    else:
        w(0, f'Base class: `{c.__base__.__name__}`')

    w(0, '')

    w(0, '"""')
    w(0, 'def test_base():')
    w(1, '# language=rst')
    w(1, '"""')

    if class_doc['text']:
        _print_rst_or_python(class_doc['text'], w)

    w(1, '"""')
    w(0, '')
    w(1, '# language=rst')
    w(1, '"""')

    if constructor_doc['text']:
        if class_doc['text']:
            w(0, '')

        f.write(constructor_doc['text'])
        w(0, '')

    w(0, '')

    defaults = Namespace()
    for refinable, value in sorted(get_namespace(c).items()):
        if value not in (None, MISSING):
            defaults[refinable] = value

    def default_description(v):
        if callable(v) and not isinstance(v, Namespace):
            v = get_docs_callable_description(v)

            if 'lambda' in v:
                v = v[v.find('lambda'):]
                v = v.strip().strip(',').replace('\n', ' ').replace('  ', ' ')
        if isinstance(v, Part):
            v = v.bind()
        if v == '':
            v = '""'
        return v

    refinable_members = sorted(dict.items(get_namespace(c)))
    if refinable_members:
        section(1, 'Refinable members')
        type_hints = get_type_hints(c)
        for refinable, value in refinable_members:
            w(0, '')
            w(0, '* `' + refinable + '`')

            if constructor_doc['params'].get(refinable):
                w(1, constructor_doc['params'][refinable])
                w(0, '')
            type_hint = type_hints.get(refinable)
            if type_hint:
                name = str(type_hint)
                if name.startswith('typing.'):
                    name = name.replace('typing.', '')
                else:
                    name = type_hint.__name__

                if type_hint in classes:
                    w(1, f'Type: :doc:`{name}`')
                else:
                    w(1, f'Type: `{name}`')
                w(0, '')

            if refinable in defaults:
                w(1, f'Default: `{default_description(defaults.pop(refinable))}`')

            ref_name = f'{c.__name__}.{refinable}'
            if ref_name in cookbook_name_by_refinable_name:
                w(0, '')
                w(1, f'Cookbook: :ref:`{ref_name.lower()}`')
                w(0, '')

        w(0, '')

    assert not defaults

    shortcuts = get_shortcuts_by_name(c)
    if shortcuts:
        section(1, 'Shortcuts')

        for name, shortcut in sorted(shortcuts.items()):
            section(2, f'`{name}`')

            if shortcut.__doc__:
                foo = docstring_param_dict(shortcut)
                f.write(foo['text'])
                w(0, '')

                if foo['params']:
                    w(0, '')
                    section(3, 'Parameters')
                    for k, v in foo['params'].items():
                        w(0, f'* `{k}`')
                        w(1, f'* `{v}`')

                w(0, '')

            defaults = (
                shortcut if isinstance(shortcut, dict) else getattr(shortcut, '__iommi_with_defaults_kwargs', {})
            )
            if defaults:
                defaults = Namespace(defaults)
                section(3, 'Defaults')
                for k, v in items(flatten(defaults)):
                    v = default_description(v)
                    w(0, f'* `{k}`')
                    w(1, f'* `{v}`')
                w(0, '')

    for k, v in get_methods_by_type_by_name(c).items():
        methods = v
        if methods:
            section(1, k)

            for name, method in sorted(methods.items()):
                section(2, f'`{name}`')

                doc = getattr(c, name).__doc__
                if doc:
                    w(0, '')
                    _print_rst_or_python(doc, w)
                    w(0, '')

    w(1, '''"""''')
    return 'test_doc__api_%s.py' % c.__name__, f.getvalue()


def _print_rst_or_python(doc, w):
    in_code_block = False
    code_block_indent = None
    for line in dedent(doc).split('\n'):
        assert '\n' not in line
        if line.strip().startswith('.. code-block:: python'):
            w(1, '"""')

            in_code_block = True
        elif in_code_block:
            if code_block_indent is None:
                if line.strip():
                    code_block_indent = len(line) - len(line.lstrip(' '))
                w(0, line)
            else:
                if line.startswith(' ' * code_block_indent) or not line.strip():
                    w(0, line)
                else:
                    in_code_block = False
                    w(1, '# language=rst')
                    w(1, '"""')
                    w(1, line)
        else:
            w(0, line)
    if in_code_block:
        w(1, '# language=rst')
        w(1, '"""')
    w(0, '')
