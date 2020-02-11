import functools
import inspect
from collections import (
    defaultdict,
)
from copy import copy

from tri_struct import (
    Frozen,
    Struct,
)

__version__ = '5.1.1'


def with_meta(class_to_decorate=None, add_init_kwargs=True):
    """
        Class decorator to enable a class (and it's sub-classes) to have a 'Meta' class attribute.

        :type class_to_decorate: class
        :param bool add_init_kwargs: Pass Meta class members to constructor

        :rtype: class
    """

    if class_to_decorate is None:
        return functools.partial(with_meta, add_init_kwargs=add_init_kwargs)

    if add_init_kwargs:
        def get_extra_args_function(self):
            return {k: v for k, v in self.get_meta().items() if not k.startswith('_')}

        add_args_to_init_call(class_to_decorate, get_extra_args_function)

    setattr(class_to_decorate, 'get_meta', classmethod(get_meta))

    return class_to_decorate


def get_meta(cls):
    """
        Collect all members of any contained :code:`Meta` class declarations from the given class or any of its base classes.
        (Sub class values take precedence.)

        :type cls: class
        :rtype: Struct
    """
    merged_attributes = Namespace()
    for class_ in reversed(cls.mro()):
        if hasattr(class_, 'Meta'):
            for key, value in class_.Meta.__dict__.items():
                if not key.startswith('__'):
                    merged_attributes.setitem_path(key, value)
    return merged_attributes


def get_members(cls, member_class=None, is_member=None, sort_key=None, _parameter=None):
    """
        Collect all class level attributes matching the given criteria.

        :param class member_class: Class(es) to collect
        :param is_member: Function to determine if an object should be collected
        :param sort_key: Function to invoke on members to obtain ordering (Default is to use ordering from `creation_ordered`)

        :type is_member: (object) -> bool
        :type sort_key: (object) -> object
    """
    if member_class is None and is_member is None:
        raise TypeError("get_members either needs a member_class parameter or an is_member check function (or both)")

    members = {}
    for base in cls.__bases__:
        if _parameter is None:
            inherited_members = get_members(base, member_class=member_class, is_member=is_member, sort_key=sort_key)
        else:
            # When user by @declarative, only traverse up the class inheritance to the decorated class.
            inherited_members = get_declared(base, _parameter)
        members.update(inherited_members)

    def generate_member_bindings():
        for name in cls.__dict__:
            if name.startswith('__'):
                continue
            obj = getattr(cls, name)
            if member_class is not None and isinstance(obj, member_class):
                yield name, obj
            elif is_member is not None and is_member(obj):
                yield name, obj
            elif type(obj) is tuple and len(obj) == 1 and isinstance(obj[0], member_class):
                raise TypeError("'%s' is a one-tuple containing what we are looking for.  Trailing comma much?  Don't... just don't." % name)  # pragma: no mutate

    bindings = generate_member_bindings()

    if sort_key is not None:
        sorted_bindings = sorted(bindings, key=lambda x: sort_key(x[1]))
        members.update(sorted_bindings)
    else:
        members.update(bindings)

    return members


def declarative(member_class=None, parameter='members', add_init_kwargs=True, sort_key=None, is_member=None):
    """
        Class decorator to enable classes to be defined in the style of django models.
        That is, @declarative classes will get an additional argument to constructor,
        containing a dict with all class members matching the specified type.

        :param class member_class: Class(es) to collect
        :param is_member: Function to determine if an object should be collected
        :param str parameter: Name of constructor parameter to inject
        :param bool add_init_kwargs: If constructor parameter should be injected (Default: True)
        :param sort_key: Function to invoke on members to obtain ordering (Default is to use ordering from `creation_ordered`)

        :type is_member: (object) -> bool
        :type sort_key: (object) -> object
    """
    if member_class is None and is_member is None:
        raise TypeError("The @declarative decorator needs either a member_class parameter or an is_member check function (or both)")

    def decorator(class_to_decorate):
        class DeclarativeMeta(class_to_decorate.__class__):
            # noinspection PyTypeChecker
            def __init__(cls, name, bases, dict):
                members = get_members(cls, member_class=member_class, is_member=is_member, sort_key=sort_key, _parameter=parameter)
                set_declared(cls, members, parameter)
                super(DeclarativeMeta, cls).__init__(name, bases, dict)

        new_class = DeclarativeMeta(class_to_decorate.__name__,
                                    class_to_decorate.__bases__,
                                    {k: v for k, v in class_to_decorate.__dict__.items() if k not in ['__dict__', '__weakref__']})

        def get_extra_args_function(self):
            declared = get_declared(self, parameter)
            copied_members = {k: copy(v) for k, v in declared.items()}
            self.__dict__.update(copied_members)
            return {parameter: copied_members}

        if add_init_kwargs:
            add_args_to_init_call(new_class, get_extra_args_function)
        else:
            add_init_call_hook(new_class, get_extra_args_function)

        setattr(new_class, 'get_declared', classmethod(get_declared))
        setattr(new_class, 'set_declared', classmethod(set_declared))

        return new_class

    return decorator


