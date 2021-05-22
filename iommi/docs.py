from glob import glob
from pathlib import Path
from textwrap import dedent
from typing import get_type_hints

from tri_declarative import (
    flatten,
    flatten_items,
    get_declared,
    get_shortcuts_by_name,
    Namespace,
)

from iommi import MISSING
from iommi.base import items


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


def generate_rst_docs(directory, classes=None):  # pragma: no cover - this is tested by rtd anyway
    """
    Generate documentation for tri.declarative APIs

    :param directory: directory to write the .rst files into
    :param classes: list of classes to generate documentation for
    """
    if classes is None:
        classes = get_default_classes()

    doc_by_filename = _generate_rst_docs(classes=classes)  # pragma: no mutate
    for filename, doc in doc_by_filename:  # pragma: no mutate
        with open(directory + filename, 'w') as f2:  # pragma: no mutate
            f2.write(doc)  # pragma: no mutate


def get_docs_callable_description(c):
    if getattr(c, '__name__', None) == '<lambda>':
        import inspect

        return inspect.getsource(c).strip()
    return c.__module__ + '.' + c.__name__


def _generate_rst_docs(classes):
    import re

    cookbook_links = read_cookbook_links()
    validate_cookbook_links(cookbook_links)
    # TODO: validate that all cookbook links are actually linked somewhere. For example ".. _Column.cells_for_rows" isn't right now.
    cookbook_name_by_refinable_name = {}
    for links, name in cookbook_links:
        for link in links:
            cookbook_name_by_refinable_name[link] = name

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
        return (' ' * levels * 4) + s.strip()

    def get_namespace(c):
        return Namespace({k: c.__init__.dispatch.get(k) for k, v in items(get_declared(c, 'refinable_members'))})

    for c in classes:
        from io import StringIO

        f = StringIO()

        def w(levels, s):
            f.write(indent(levels, s))
            f.write('\n')

        def section(level, title):
            underline = {0: '=', 1: '-', 2: '^', 3: '+'}[level] * len(title)
            w(0, title)
            w(0, underline)
            w(0, '')

        section(0, c.__name__)

        class_doc = docstring_param_dict(c)
        constructor_doc = docstring_param_dict(c.__init__)

        if c.__base__ in classes:
            w(0, f'Base class: :doc:`{c.__base__.__name__}`')
        else:
            w(0, f'Base class: `{c.__base__.__name__}`')

        w(0, '')

        if class_doc['text']:
            f.write(class_doc['text'])
            w(0, '')

        if constructor_doc['text']:
            if class_doc['text']:
                w(0, '')

            f.write(constructor_doc['text'])
            w(0, '')

        w(0, '')

        refinable_members = sorted(dict.items(get_namespace(c)))
        if refinable_members:
            section(1, 'Refinable members')
            type_hints = get_type_hints(c)
            for refinable, value in refinable_members:
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
                    w(1, '')

                ref_name = f'{c.__name__}.{refinable}'
                if ref_name in cookbook_name_by_refinable_name:
                    w(1, f'Cookbook: :ref:`{ref_name.lower()}`')
                    w(1, '')

            w(0, '')

        defaults = Namespace()
        for refinable, value in sorted(get_namespace(c).items()):
            if value not in (None, MISSING):
                defaults[refinable] = value

        def default_description(v):
            if callable(v) and not isinstance(v, Namespace):
                v = get_docs_callable_description(v)

                if 'lambda' in v:
                    v = v[v.find('lambda') :]
                    v = v.strip().strip(',').replace('\n', ' ').replace('  ', ' ')
            if v == '':
                v = '""'
            return v

        if defaults:
            section(2, 'Defaults')

            for k, v in sorted(flatten_items(defaults)):
                if v != {}:
                    v = default_description(v)

                    w(0, '* `%s`' % k)
                    w(1, '* `%s`' % v)
            w(0, '')

        shortcuts = get_shortcuts_by_name(c)
        if shortcuts:
            section(1, 'Shortcuts')

            for name, shortcut in sorted(shortcuts.items()):
                section(2, f'`{name}`')

                if shortcut.__doc__:
                    doc = shortcut.__doc__
                    f.write(doc.strip())
                    w(0, '')
                    w(0, '')

                defaults = shortcut if isinstance(shortcut, dict) else shortcut.dispatch
                if defaults:
                    defaults = Namespace(defaults)
                    section(3, 'Defaults')
                    for k, v in items(flatten(defaults)):
                        v = default_description(v)
                        w(0, f'* `{k}`')
                        w(1, f'* `{v}`')
                    w(0, '')

        yield '/%s.rst' % c.__name__, f.getvalue()
