from collections import OrderedDict
import functools
from functools import total_ordering, wraps
import inspect
import itertools

from tri.struct import Struct


__version__ = '0.4.0'


def with_meta(class_to_decorate=None, add_init_kwargs=True):
    """
    Class decorator to enable a class (and it's sub-classes) to have a 'Meta' class attribute.
    """

    if class_to_decorate is None:
        return functools.partial(with_meta, add_init_kwargs=add_init_kwargs)

    if 'Meta' not in class_to_decorate.__dict__:
        blank_meta = type('Meta', (object, ), {})
        setattr(class_to_decorate, 'Meta', blank_meta)

    if add_init_kwargs:
        __init__orig = class_to_decorate.__init__

        try:
            pos_arg_names, _, _, _ = inspect.getargspec(__init__orig)
            pos_arg_names = list(pos_arg_names)[1:]  # Skip 'self'
        except TypeError:
            # We might fail on not being able to find the signature of builtin constructors
            pos_arg_names = None

        def __init__(self, *args, **kwargs):
            new_kwargs = {}
            new_kwargs.update((k, v) for k, v in self.get_meta().items() if not k.startswith('_'))
            if pos_arg_names is not None:
                if len(args) > len(pos_arg_names):
                    raise TypeError('Too many positional argument')
                new_kwargs.update((k, v) for k, v in zip(pos_arg_names, args))
                args = []
            new_kwargs.update(kwargs)
            __init__orig(self, *args, **new_kwargs)

        setattr(class_to_decorate, '__init__', __init__)

    def get_meta(cls):
        merged_attributes = Struct()
        for class_ in reversed(cls.mro()):
            if hasattr(class_, 'Meta'):
                for key, value in class_.Meta.__dict__.items():
                    if key.startswith('__'):  # Skip internal attributes
                        continue
                    merged_attributes[key] = value
        return merged_attributes

    setattr(class_to_decorate, 'get_meta', classmethod(get_meta))

    return class_to_decorate


def creation_ordered(class_to_decorate):
    """
        Class decorator that ensures that instances will be ordered after creation order when sorted.
    """

    next_index = functools.partial(next, itertools.count())

    __init__orig = class_to_decorate.__init__

    def __init__(self, *args, **kwargs):
        object.__setattr__(self, '_index', next_index())
        __init__orig(self, *args, **kwargs)

    setattr(class_to_decorate, '__init__', __init__)

    # noinspection PyProtectedMember
    def __lt__(self, other):
        return self._index < other._index

    setattr(class_to_decorate, '__lt__', __lt__)

    class_to_decorate = total_ordering(class_to_decorate)

    return class_to_decorate


def declarative(member_class, parameter='members', add_init_kwargs=True):
    """
        Class decorator to enable classes to be defined in the style of django models.
        That is, @declarative classes will get an additional argument to constructor,
        containing an OrderedDict with all class members matching the specified type.
    """

    def get_members(cls):
        members = OrderedDict()
        for base in cls.__bases__:
            meta = getattr(base, 'Meta', None)
            if meta is not None:
                inherited_members = getattr(meta, parameter, {})
                members.update(inherited_members)

        def generate_member_bindings():
            for name, obj in cls.__dict__.items():
                if isinstance(obj, member_class) and not name.startswith('__'):
                    yield name, obj

        members.update(sorted(generate_member_bindings(), key=lambda x: x[1]))

        return members

    def decorator(class_to_decorate):

        class DeclarativeMeta(type):
            def __init__(cls, name, bases, dict):
                if 'Meta' not in cls.__dict__:
                    setattr(cls, 'Meta', type('Meta', (object, ), {}))
                setattr(cls.Meta, parameter, get_members(cls))
                super(DeclarativeMeta, cls).__init__(name, bases, dict)

        new_class = DeclarativeMeta(class_to_decorate.__name__,
                                    class_to_decorate.__bases__,
                                    dict(class_to_decorate.__dict__))
        new_class = with_meta(add_init_kwargs=add_init_kwargs)(new_class)
        return new_class

    return decorator


def should_not_evaluate(f):
    if not callable(f):
        return f

    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    wrapper.__evaluate = False
    return wrapper


# Bypass the no_evaluate flag
def should_evaluate(f):
    if not callable(f):
        return f

    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    wrapper.__evaluate = True
    return wrapper


def force_evaluate(f, *args, **kwargs):
    return evaluate(should_evaluate(f), *args, **kwargs)


def evaluate(func_or_value, *args, **kwargs):
    if not getattr(func_or_value, '__evaluate', True):
        return func_or_value
    elif callable(func_or_value):
        return func_or_value(*args, **kwargs)
    else:
        return func_or_value


def evaluate_recursive(func_or_value, *args, **kwargs):
    if isinstance(func_or_value, dict):
        # The type(item)(** stuff is to preserve the original type
        return type(func_or_value)(**{k: evaluate_recursive(v, *args, **kwargs) for k, v in func_or_value.items()})

    if isinstance(func_or_value, list):
        return [evaluate_recursive(v, *args, **kwargs) for v in func_or_value]

    if isinstance(func_or_value, set):
        return {evaluate_recursive(v, *args, **kwargs) for v in func_or_value}

    return evaluate(func_or_value, *args, **kwargs)


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