def set_declared(cls, value, parameter='members'):
    """
        :type cls: class
        :type value: dict
        :type parameter: str
    """

    setattr(cls, '_declarative_' + parameter, value)


def get_declared(cls, parameter='members'):
    """
        Get the :code:`dict` value of the parameter collected by the :code:`@declarative` class decorator.
        This is the same value that would be submitted to the :code:`__init__` invocation in the :code:`members`
        argument (or another name if overridden by the :code:`parameter` specification)

        :type cls: class
        :type parameter: str
        :rtype: dict
    """

    return getattr(cls, '_declarative_' + parameter, {})


def add_args_to_init_call(cls, get_extra_args_function):
    __init__orig = getattr(cls, '__init__')

    pos_arg_names = getattr(__init__orig, 'pos_arg_names', None)
    if pos_arg_names is None:
        pos_arg_names = inspect.getfullargspec(__init__orig)[0]
        pos_arg_names = list(pos_arg_names)[1:]  # Skip 'self'

    @functools.wraps(__init__orig, assigned=['__doc__'])
    def argument_injector_wrapper(self, *args, **kwargs):
        extra_kwargs = get_extra_args_function(self)
        new_args, new_kwargs = inject_args(args, kwargs, extra_kwargs, pos_arg_names)
        __init__orig(self, *new_args, **new_kwargs)

    argument_injector_wrapper.pos_arg_names = pos_arg_names
    setattr(cls, '__init__', argument_injector_wrapper)


def add_init_call_hook(cls, init_hook):
    __init__orig = getattr(cls, '__init__')

    def init_hook_wrapper(self, *args, **kwargs):
        init_hook(self)
        __init__orig(self, *args, **kwargs)

    init_hook_wrapper = functools.wraps(__init__orig, assigned=['__doc__'])(init_hook_wrapper)

    setattr(cls, '__init__', init_hook_wrapper)


def inject_args(args, kwargs, extra_args, pos_arg_names):
    new_kwargs = dict(extra_args)
    if pos_arg_names:
        if len(args) > len(pos_arg_names):
            raise TypeError('Too many positional arguments')
        new_kwargs.update((k, v) for k, v in zip(pos_arg_names, args))
        new_args = []
    else:
        new_args = args

    for k, v in kwargs.items():
        if isinstance(new_kwargs.get(k, None), Namespace):
            new_kwargs[k] = Namespace(new_kwargs[k], v)
        else:
            new_kwargs[k] = v

    return new_args, new_kwargs


def get_signature(func):
    """
        :type func: Callable
        :rtype: str
    """
    try:
        return object.__getattribute__(func, '__tri_declarative_signature')
    except AttributeError:
        pass

    try:
        names, _, varkw, defaults, _, _, _ = inspect.getfullargspec(func)
    except TypeError:
        return None

    first_arg_index = 1 if inspect.ismethod(func) else 0  # Skip self argument on methods

    number_of_defaults = len(defaults) if defaults else 0
    if number_of_defaults > 0:
        required = ','.join(sorted(names[first_arg_index:-number_of_defaults]))
        optional = ','.join(sorted(names[-number_of_defaults:]))
    else:
        required = ','.join(sorted(names[first_arg_index:]))
        optional = ''
    wildcard = '*' if varkw is not None else ''

    signature = '|'.join((required, optional, wildcard))
    try:
        object.__setattr__(func, '__tri_declarative_signature', signature)
    except TypeError:
        # For classes
        type.__setattr__(func, '__tri_declarative_signature', signature)
    except AttributeError:
        pass
    return signature


