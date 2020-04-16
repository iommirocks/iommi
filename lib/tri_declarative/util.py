import functools
import inspect


def add_args_to_init_call(cls, get_extra_args_function, merge_namespaces=False):
    __init__orig = getattr(cls, '__init__')

    pos_arg_names = getattr(__init__orig, 'pos_arg_names', None)
    if pos_arg_names is None:
        pos_arg_names = inspect.getfullargspec(__init__orig)[0]
        pos_arg_names = list(pos_arg_names)[1:]  # Skip 'self'

    @functools.wraps(__init__orig, assigned=['__doc__'])
    def argument_injector_wrapper(self, *args, **kwargs):
        extra_kwargs = get_extra_args_function(self)
        new_args, new_kwargs = inject_args(args, kwargs, extra_kwargs, pos_arg_names, merge_namespaces)
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


def inject_args(args, kwargs, extra_args, pos_arg_names, merge_namespaces):
    from .namespace import Namespace
    new_kwargs = dict(extra_args)
    if pos_arg_names:
        if len(args) > len(pos_arg_names):
            raise TypeError('Too many positional arguments')
        new_kwargs.update((k, v) for k, v in zip(pos_arg_names, args))
        new_args = []
    else:
        new_args = args

    for k, v in kwargs.items():
        if merge_namespaces and isinstance(new_kwargs.get(k, None), Namespace):
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
            from .declarative import get_declared
            inherited_members = get_declared(base, _parameter)
        members.update(inherited_members)

    def generate_member_bindings():
        def is_a_member(obj):
            return (
                (member_class is not None and isinstance(obj, member_class))
                or (is_member is not None and is_member(obj))
            )

        for name in cls.__dict__:
            if name.startswith('__'):
                continue
            obj = getattr(cls, name)
            if is_a_member(obj):
                yield name, obj
            elif type(obj) is tuple and len(obj) == 1 and is_a_member(obj[0]):
                raise TypeError(f"'{name}' is a one-tuple containing what we are looking for.  Trailing comma much?  Don't... just don't.")  # pragma: no mutate

    bindings = generate_member_bindings()

    if sort_key is not None:
        sorted_bindings = sorted(bindings, key=lambda x: sort_key(x[1]))
        members.update(sorted_bindings)
    else:
        members.update(bindings)

    return members


# The first argument has a funky name to avoid name clashes with stuff in kwargs
def setdefaults_path(__target__, *defaults, **kwargs):
    from .namespace import Namespace
    args = [kwargs] + list(reversed(defaults)) + [__target__]
    dict.update(__target__, Namespace(*args))
    return __target__


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
