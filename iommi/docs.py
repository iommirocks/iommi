from textwrap import dedent

from tri_declarative import (
    flatten,
    flatten_items,
    get_declared,
    get_shortcuts_by_name,
    Namespace,
)

from iommi import MISSING


def generate_rst_docs(directory, classes):
    """
    Generate documentation for tri.declarative APIs

    :param directory: directory to write the .rst files into
    :param classes: list of classes to generate documentation for
    """

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

    def docstring_param_dict(obj):
        doc = obj.__doc__
        if doc is None:
            return dict(text=None, params={})
        doc = dedent(doc)
        return dict(
            text=doc[:doc.find(':param')].strip() if ':param' in doc else doc.strip(),
            params=dict(re.findall(r":param (?P<name>\w+): (?P<text>.*)", doc))
        )

    def indent(levels, s):
        return (' ' * levels * 4) + s.strip()

    def get_namespace(c):
        return Namespace({
            k: c.__init__.dispatch.get(k)
            for k, v in get_declared(c, 'refinable_members').items()
        })

    for c in classes:
        from io import StringIO
        f = StringIO()

        def w(levels, s):
            f.write(indent(levels, s))
            f.write('\n')

        def section(level, title):
            underline = {
                0: '=',
                1: '-',
                2: '^',
                3: '+',
            }[level] * len(title)
            w(0, title)
            w(0, underline)
            w(0, '')

        section(0, c.__name__)

        class_doc = docstring_param_dict(c)
        constructor_doc = docstring_param_dict(c.__init__)

        if class_doc['text']:
            f.write(class_doc['text'])
            w(0, '')

        if constructor_doc['text']:
            if class_doc['text']:
                w(0, '')

            f.write(constructor_doc['text'])
            w(0, '')

        w(0, '')

        w(0, f'Base class: :doc:`{c.__base__.__name__} <{c.__base__.__name__}>`')

        w(0, '')

        section(1, 'Refinable members')
        for refinable, value in sorted(dict.items(get_namespace(c))):
            w(0, '* `' + refinable + '`')

            if constructor_doc['params'].get(refinable):
                w(1, constructor_doc['params'][refinable])
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
                    for k, v in flatten(defaults).items():
                        v = default_description(v)
                        w(0, f'* `{k}`')
                        w(1, f'* `{v}`')
                    w(0, '')

        yield '/%s.rst' % c.__name__, f.getvalue()