def signature_from_kwargs(kwargs):
    return ','.join(sorted(kwargs.keys()))


_matches_cache = {}


def matches(caller_parameters, callee_parameters):
    cache_key = ';'.join((caller_parameters, callee_parameters))  # pragma: no mutate
    cached_value = _matches_cache.get(cache_key, None)  # pragma: no mutate (mutation changes this to cached_value = None, which just slows down the code)
    if cached_value is not None:
        return cached_value

    caller = set(caller_parameters.split(',')) if caller_parameters else set()

    a, b, c = callee_parameters.split('|')
    required = set(a.split(',')) if a else set()
    optional = set(b.split(',')) if b else set()
    wildcard = (c == '*')

    if not required and not optional and wildcard:
        return False  # Special case to not match no-specification function "lambda **whatever: ..."

    if wildcard:
        result = caller >= required
    else:
        result = required <= caller <= required.union(optional)

    _matches_cache[cache_key] = result  # pragma: no mutate (mutation changes result to None which just makes things slower)
    return result


def get_callable_description(c):
    if getattr(c, '__name__', None) == '<lambda>':
        import inspect
        try:
            return 'lambda found at: `{}`'.format(inspect.getsource(c).strip())
        except OSError:
            pass
    return f'`{c}`'


def evaluate(func_or_value, __signature=None, __strict=False, **kwargs):
    if callable(func_or_value):
        if __signature is None:
            __signature = signature_from_kwargs(kwargs)

        callee_parameters = get_signature(func_or_value)
        if callee_parameters is not None and matches(__signature, callee_parameters):
            return func_or_value(**kwargs)
    if __strict and callable(func_or_value):
        assert (
            isinstance(func_or_value, Namespace)
            and 'call_target' not in func_or_value
        ), "Evaluating {} didn't resolve it into a value but strict mode was active, " \
           "the signature doesn't match the given parameters. " \
           "Note that you must match at least one keyword argument. " \
           "We had these arguments: {}".format(
            get_callable_description(func_or_value),
            ', '.join(kwargs.keys()),
        )
    return func_or_value


def evaluate_strict(func_or_value, __signature=None, **kwargs):
    return evaluate(func_or_value, __signature=None, __strict=True, **kwargs)


def evaluate_recursive(func_or_value, __signature=None, __strict=False, **kwargs):
    if __signature is None:
        __signature = signature_from_kwargs(kwargs)  # pragma: no mutate

    if isinstance(func_or_value, dict):
        # The type(item)(** stuff is to preserve the original type
        return type(func_or_value)(**{k: evaluate_recursive(v, __signature=__signature, __strict=__strict, **kwargs) for k, v in dict.items(func_or_value)})

    if isinstance(func_or_value, list):
        return [evaluate_recursive(v, __signature=__signature, __strict=__strict, **kwargs) for v in func_or_value]

    if isinstance(func_or_value, set):
        return {evaluate_recursive(v, __signature=__signature, __strict=__strict, **kwargs) for v in func_or_value}

    return evaluate(func_or_value, __signature=__signature, __strict=__strict, **kwargs)


def evaluate_recursive_strict(func_or_value, __signature=None, **kwargs):
    """
    Like `evaluate_recursive` but won't allow un-evaluated callables to slip through.
    """
    return evaluate_recursive(func_or_value, __signature=None, __strict=True, **kwargs)


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


