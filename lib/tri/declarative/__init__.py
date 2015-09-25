from functools import wraps


__version__ = '0.1.0'


def should_not_evaluate(f):
    if not callable(f):
        return f

    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    wrapper.__evaluate = False
    return wrapper


def should_evaluate(f):
    """
    Bypass the no_evaluate flag
    """
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
