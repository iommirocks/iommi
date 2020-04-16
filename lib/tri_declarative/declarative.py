from copy import copy

from .util import (
    add_args_to_init_call,
    add_init_call_hook,
    get_members,
)


def declarative(member_class=None, parameter='members', add_init_kwargs=True, sort_key=None, is_member=None):
    """
        Class decorator to enable classes to be defined in the style of django models.
        That is, @declarative classes will get an additional argument to constructor,
        containing a dict with all class members matching the specified type.

        :param class member_class: Class(es) to collect
        :param is_member: Function to determine if an object should be collected
        :param str parameter: Name of constructor parameter to inject
        :param bool add_init_kwargs: If constructor parameter should be injected (Default: True)
        :param sort_key: Function to invoke on members to obtain ordering (Default is to use ordering from `creation_ordered`)

        :type is_member: (object) -> bool
        :type sort_key: (object) -> object
    """
    if member_class is None and is_member is None:
        raise TypeError("The @declarative decorator needs either a member_class parameter or an is_member check function (or both)")

    def decorator(class_to_decorate):
        class DeclarativeMeta(class_to_decorate.__class__):
            # noinspection PyTypeChecker
            def __init__(cls, name, bases, dict):
                members = get_members(cls, member_class=member_class, is_member=is_member, sort_key=sort_key, _parameter=parameter)
                set_declared(cls, members, parameter)
                super(DeclarativeMeta, cls).__init__(name, bases, dict)

        new_class = DeclarativeMeta(class_to_decorate.__name__,
                                    class_to_decorate.__bases__,
                                    {k: v for k, v in class_to_decorate.__dict__.items() if k not in ['__dict__', '__weakref__']})

        def get_extra_args_function(self):
            declared = get_declared(self, parameter)
            copied_members = {k: copy(v) for k, v in declared.items()}
            self.__dict__.update(copied_members)
            return {parameter: copied_members}

        if add_init_kwargs:
            add_args_to_init_call(new_class, get_extra_args_function)
        else:
            add_init_call_hook(new_class, get_extra_args_function)

        setattr(new_class, 'get_declared', classmethod(get_declared))
        setattr(new_class, 'set_declared', classmethod(set_declared))

        return new_class

    return decorator


def set_declared(cls, value, parameter='members'):
    """
        :type cls: class
        :type value: dict
        :type parameter: str
    """

    setattr(cls, '_declarative_' + parameter, value)


def get_declared(cls, parameter='members'):
    """
        Get the :code:`dict` value of the parameter collected by the :code:`@declarative` class decorator.
        This is the same value that would be submitted to the :code:`__init__` invocation in the :code:`members`
        argument (or another name if overridden by the :code:`parameter` specification)

        :type cls: class
        :type parameter: str
        :rtype: dict
    """

    return getattr(cls, '_declarative_' + parameter, {})
