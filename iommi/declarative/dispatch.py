import functools

from .namespace import (
    EMPTY,
    Namespace,
)


def dispatch(*function, **defaults):
    def decorator(f):
        if defaults:

            @functools.wraps(f)
            def dispatch_defaults_wrapper(*args, **kwargs):
                return f(*args, **Namespace(defaults, kwargs))

        else:

            @functools.wraps(f)
            def dispatch_defaults_wrapper(*args, **kwargs):
                # Without defaults, a Namespace only differs from kwargs if there are paths or EMPTY values
                for key, value in dict.items(kwargs):
                    if '__' in key or value is EMPTY:
                        return f(*args, **Namespace(kwargs))
                return f(*args, **kwargs)

        dispatch_defaults_wrapper.dispatch = Namespace(
            defaults
        )  # we store these here so we can inspect them for stuff like documentation
        return dispatch_defaults_wrapper

    if function:
        assert len(function) == 1
        return decorator(function[0])

    return decorator
