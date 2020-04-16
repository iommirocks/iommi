import functools

from .dispatch import dispatch
from .namespace import Namespace
from .util import setdefaults_path


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
        @functools.wraps(__target__)
        @shortcut
        @dispatch(
            **defaults
        )
        def class_shortcut_wrapper(cls, *args, **kwargs):
            name = __target__.__name__
            next_call_target = kwargs.pop('call_target', None)

            if (
                isinstance(next_call_target, Namespace)
                and name == next_call_target.get('attribute', None)
            ):
                # Next call is to the same attribute name, but on the base class.
                initial_resolve = getattr(cls, name).__func__
                # Loop until we find a super class implementation
                base_class_candidate = cls
                while getattr(base_class_candidate, name).__func__ == initial_resolve:
                    base_class_candidate = base_class_candidate.__bases__[0]

                next_call_target_cls = base_class_candidate
                next_call_target_attribute = next_call_target.attribute

                # We need to retain the cls value for later use (as _final_cls).
                setdefaults_path(kwargs, _final_cls=cls)

                call_target_after_shortcut = Namespace(
                    call_target__cls=next_call_target_cls,
                    call_target__attribute=next_call_target_attribute,
                )

            else:
                next_call_target_cls = kwargs.pop('_final_cls', cls)
                if next_call_target is None:
                    # No call_target specified in the decorator, just use the cls (or _final_cls from earlier)
                    call_target_after_shortcut = Namespace(
                        call_target__cls=next_call_target_cls,
                    )
                else:
                    # Merge decorator specified call_target with what final class we should have.
                    call_target_after_shortcut = Namespace(
                        call_target=next_call_target,
                        call_target__cls=next_call_target_cls,
                    )

            result = __target__(cls, *args, call_target=call_target_after_shortcut, **kwargs)

            shortcut_stack = [name] + getattr(result, '__tri_declarative_shortcut_stack', [])
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
