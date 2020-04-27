import inspect

from .namespace import Namespace

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
    # noinspection PyArgumentEqualDefault
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
    # noinspection PyArgumentEqualDefault
    return evaluate_recursive(func_or_value, __signature=None, __strict=True, **kwargs)


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