class Namespace(Struct):
    def __init__(self, *dicts, **kwargs):
        if dicts or kwargs:
            for mappings in list(dicts) + [kwargs]:
                for path, value in dict.items(mappings):
                    self.setitem_path(path, value)

    def setitem_path(self, path, value):
        if value is EMPTY:
            value = Namespace()
        key, delimiter, rest_path = path.partition('__')

        def get_type_of_namespace(dict_value):
            if isinstance(dict_value, Namespace):
                return type(dict_value)
            else:
                return Namespace

        existing = Struct.get(self, key)
        if delimiter:
            if isinstance(existing, dict):
                type_of_namespace = get_type_of_namespace(existing)
                self[key] = type_of_namespace(existing, {rest_path: value})
            elif callable(existing):
                self[key] = Namespace(dict(call_target=existing), {rest_path: value})
            else:
                # Unable to promote to Namespace, just overwrite
                self[key] = Namespace({rest_path: value})
        else:
            if is_shortcut(existing):
                # Avoid merging Shortcuts
                self[key] = value
            elif isinstance(existing, dict):
                type_of_namespace = get_type_of_namespace(existing)
                if isinstance(value, dict):
                    self[key] = type_of_namespace(existing, value)
                elif callable(value):
                    self[key] = type_of_namespace(existing, call_target=value)
                else:
                    # Unable to promote to Namespace, just overwrite
                    self[key] = value
            elif callable(existing):
                if isinstance(value, dict):
                    type_of_namespace = get_type_of_namespace(value)
                    self[key] = type_of_namespace(Namespace(call_target=existing), value)
                else:
                    self[key] = value
            else:
                self[key] = value

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, ", ".join('%s=%r' % (k, v) for k, v in sorted(flatten_items(self), key=lambda x: x[0])))

    def __str__(self):
        return "%s(%s)" % (type(self).__name__, ", ".join('%s=%s' % (k, v) for k, v in sorted(flatten_items(self), key=lambda x: x[0])))

    def __call__(self, *args, **kwargs):
        params = Namespace(self, kwargs)

        try:
            call_target = params.pop('call_target')
        except KeyError:
            raise TypeError('Namespace was used as a function, but no call_target was specified. The namespace is: %s' % self)

        if isinstance(call_target, Namespace):
            if 'call_target' in call_target:
                # Override of the default
                call_target.pop('attribute', None)
                call_target.pop('cls', None)
            else:
                # The default
                if 'attribute' in call_target:
                    call_target = getattr(call_target.cls, call_target.attribute)
                else:
                    call_target = call_target.cls

        return call_target(*args, **params)


# This is just a marker class for declaring shortcuts, and later for collecting them
class Shortcut(Namespace):
    pass


# decorator
def shortcut(f):
    f.shortcut = True
    return f


def is_shortcut(x):
    return isinstance(x, Shortcut) or getattr(x, 'shortcut', False)


def class_shortcut(*args, **defaults):
    def decorator(__target__):
        @shortcut
        @dispatch(
            **defaults
        )
        def class_shortcut_wrapper(cls, *args, **kwargs):
            call_target = kwargs.pop('call_target', None)
            if call_target is None:
                setdefaults_path(
                    kwargs,
                    call_target__call_target__cls=cls,
                )
            else:
                setdefaults_path(
                    kwargs,
                    call_target__call_target=call_target,
                    call_target__call_target__cls=cls,
                )

            result = __target__(cls, *args, **kwargs)

            shortcut_stack = [__target__.__name__] + getattr(result, '__tri_declarative_shortcut_stack', [])
            try:
                result.__tri_declarative_shortcut_stack = shortcut_stack
            except AttributeError:
                pass

            return result

        class_shortcut_wrapper.__doc__ = __target__.__doc__
        return class_shortcut_wrapper

    assert len(args) in (0, 1), "There are no (explicit) positional arguments to class_shortcut"  # pragma: no mutate

    if len(args) == 1:
        return decorator(args[0])

    return decorator


def flatten(namespace):
    return dict(flatten_items(namespace))


def flatten_items(namespace):
    def mappings(n, visited, prefix=''):
        for key, value in dict.items(n):
            path = prefix + key
            if isinstance(value, Namespace):
                if id(value) not in visited:
                    if value:
                        for mapping in mappings(value, visited=[id(value)] + visited, prefix=path + '__'):
                            yield mapping
                    else:
                        yield path, Namespace()
            else:
                yield path, value

    return mappings(namespace, visited=[])


class FrozenNamespace(Frozen, Namespace):
    pass


EMPTY = FrozenNamespace()


# The first argument has a funky name to avoid name clashes with stuff in kwargs
def setdefaults_path(__target__, *defaults, **kwargs):
    args = [kwargs] + list(reversed(defaults)) + [__target__]
    dict.update(__target__, Namespace(*args))
    return __target__


def dispatch(*function, **defaults):
    def decorator(f):
        @functools.wraps(f)
        def dispatch_defaults_wrapper(*args, **kwargs):
            return f(*args, **Namespace(defaults, kwargs))

        dispatch_defaults_wrapper.dispatch = Namespace(defaults)  # we store these here so we can inspect them for stuff like documentation
        return dispatch_defaults_wrapper

    if function:
        assert len(function) == 1
        return decorator(function[0])

    return decorator


