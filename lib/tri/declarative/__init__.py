from collections import OrderedDict, defaultdict
from copy import copy
import functools
import inspect
import itertools

from tri.struct import Struct, Frozen

__version__ = '0.31.0'  # pragma: no mutate


def with_meta(class_to_decorate=None, add_init_kwargs=True):
    """
        Class decorator to enable a class (and it's sub-classes) to have a 'Meta' class attribute.

        @type class_to_decorate: class
        @type add_init_kwargs: bool
        @return class
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

        @type cls: class
        @return Struct
    """
    merged_attributes = Struct()
    for class_ in reversed(cls.mro()):
        if hasattr(class_, 'Meta'):
            for key, value in class_.Meta.__dict__.items():
                merged_attributes[key] = value
    return merged_attributes


def creation_ordered(class_to_decorate):
    """
        Class decorator that ensures that instances will be ordered after creation order when sorted.

        @type class_to_decorate: class
        @return class
    """

    next_index = functools.partial(next, itertools.count())

    __init__orig = class_to_decorate.__init__

    @functools.wraps(__init__orig, assigned=['__doc__'])
    def __init__(self, *args, **kwargs):
        object.__setattr__(self, '_index', next_index())
        __init__orig(self, *args, **kwargs)

    setattr(class_to_decorate, '__init__', __init__)

    # noinspection PyProtectedMember
    def __lt__(self, other):
        return self._index < other._index  # pragma: no mutate

    setattr(class_to_decorate, '__lt__', __lt__)

    class_to_decorate = functools.total_ordering(class_to_decorate)

    return class_to_decorate


def default_sort_key(x):
    # noinspection PyProtectedMember
    return x._index


