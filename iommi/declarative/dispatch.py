import functools

from .namespace import Namespace


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
