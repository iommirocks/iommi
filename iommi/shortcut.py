import functools

from iommi.declarative import get_members
from iommi.declarative.namespace import Namespace
from iommi.refinable import Prio


# This is just a marker class for declaring shortcuts, and later for collecting them
class Shortcut(Namespace):
    shortcut = True


# decorator
def shortcut(f):
    f.shortcut = True
    return f


def is_shortcut(x):
    return getattr(x, 'shortcut', False)


def get_shortcuts_by_name(class_):
    return dict(get_members(class_, member_class=Shortcut, is_member=is_shortcut))


def with_defaults(__target__=None, **decorator_kwargs):
    def decorator(__target__):
        @functools.wraps(__target__)
        @shortcut
        def wrapper_for_with_defaults(*args, **kwargs):
            instance = __target__(*args, **kwargs)

            name = __target__.__name__
            if name == '__init__':
                args[0].refine(Prio.constructor, **decorator_kwargs)
            else:
                if decorator_kwargs:
                    instance = instance.refine(
                        Prio.shortcut,
                        **decorator_kwargs,
                    )

                shortcut_stack = [name] + getattr(instance, 'iommi_shortcut_stack', [])
                try:
                    instance.iommi_shortcut_stack = shortcut_stack
                except AttributeError:
                    pass

            return instance

        wrapper_for_with_defaults.__iommi_with_defaults_kwargs = decorator_kwargs
        return wrapper_for_with_defaults

    if __target__ is not None:
        return decorator(__target__)

    return decorator


def superinvoking_classmethod(f):
    @functools.wraps(f)
    def wrapper_for_superinvoking_classmethod(cls, *args, **kwargs):
        def super_classmethod_invoker(*args, **kwargs):
            parent_classmethod = None
            for parent_class in list(cls.mro())[1:]:
                candidate = vars(parent_class).get(f.__name__)
                if candidate is not None:
                    if parent_classmethod is None:
                        parent_classmethod = candidate
                    if candidate.__func__ == wrapper_for_superinvoking_classmethod:
                        # Infinite loop avoidance, we found ourselves.
                        parent_classmethod = None

            if parent_classmethod is None:
                raise TypeError(f'Unable to find parent class implementation of {cls.__name__}:{f.__name__}')

            undecorated_parent = parent_classmethod.__func__
            return undecorated_parent(cls, *args, **kwargs)

        return f(cls, *args, super_classmethod=super_classmethod_invoker, **kwargs)

    return wrapper_for_superinvoking_classmethod
