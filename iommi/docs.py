import inspect
import re
from collections import defaultdict
from glob import glob
from os.path import join
from pathlib import Path
from textwrap import (
    dedent,
    indent,
)
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
from iommi.refinable import (
    EvaluatedRefinable,
    is_refinable_function,
    SpecialEvaluatedRefinable,
)
from iommi.shortcut import (
    get_shortcuts_by_name,
    is_shortcut,
)
from iommi.struct import merged
from iommi.struct import Struct  # noqa: E402
from tests.helpers import create_iframe  # noqa: E402


def uses_from_cookbooks():
    import docutils.parsers.rst
    import docutils.utils
    import docutils.frontend
    from docutils.nodes import comment, title, target, section
    from iommi.declarative.util import strip_prefix

    parser = docutils.parsers.rst.Parser()
    components = (docutils.parsers.rst.Parser,)
    settings = docutils.frontend.OptionParser(components=components).get_default_values()

    backrefs = defaultdict(set)

    for filename in glob(str(Path(__file__).parent.parent / 'docs' / 'cookbook_*.rst')):
        with open(filename) as f:
            content = f.read()

        document = docutils.utils.new_document(filename, settings=settings)
        parser.parse(content, document)

        targets = [x for x in document.children if isinstance(x, target)]
        nodes = [x for x in document.children if not isinstance(x, target)]

        target_node = None if not targets else targets[0]

        assert len(nodes) == 1, 'Expected a document with only ONE level 1 header'
        (d,) = nodes

        for node in d.children:
            if isinstance(node, target):
                target_node = node
                continue
            if not node.attributes['ids']:
                continue
            if not node.children:
                continue
            if not isinstance(node, section):
                continue
            title_node = node.children[0]
            assert isinstance(title_node, title)

            for c in node.children:
                x = c.astext()

                if isinstance(c, target):
                    target_node = c

                elif isinstance(c, comment) and x.startswith('uses '):
                    if x.endswith(':'):
                        print(f'WARNING: bad `uses`: {x}')
                    if not target_node:
                        print(f'WARNING: no target for {title_node.astext()}. It must be ABOVE the title.')
                        continue

                    backrefs[strip_prefix(x, prefix='uses ')].add((target_node.attributes['ids'][0], title_node.astext()))

    assert backrefs
    return backrefs


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
        iommi.middleware,
        # Private-ish APIs
        iommi.endpoint.Endpoint,
        iommi.part.Part,
        iommi.traversable.Traversable,
        iommi.member.Members,
        iommi.table.Cell,
        iommi.table.Cells,
        iommi.table.ColumnHeader,
        iommi.table.HeaderConfig,
        iommi.attrs.Attrs,
        iommi.table.ColumnHeader,
        iommi.fragment.Container,
        iommi.table.TableAutoConfig,
        iommi.form.FormAutoConfig,
        iommi.query.QueryAutoConfig,
    ]


