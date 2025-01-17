import inspect

from iommi.base import (
    items,
    keys,
)
from iommi.declarative.namespace import (
    Namespace,
    func_from_namespace,
)

_matches_cache = {}
_use_cache = True


def matches(caller_parameters, callee_parameters, __match_empty=False):
    cache_key = ';'.join((caller_parameters, callee_parameters, str(int(__match_empty))))  # pragma: no mutate
    # (mutation changes this to cached_value = None, which just slows down the code)
    global _use_cache
    if _use_cache:
        cached_value = _matches_cache.get(cache_key, None)  # pragma: no mutate
        if cached_value is not None:
            return cached_value

    caller = set(caller_parameters.split(',')) if caller_parameters else set()

    a, b, c = callee_parameters.split('|')
    required = set(a.split(',')) if a else set()
    optional = set(b.split(',')) if b else set()
    wildcard = c == '*'

    if not __match_empty and not required and not optional and wildcard:
        result = False  # Special case to not match no-specification function "lambda **whatever: ..."
    else:
        if wildcard:
            result = caller >= required
        else:
            result = required <= caller <= required.union(optional)

    _matches_cache[cache_key] = (
        result  # pragma: no mutate (mutation changes result to None which just makes things slower)
    )
    return result


def get_callable_description(c):
    if getattr(c, '__name__', None) == '<lambda>':
        import inspect

        try:
            return 'lambda found at: `{}`'.format(inspect.getsource(c).strip())
        except OSError:  # pragma: no cover
            pass
    if isinstance(c, Namespace):
        return f'`{c}`'
    return f'{c.__module__}.{c.__name__}'


def is_callable(v):
    if isinstance(v, Namespace) and 'call_target' not in v:
        return False
    else:
        return callable(v)


def evaluate(func_or_value, *, __signature=None, __strict=False, __match_empty=True, **kwargs):
    if is_callable(func_or_value):
        if __signature is None:
            __signature = signature_from_kwargs(kwargs)

        callee_parameters = get_signature(func_or_value)
        if callee_parameters is not None and matches(__signature, callee_parameters, __match_empty):
            return func_or_value(**kwargs)

        if __strict:
            arguments = '\n        '.join(keys(kwargs))
            parameters = '\n        '.join(inspect.getfullargspec(func_or_value)[0])
            assert isinstance(func_or_value, Namespace) and 'call_target' not in func_or_value, (
f'''Evaluating {get_callable_description(func_or_value)} didn't resolve it into a value but strict mode was active. The signature doesn't match the given parameters.

    Possible inputs:
        {arguments}

    Function inputs:
        {parameters}
''')
    return func_or_value


def evaluate_strict(__func_or_value, *, __signature=None, __match_empty=True, **kwargs):
    # noinspection PyArgumentEqualDefault
    return evaluate(__func_or_value, __signature=None, __strict=True, __match_empty=__match_empty, **kwargs)


def get_signature(func):
    """
    :type func: Callable
    :rtype: str
    """
    try:
        return object.__getattribute__(func, '__iommi_declarative_signature')
    except AttributeError:
        pass

    if isinstance(func, Namespace):
        func = func_from_namespace(func)

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
        object.__setattr__(func, '__iommi_declarative_signature', signature)
    except TypeError:
        # For classes
        type.__setattr__(func, '__iommi_declarative_signature', signature)
    except AttributeError:
        pass
    return signature


def signature_from_kwargs(kwargs):
    return ','.join(sorted(keys(kwargs)))


def evaluate_members(obj, **kwargs):
    for key in obj._refinables_dynamic:
        evaluate_member(obj, key, **kwargs)


def evaluate_member(__obj, __key, __strict=True, **kwargs):
    value = getattr(__obj, __key)
    new_value = evaluate(value, __strict=__strict, __signature=signature_from_kwargs(kwargs), **kwargs)
    if new_value is not value:
        setattr(__obj, __key, new_value)


def find_static_items(d):
    if d and isinstance(d, Namespace):
        object.__setattr__(d, '_static_items', {k for k, v in items(d) if not callable(v)})


def find_static_items_recursively(d):
    if d and isinstance(d, Namespace):
        find_static_items(d)
        for k, v in items(d):
            if isinstance(v, Namespace):
                find_static_items_recursively(v)


def evaluate_as_needed(d, kwargs, ignore=()):
    static_items = getattr(d, '_static_items', [])
    return {k: d[k] if k in static_items else evaluate_strict(v, **kwargs) for k, v in items(d) if k not in ignore}


def evaluate_as_needed_recursively(d, kwargs, ignore=()):
    static_items = getattr(d, '_static_items', [])

    def value(k, v):
        if k in static_items:
            return d[k]
        if isinstance(v, Namespace):
            return evaluate_as_needed_recursively(v, kwargs, ignore)
        return evaluate_strict(v, **kwargs)

    return Namespace({
        k: value(k, v)
        for k, v in items(d) if k not in ignore
    })


def has_catch_all_kwargs(callback):
    return get_signature(callback).endswith('|*')