def getattr_path(obj, path):
    """
    Get an attribute path, as defined by a string separated by '__'.
    getattr_path(foo, 'a__b__c') is roughly equivalent to foo.a.b.c but
    will short circuit to return None if something on the path is None.
    """
    path = path.split('__')
    for name in path:
        obj = getattr(obj, name)
        if obj is None:
            return None
    return obj


def setattr_path(obj, path, value):
    """
    Set an attribute path, as defined by a string separated by '__'.
    setattr_path(foo, 'a__b__c', value) is equivalent to "foo.a.b.c = value".
    """
    path = path.split('__')
    o = obj
    for name in path[:-1]:
        o = getattr(o, name)
    setattr(o, path[-1], value)
    return obj


LAST = object()


def sort_after(l):
    unmoved = []
    to_be_moved_by_index = []
    to_be_moved_by_name = defaultdict(list)
    to_be_moved_last = []
    for x in l:
        after = getattr(x, 'after', None)
        if after is None:
            unmoved.append(x)
        elif after is LAST:
            to_be_moved_last.append(x)
        elif isinstance(after, int):
            to_be_moved_by_index.append(x)
        else:
            to_be_moved_by_name[x.after].append(x)

    to_be_moved_by_index = sorted(to_be_moved_by_index, key=lambda x: x.after)  # pragma: no mutate (infinite loop when x.after changed to None, but if changed to a number manually it exposed a missing test)

    def place(x):
        yield x
        for y in to_be_moved_by_name.pop(x.name, []):
            for z in place(y):
                yield z

    def traverse():
        count = 0
        while unmoved or to_be_moved_by_index:
            while to_be_moved_by_index:
                next_by_position_index = to_be_moved_by_index[0].after
                if count < next_by_position_index:  # pragma: no mutate (infinite loop when mutating < to <=)
                    break  # pragma: no mutate (infinite loop when mutated to continue)

                objects_with_index_due = place(to_be_moved_by_index.pop(0))
                for x in objects_with_index_due:
                    yield x
                    count += 1  # pragma: no mutate
            if unmoved:
                next_unmoved_and_its_children = place(unmoved.pop(0))
                for x in next_unmoved_and_its_children:
                    yield x
                    count += 1  # pragma: no mutate

        for x in to_be_moved_last:
            for y in place(x):
                yield y

    result = list(traverse())

    if to_be_moved_by_name:
        available_names = "\n   ".join(sorted([x.name for x in l]))
        raise KeyError(f'Tried to order after {", ".join(sorted(to_be_moved_by_name.keys()))} but {"that key does" if len(to_be_moved_by_name) == 1 else "those keys do"} not exist.\nAvailable names:\n    {available_names}')

    return result


def assert_kwargs_empty(kwargs):
    if kwargs:
        import traceback
        function_name = traceback.extract_stack()[-2][2]
        raise TypeError('%s() got unexpected keyword arguments %s' % (function_name, ', '.join(["'%s'" % x for x in sorted(kwargs.keys())])))


def full_function_name(f):
    return '%s.%s' % (f.__module__, f.__name__)


def get_shortcuts_by_name(class_):
    return dict(get_members(class_, member_class=Shortcut, is_member=is_shortcut))


class Refinable:
    pass


# decorator
def refinable(f):
    f.refinable = True
    return f


def is_refinable_function(attr):
    return getattr(attr, 'refinable', False)


@declarative(
    member_class=Refinable,
    parameter='refinable_members',
    is_member=is_refinable_function,
    add_init_kwargs=False,
)
class RefinableObject:
    # This constructor assumes that the class that inherits from RefinableObject
    # has done any attribute assignments to self BEFORE calling super(...)
    @dispatch()
    def __init__(self, **kwargs):
        declared_items = self.get_declared('refinable_members')
        for k, v in declared_items.items():
            if isinstance(v, Refinable):
                setattr(self, k, kwargs.pop(k, None))
            else:
                if k in kwargs:
                    setattr(self, k, kwargs.pop(k))

        if kwargs:
            available_keys = '\n    '.join(sorted(declared_items.keys()))
            raise TypeError(f"""'{self.__class__.__name__}' object has no refinable attribute(s): {', '.join(sorted(kwargs.keys()))}.
Available attributes:
    {available_keys}""")

        super(RefinableObject, self).__init__()


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