def declarative(member_class=None, parameter='members', add_init_kwargs=True, sort_key=default_sort_key, is_member=None):
    """
        Class decorator to enable classes to be defined in the style of django models.
        That is, @declarative classes will get an additional argument to constructor,
        containing an OrderedDict with all class members matching the specified type.

        @param member_class: Class(es) to collect
        @param is_member: Function to determine if an object should be collected
        @param parameter: Name of constructor parameter to inject
        @param add_init_kwargs: If constructor parameter should be injected (Default: True)
        @param sort_key: Function to invoke on members to obtain ordering (Default is
        to use ordering from `@creation_ordered`)

        @type member_class: class
        @type is_member: (object) -> bool
        @type parameter: str
        @type add_init_kwargs: bool
        @type sort_key: (object) -> object
    """
    assert member_class or is_member, "....."

    def get_members(cls):
        members = OrderedDict()
        for base in cls.__bases__:
            inherited_members = get_declared(base, parameter)
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
        try:
            sorted_bindings = sorted(bindings, key=lambda x: sort_key(x[1]))
        except AttributeError:
            if sort_key is default_sort_key:
                raise TypeError('Missing member ordering definition. Use @creation_ordered or specify sort_key')
            else:  # pragma: no cover
                raise
        members.update(sorted_bindings)

        return members

    def decorator(class_to_decorate):

        class DeclarativeMeta(class_to_decorate.__class__):
            # noinspection PyTypeChecker
            def __init__(cls, name, bases, dict):
                members = get_members(cls)
                set_declared(cls, members, parameter)
                super(DeclarativeMeta, cls).__init__(name, bases, dict)

        new_class = DeclarativeMeta(class_to_decorate.__name__,
                                    class_to_decorate.__bases__,
                                    {k: v for k, v in class_to_decorate.__dict__.items() if k not in ['__dict__', '__weakref__']})

        def get_extra_args_function(self):
            members = get_declared(self, parameter)

            def copy_members():
                for k, v in members.items():
                    try:
                        v = copy(v)
                    except TypeError:
                        pass  # Not always possible to copy methods
                    yield (k, v)

            copied_members = OrderedDict(copy_members())
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
        @type cls: class
        @type value: OrderedDict
        @type parameter: str
    """

    setattr(cls, '_declarative_' + parameter, value)


def get_declared(cls, parameter='members'):
    """
        Get the :code:`OrderedDict` value of the parameter collected by the :code:`@declarative` class decorator.
        This is the same value that would be submitted to the :code:`__init__` invocation in the :code:`members`
        argument (or another name if overridden by the :code:`parameter` specification)
        @type cls: class
        @type parameter: str
        @return OrderedDict
    """

    return getattr(cls, '_declarative_' + parameter, {})


def add_args_to_init_call(cls, get_extra_args_function):
    __init__orig = object.__getattribute__(cls, '__init__')  # Use object.__getattribute__ to not have the original implementation bind to the class

    pos_arg_names = getattr(__init__orig, 'pos_arg_names', None)
    if pos_arg_names is None:
        try:
            pos_arg_names, _, _, _ = inspect.getargspec(__init__orig)
            pos_arg_names = list(pos_arg_names)[1:]  # Skip 'self'
        except TypeError:
            # We might fail on not being able to find the signature of builtin constructors
            pass

    @functools.wraps(__init__orig, assigned=['__doc__'])
    def argument_injector_wrapper(self, *args, **kwargs):
        extra_kwargs = get_extra_args_function(self)
        new_args, new_kwargs = inject_args(args, kwargs, extra_kwargs, pos_arg_names)
        __init__orig(self, *new_args, **new_kwargs)

    argument_injector_wrapper.pos_arg_names = pos_arg_names
    setattr(cls, '__init__', argument_injector_wrapper)


def add_init_call_hook(cls, init_hook):
    # Use object.__getattribute__ to not have the original implementation bind to the class
    # Extra acrobatics to get None if no __init__ is defined
    __init__orig = object.__getattribute__(cls, '__dict__').get('__init__', None)

    def init_hook_wrapper(self, *args, **kwargs):
        init_hook(self)
        if __init__orig is None:
            super(cls, self).__init__(*args, **kwargs)
        else:
            __init__orig(self, *args, **kwargs)

    if __init__orig is not None:
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
    new_kwargs.update(kwargs)
    return new_args, new_kwargs


def get_signature(func):
    """
        @type func: Callable
        @return str
    """
    try:
        return func.__tri_declarative_signature
    except AttributeError:
        pass

    try:
        names, _, varkw, defaults = inspect.getargspec(func)
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
        func.__tri_declarative_signature = signature
    except AttributeError:
        pass
    return signature


def signature_from_kwargs(kwargs):
    return ','.join(sorted(kwargs.keys()))


_matches_cache = {}


def matches(caller_parameters, callee_parameters):
    cache_key = ';'.join((caller_parameters, callee_parameters))  # pragma: no mutate
    cached_value = _matches_cache.get(cache_key, None)
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
        result = caller >= required and required.union(optional) >= set(caller)

    _matches_cache[cache_key] = result
    return result


def evaluate(func_or_value, signature=None, **kwargs):
    if callable(func_or_value):
        if signature is None:
            signature = signature_from_kwargs(kwargs)

        callee_parameters = get_signature(func_or_value)
        if callee_parameters is not None and matches(signature, callee_parameters):
            return func_or_value(**kwargs)
    return func_or_value


def evaluate_recursive(func_or_value, signature=None, **kwargs):
    if signature is None:  # pragma: no mutate
        signature = signature_from_kwargs(kwargs)

    if isinstance(func_or_value, dict):
        # The type(item)(** stuff is to preserve the original type
        return type(func_or_value)(**{k: evaluate_recursive(v, signature=signature, **kwargs) for k, v in func_or_value.items()})

    if isinstance(func_or_value, list):
        return [evaluate_recursive(v, signature=signature, **kwargs) for v in func_or_value]

    if isinstance(func_or_value, set):
        return {evaluate_recursive(v, signature=signature, **kwargs) for v in func_or_value}

    return evaluate(func_or_value, signature=signature, **kwargs)


def should_show(item):
    try:
        return item.show
    except AttributeError:
        try:
            return item['show']
        except (TypeError, KeyError):
            return True


def filter_show_recursive(item):
    if isinstance(item, list):
        return [filter_show_recursive(v) for v in item if should_show(v)]

    if isinstance(item, set):
        return {filter_show_recursive(v) for v in item if should_show(v)}

    if isinstance(item, dict):
        # The type(item)(** stuff is to preserve the original type
        return type(item)(**{k: filter_show_recursive(v) for k, v in item.items() if should_show(v)})

    return item


def remove_keys_recursive(item, keys_to_remove):
    if isinstance(item, list):
        return [remove_keys_recursive(v, keys_to_remove) for v in item]

    if isinstance(item, set):
        return {remove_keys_recursive(v, keys_to_remove) for v in item}

    if isinstance(item, dict):
        return {k: remove_keys_recursive(v, keys_to_remove) for k, v in item.items() if k not in keys_to_remove}

    return item


def remove_show_recursive(item):
    return remove_keys_recursive(item, {'show'})


def collect_namespaces(values):
    """
    Gather mappings with keys of the shape '<base_key>__<sub_key>' as new dicts under '<base_key>', indexed by '<sub_key>'.

    >>> foo = dict(
    ...     foo__foo=1,
    ...     foo__bar=2,
    ...     bar__foo=3,
    ...     bar__bar=4,
    ...     foo_baz=5,
    ...     baz=6
    ... )

    >>> assert collect_namespaces(foo) == dict(
    ...     foo=dict(foo=1, bar=2),
    ...     bar=dict(foo=3, bar=4),
    ...     foo_baz=5,
    ...     baz=6
    ... )

    @type values: dict
    @rtype: dict
    """
    namespaces = {}
    result = dict(values)
    for key, value in values.items():
        parts = key.split('__', 1)  # pragma: no mutate
        if len(parts) == 2:
            prefix, name = parts
            if prefix not in namespaces:
                initial_namespace = values.get(prefix)
                if initial_namespace is None:
                    initial_namespace = {}
                elif not isinstance(initial_namespace, dict):
                    initial_namespace = {initial_namespace: True}
                namespaces[prefix] = initial_namespace
            namespaces[prefix][name] = result.pop(key)
    for prefix, namespace in namespaces.items():
        result[prefix] = namespace
    return result


def extract_subkeys(kwargs, prefix, defaults=None):
    """
    Extract mappings of the shape '<base_key>__<sub_key>' to new mappings under '<sub_key>'.

    >>> foo = {
    ...     'foo__foo': 1,
    ...     'foo__bar': 2,
    ...     'baz': 3,
    ... }
    >>> assert extract_subkeys(foo, 'foo', defaults={'quux': 4}) == {
    ...     'foo': 1,
    ...     'bar': 2,
    ...     'quux': 4,
    ... }

    @type kwargs: dict
    @return dict
    """

    prefix += '__'
    result = {k[len(prefix):]: v for k, v in kwargs.items() if k.startswith(prefix)}
    if defaults is not None:
        return setdefaults(result, defaults)
    else:
        return result


def setdefaults(d, d2):
    """
    @type d: dict
    @type d2: dict
    @return dict
    """
    for k, v in d2.items():
        d.setdefault(k, v)
    return d


class Namespace(Struct):
    def __init__(self, *args, **kwargs):
        if args or kwargs:
            super(Namespace, self).__init__(setdefaults_path(Namespace(), *args, **kwargs))

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, ", ".join('%s=%r' % (k, v) for k, v in sorted(flatten_items(self), key=lambda x: x[0])))

    def __str__(self):
        return "%s(%s)" % (type(self).__name__, ", ".join('%s=%s' % (k, v) for k, v in sorted(flatten_items(self), key=lambda x: x[0])))

    def __call__(self, *args, **kwargs):
        params = setdefaults_path(Struct(), kwargs, **self)
        try:
            target = params.pop('call_target')
        except KeyError:
            raise TypeError('Namespace was used as a function, but no call_target was specified. The namespace is: %s' % self)  # pragma: no mutate
        return target(*args, **params)


# This is just a marker class for declaring shortcuts, and later for collecting them
class Shortcut(Namespace):
    pass


# decorator
def shortcut(f):
    f.shortcut = True
    return f


def is_shortcut(x):
    return isinstance(x, Shortcut) or getattr(x, 'shortcut', False)


def flatten(namespace):
    return dict(flatten_items(namespace))


def flatten_items(namespace):
    def mappings(n, visited=None, prefix=''):
        for key, value in n.items():
            path = prefix + key
            if isinstance(value, Namespace):
                visited = [] if visited is None else visited
                if id(value) not in visited:
                    visited.append(id(value))
                    if value:
                        for mapping in mappings(value, visited=visited, prefix=path + '__'):
                            yield mapping
                    else:
                        yield path, Namespace()
            else:
                yield path, value
    return mappings(namespace)


class FrozenNamespace(Frozen, Namespace):
    pass


EMPTY = FrozenNamespace()


# The first argument has a funky name to avoid name clashes with stuff in kwargs
def setdefaults_path(__target__, *defaults, **kwargs):

    def setdefault(path, value):
        namespace = __target__
        parts = path.split('__')
        for part in parts[:-1]:
            current = namespace.get(part)
            if current is None:
                namespace[part] = Namespace()
            elif not isinstance(current, dict):
                namespace[part] = Namespace(**{current: True})
            else:
                namespace[part] = Namespace(current)
            namespace = namespace[part]
        namespace.setdefault(parts[-1], value)

    for mappings in list(defaults) + [kwargs]:
        for path, value in sorted(mappings.items(), key=lambda x: len(x[0])):
            if not type(value) == Namespace:
                setdefault(path, value)
            else:
                if value:
                    for path2, value in flatten(value).items():
                        setdefault('__'.join((path, path2)), value)
                else:
                    setdefault(path, Namespace())
    return __target__


def dispatch(*function, **defaults):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **setdefaults_path(Namespace(), kwargs, defaults))
        wrapper.dispatch = Namespace(defaults)  # we store these here so we can inspect them for stuff like documentation
        return wrapper

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

    to_be_moved_by_index = sorted(to_be_moved_by_index, key=lambda x: x.after)

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
        raise KeyError('Tried to order after %s but %s not exist' % (', '.join(sorted(to_be_moved_by_name.keys())), 'that key does' if len(to_be_moved_by_name) == 1 else 'those keys do'))

    return result


def assert_kwargs_empty(kwargs):
    if kwargs:
        import traceback
        function_name = traceback.extract_stack()[-2][2]
        raise TypeError('%s() got unexpected keyword arguments %s' % (function_name, ', '.join(["'%s'" % x for x in sorted(kwargs.keys())])))


def full_function_name(f):
    return '%s.%s' % (f.__module__, f.__name__)


def get_shortcuts_by_name(class_):
    def sorting_order_is_irrelevant(_):
        return 0  # pragma: no mutate
    decorated_class = declarative(member_class=Shortcut, is_member=is_shortcut, sort_key=sorting_order_is_irrelevant)(class_)
    return dict(decorated_class.get_declared())


@creation_ordered
class Refinable(object):
    pass


# decorator
def refinable(f):
    f.refinable = True
    # noinspection PyProtectedMember
    f._index = Refinable()._index
    return f


def is_refinable_function(attr):
    return getattr(attr, 'refinable', False)


@declarative(
    member_class=Refinable,
    parameter='refinable_members',
    is_member=is_refinable_function,
    add_init_kwargs=False,
)
class RefinableObject(object):
    # This constructor assumes that the class that inherits from RefinableObject
    # has done any attribute assignments to self BEFORE calling super(...)
    @dispatch()
    def __init__(self, **kwargs):
        for k, v in self.get_declared('refinable_members').items():
            if isinstance(v, Refinable):
                setattr(self, k, kwargs.pop(k, None))
            else:
                if k in kwargs:
                    setattr(self, k, kwargs.pop(k))

        if kwargs:
            raise TypeError("'%s' object has no refinable attribute(s): %s" % (self.__class__.__name__, ', '.join(sorted(kwargs.keys()))))

        super(RefinableObject, self).__init__()