def generate_api_docs_tests(directory, classes=None, verbose=False):  # pragma: no cover - this is tested by rtd anyway
    """
    Generate test files for declarative APIs

    :param directory: directory to write the .py files into
    :param classes: list of classes to generate tests for
    :param verbose: print verbose warnings for missing docs
    """
    if classes is None:
        classes = get_default_classes()

    doc_by_filename = _generate_tests_from_class_docs(classes=classes, verbose=verbose)  # pragma: no mutate
    for source_filename, filename, doc_generator in doc_by_filename:  # pragma: no mutate
        doc = doc_generator()
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
        if not k.startswith('_')
        and k not in ignore_list
        and not is_shortcut(getattr(class_, k))
        and not is_refinable_function(getattr(class_, k))
    }

    return {
        'Methods': {k: v for k, v in r.items() if isinstance(v, function_type)},
        'Static methods': {k: v for k, v in r.items() if isinstance(v, staticmethod)},
        'Class methods': {k: v for k, v in r.items() if isinstance(v, classmethod)},
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


def indent_levels(levels, s):
    return (' ' * levels * 4) + s


def get_namespace(c):
    return Namespace(
        {
            k: getattr(c.__init__, '__iommi_with_defaults_kwargs', {}).get(k)
            for k, v in items(get_declared(c, 'refinable'))
        }
    )


def _generate_tests_from_class_docs(classes, verbose=False):
    uses_by_field = uses_from_cookbooks()

    for c in classes:
        from io import StringIO

        f = StringIO()
        yield _generate_tests_from_class_doc(f, c, classes, uses_by_field, verbose=verbose)


def _generate_tests_from_class_doc(f, c, classes, uses_by_field, verbose=False):
    return (
        inspect.getfile(c),
        'test_doc__api_%s.py' % c.__name__,
        lambda: _generate_tests_from_class_doc_inner(f, c, classes, uses_by_field, verbose=verbose),
    )


concepts = {
    'after': 'after',
    'assets': 'assets',
    'attr': 'attr',
    'attrs': 'attributes',
    'auto': 'auto',
    'endpoints': 'endpoints',
    'extra': 'extra',
    'extra_evaluated': 'extra',
    'extra_params': 'extra_params',
    'include': 'include',
    'iommi_style': 'iommi_style',
    'name': 'name',
    'display_name': 'name',
    'tag': 'tag',
    'template': 'template',
    'title': 'title',
    'h_tag': 'title',
}


def _generate_tests_from_class_doc_inner(f, c, classes, uses_by_field, verbose):
    def w(levels, s):
        f.write(indent_levels(levels, s))
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
from iommi.struct import Struct
from django.urls import (
    include,
    path,
)
import pytest
from django.db import models
from tests.helpers import req, user_req, staff_req, show_output
from docs.models import *

pytestmark = pytest.mark.django_db

@pytest.fixture(autouse=True)
def auto_use(big_discography):
    pass

request = req('get')


# language=rst
"""
    ''',
    )

    section(0, c.__name__, indent=0)

    class_text = ''
    constructor_text = ''
    params = {}
    for x in reversed(c.__mro__):
        foo = docstring_param_dict(x.__init__)
        constructor_text = foo.pop('text')
        params = merged(foo.pop('params'), params)

        foo = docstring_param_dict(x)
        class_text = foo.pop('text')
        params = merged(foo.pop('params'), params)
        assert not foo

    if c.__base__ in classes:
        w(0, f'Base class: :doc:`{c.__base__.__name__}`')
    else:
        w(0, f'Base class: `{c.__base__.__name__}`')

    w(0, '')

    w(0, '"""')
    w(0, 'def test_base():')
    w(1, '# language=rst')
    w(1, '"""')

    _print_rst_or_python(class_text, w)

    w(1, '"""')
    w(0, '')
    w(1, '# language=rst')
    w(1, '"""')

    if constructor_text:
        if constructor_text:
            w(0, '')

        f.write(constructor_text)
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
            evaluated_marker = ''
            if isinstance(getattr(c, refinable, None), (EvaluatedRefinable, SpecialEvaluatedRefinable)):
                evaluated_marker = (
                    '  \N{NO-BREAK SPACE}\N{NO-BREAK SPACE}\N{NO-BREAK SPACE}  (:ref:`evaluated <evaluate>`)'
                )

            w(0, '')
            section(2, '`' + refinable + '`' + evaluated_marker)

            docstring = getattr(getattr(c, refinable, None), '__doc__')
            if docstring:
                _print_rst_or_python(docstring, w, indent=0)
                w(0, '')
            elif params.get(refinable):
                w(0, params[refinable])
                w(0, '')
            type_hint = type_hints.get(refinable)
            if type_hint:
                name = str(type_hint)
                if name.startswith('typing.'):
                    name = name.replace('typing.', '')
                else:
                    name = type_hint.__name__

                if type_hint in classes:
                    w(0, f'Type: :doc:`{name}`')
                else:
                    w(0, f'Type: `{name}`')
                w(0, '')

            if refinable in defaults:
                w(0, f'Default: `{default_description(defaults.pop(refinable))}`')

            if refinable in concepts:
                w(1, f'See :ref:`{concepts[refinable]} <{concepts[refinable]}>`')
                w(0, '')

            cookbook_usages = uses_by_field.get(f'{c.__name__}.{refinable}', [])
            if cookbook_usages:
                w(0, '')
                w(0, f'Cookbook:')
                for id_, title in cookbook_usages:
                    w(1, f':ref:`{id_}`')
                    w(0, '')
            else:
                if refinable not in concepts and verbose:
                    print(f'WARNING: {c.__name__}.{refinable} has no cookbook examples')

        w(0, '')

    assert not defaults

    shortcuts = get_shortcuts_by_name(c)
    if shortcuts:
        section(1, 'Shortcuts')

        for name, shortcut in sorted(shortcuts.items()):
            section(2, f'`{c.__name__}.{name}`')

            if shortcut.__doc__:
                foo = docstring_param_dict(shortcut)
                _print_rst_or_python(foo['text'], w)
                w(0, '')

                if foo['params']:
                    w(0, '')
                    section(3, 'Parameters')
                    for k, v in foo['params'].items():
                        w(0, f'* `{k}`')
                        w(1, f'* `{v}`')

                w(0, '')

            try:
                instance = shortcut()
            except Exception:
                pass  # todo For now...
            else:
                parents = instance.iommi_shortcut_stack[1:]
                if parents:
                    parent = parents[0]

                    w(0, f'Parent: {c.__name__}.{parent}_')
                    w(0, '')

            defaults = shortcut if isinstance(shortcut, dict) else getattr(shortcut, '__iommi_with_defaults_kwargs', {})
            if defaults:
                defaults = Namespace(defaults)
                section(3, 'Defaults')
                for k, v in items(flatten(defaults)):
                    v = default_description(v)
                    w(0, f'* `{k}`')
                    w(1, f'* `{v}`')
                w(0, '')

            cookbook_usages = uses_by_field.get(f'{c.__name__}.{name}', [])
            if cookbook_usages:
                w(0, '')
                w(0, f'Cookbook:')
                for id_, title in cookbook_usages:
                    w(1, f':ref:`{id_}`')
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
    return f.getvalue()


def _print_rst_or_python(doc, w, indent=0):
    if not doc:
        return
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
                    w(1 + indent, line)
        else:
            w(0 + indent, line)
    if in_code_block:
        w(1, '# language=rst')
        w(1, '"""')
    w(0, '')


def write_rst_from_pytest():
    for source in (Path(__file__).parent.parent / 'docs/').glob('test_*.py'):
        target = source.parent / f'{source.stem.replace("test_doc__api_", "").replace("test_doc_", "")}.rst'

        with open(source) as source_f:
            with open(target, 'w') as target_f:
                rst_from_pytest(source_f, target_f, target)


def rst_from_pytest(source_f, target_f, target):
    blocks = []
    stack = []
    state_ = None

    def push(new_state, **kwargs):
        nonlocal state_
        nonlocal i
        assert state_ != 'only test', ('exited @test without @end', source_f.name, i)
        stack.append(new_state)
        blocks.append(Struct(state=new_state, lines=[], metadata=kwargs))
        state_ = new_state

    def pop():
        nonlocal state_
        stack.pop()
        state_ = stack[-1]
        blocks.append(Struct(state=state_, lines=[], metadata={}))

    def add_line(line):
        blocks[-1].lines.append(line)

    push('import')

    func_name = None
    func_count = 0

    for i, line in enumerate(source_f.readlines(), start=1):
        stripped_line = line.strip()
        if state_ in ('import', 'py') and line.startswith('def test_'):  # not stripped_line!
            func_name = line[len('def ') :].partition('(')[0]
            push('py', func_name=func_name, func_count=0)
            func_count = 0
        elif stripped_line.startswith("# language=rst"):
            push('starting rst')
        elif stripped_line in ('"""', "'''"):
            if state_ == 'starting rst':
                # add_line('')
                pop()
                push('rst')
            elif state_ == 'rst':
                pop()
        elif stripped_line.startswith('# @test'):
            push('only test')
        elif stripped_line.startswith('# @end'):
            pop()
        elif state_ == 'py' and line.startswith(
            '#'
        ):  # not stripped_line! skip comments on the global level between functions
            continue
        elif state_ == 'py' and line.startswith(
            '@'
        ):  # not stripped_line! skip decorators on the global level between functions
            continue
        else:
            if state_ == 'only test':
                if stripped_line.startswith('show_output(') or stripped_line.startswith('show_output_collapsed('):
                    name = join(target.stem, func_name)
                    if func_count:
                        name += str(func_count)
                    func_count += 1

                    blocks.append(
                        Struct(
                            state='raw',
                            lines=[create_iframe(name, collapsed=stripped_line.startswith('show_output_collapsed'))],
                            metadata={},
                        )
                    )
            else:
                add_line(line)

    for b in blocks:
        b.text = dedent(''.join(b.lines)).strip()
        del b['lines']

    blocks = [x for x in blocks if x.text]

    for b in blocks:
        if b.state == 'rst':
            target_f.write(b.text)
        elif b.state == 'py':
            target_f.write('.. code-block:: python\n\n')
            target_f.write(indent(b.text, '    '))
        elif b.state == 'raw':
            target_f.write('.. raw:: html\n\n')
            target_f.write(indent(b.text, '    '))

        target_f.write('\n\n')
