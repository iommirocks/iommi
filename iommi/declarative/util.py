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

    if merge_namespaces:
        new_kwargs = Namespace(new_kwargs, kwargs)
    else:
        new_kwargs.update(kwargs)

    return new_args, new_kwargs


def strip_prefix(s, *, prefix, strict=False):
    if s.startswith(prefix):
        return s[len(prefix) :]
    assert strict is False, f"String '{s}' does not start with prefix '{prefix}'"
    return s
