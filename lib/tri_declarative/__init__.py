from .declarative import declarative
from .declarative import get_declared
from .dispatch import dispatch
from .evaluate import (
    evaluate,
    evaluate_strict,
    evaluate_recursive,
    evaluate_recursive_strict,
    get_callable_description,
    matches,
)
from .namespace import (
    EMPTY,
    flatten,
    flatten_items,
    Namespace,
)
from .refinable import (
    refinable,
    Refinable,
    RefinableObject
)
from .shortcut import (
    class_shortcut,
    is_shortcut,
    Shortcut,
)
from .sort_after import (
    LAST,
    sort_after
)
from .shortcut import shortcut
from .util import (
    add_args_to_init_call,
    get_members,
    get_signature,
    getattr_path,
    setattr_path,
    setdefaults_path,
    signature_from_kwargs,
)
from .with_meta import with_meta

__version__ = '5.4.0'

__all__ = [
    'class_shortcut',
    'declarative',
    'dispatch',
    'EMPTY',
    'evaluate',
    'evaluate_strict',
    'evaluate_recursive',
    'evaluate_recursive_strict',
    'filter_show_recursive',
    'flatten',
    'flatten_items',
    'full_function_name',
    'get_signature',
    'getattr_path',
    'LAST',
    'matches',
    'Namespace',
    'remove_show_recursive',
    'refinable',
    'Refinable',
    'RefinableObject',
    'setattr_path',
    'setdefaults_path',
    'Shortcut',
    'should_show',
    'sort_after',
    'with_meta',
]


def should_show(item):
    try:
        r = item.show
    except AttributeError:
        try:
            r = item['show']
        except (TypeError, KeyError):
            return True

    if callable(r):
        assert False, "`show` was a callable. You probably forgot to evaluate it. The callable was: {}".format(get_callable_description(r))

    return r


def filter_show_recursive(item):
    if isinstance(item, list):
        return [filter_show_recursive(v) for v in item if should_show(v)]

    if isinstance(item, dict):
        # The type(item)(** stuff is to preserve the original type
        return type(item)(**{k: filter_show_recursive(v) for k, v in dict.items(item) if should_show(v)})

    if isinstance(item, set):
        return {filter_show_recursive(v) for v in item if should_show(v)}

    return item


def remove_keys_recursive(item, keys_to_remove):
    if isinstance(item, list):
        return [remove_keys_recursive(v, keys_to_remove) for v in item]

    if isinstance(item, set):
        return {remove_keys_recursive(v, keys_to_remove) for v in item}

    if isinstance(item, dict):
        return {k: remove_keys_recursive(v, keys_to_remove) for k, v in dict.items(item) if k not in keys_to_remove}

    return item


def remove_show_recursive(item):
    return remove_keys_recursive(item, {'show'})


def assert_kwargs_empty(kwargs):
    if kwargs:
        import traceback
        function_name = traceback.extract_stack()[-2][2]
        raise TypeError('%s() got unexpected keyword arguments %s' % (function_name, ', '.join(["'%s'" % x for x in sorted(kwargs.keys())])))


def full_function_name(f):
    return '%s.%s' % (f.__module__, f.__name__)


def get_shortcuts_by_name(class_):
    return dict(get_members(class_, member_class=Shortcut, is_member=is_shortcut))


def generate_rst_docs(directory, classes, missing_objects=None):  # pragma: no coverage
    """
    Generate documentation for tri.declarative APIs

    :param directory: directory to write the .rst files into
    :param classes: list of classes to generate documentation for
    :param missing_objects: tuple of objects to count as missing markers, if applicable
    """

    doc_by_filename = _generate_rst_docs(classes=classes, missing_objects=missing_objects)  # pragma: no mutate
    for filename, doc in doc_by_filename:  # pragma: no mutate
        with open(directory + filename, 'w') as f2:  # pragma: no mutate
            f2.write(doc)  # pragma: no mutate


def _generate_rst_docs(classes, missing_objects=None):
    if missing_objects is None:
        missing_objects = tuple()

    import re

    def docstring_param_dict(obj):
        doc = obj.__doc__
        if doc is None:
            return dict(text=None, params={})
        return dict(
            text=doc[:doc.find(':param')].strip() if ':param' in doc else doc.strip(),
            params=dict(re.findall(r":param (?P<name>\w+): (?P<text>.*)", doc))
        )

    def indent(levels, s):
        return (' ' * levels * 4) + s.strip()

    def get_namespace(c):
        return Namespace(
            {k: c.__init__.dispatch.get(k) for k, v in get_declared(c, 'refinable_members').items()})

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

        section(1, 'Refinable members')
        for refinable, value in sorted(dict.items(get_namespace(c))):
            w(0, '* `' + refinable + '`')

            if constructor_doc['params'].get(refinable):
                w(1, constructor_doc['params'][refinable])
                w(0, '')
        w(0, '')

        defaults = Namespace()
        for refinable, value in sorted(get_namespace(c).items()):
            if value not in (None,) + missing_objects:
                defaults[refinable] = value

        if defaults:
            section(2, 'Defaults')

            for k, v in sorted(flatten_items(defaults)):
                if v != {}:
                    if '<lambda>' in repr(v):
                        import inspect
                        v = inspect.getsource(v)
                        v = v[v.find('lambda'):]
                        v = v.strip().strip(',')
                    elif callable(v):
                        v = v.__module__ + '.' + v.__name__

                    if v == '':
                        v = '""'

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

        yield '/%s.rst' % c.__name__, f.getvalue()
