from copy import copy
from typing import (
    Type,
    TypeVar,
)

from .util import (
    add_args_to_init_call,
    add_init_call_hook,
)

T = TypeVar("T")


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
        raise TypeError(
            "The @declarative decorator needs either a member_class parameter or an is_member check function (or both)"
        )

    def decorator(class_to_decorate: Type[T]) -> Type[T]:
        class DeclarativeMeta(class_to_decorate.__class__):  # type:ignore
            # noinspection PyTypeChecker,PyMethodParameters
            def __init__(cls, name, bases, dict_):  # noqa: N805
                members = get_members(
                    cls, member_class=member_class, is_member=is_member, sort_key=sort_key, _parameter=parameter
                )
                set_declared(cls, members, parameter)
                super(DeclarativeMeta, cls).__init__(name, bases, dict_)

        new_class = DeclarativeMeta(
            class_to_decorate.__name__,
            class_to_decorate.__bases__,
            {k: v for k, v in class_to_decorate.__dict__.items() if k not in ['__dict__', '__weakref__']},
        )

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


# noinspection PyIncorrectDocstring
def get_members(cls, member_class=None, is_member=None, sort_key=None, _parameter=None):
    """
    Collect all class level attributes matching the given criteria.

    :param cls: Class to traverse
    :param class member_class: Class(es) to collect
    :param is_member: Function to determine if an object should be collected
    :param sort_key: Function to invoke on members to obtain ordering (Default is to use ordering from `creation_ordered`)

    :type is_member: (object) -> bool
    :type sort_key: (object) -> object
    """
    if member_class is None and is_member is None:
        raise TypeError("get_members either needs a member_class parameter or an is_member check function (or both)")

    members = {}
    for base in cls.__bases__:
        if _parameter is None:
            inherited_members = get_members(base, member_class=member_class, is_member=is_member, sort_key=sort_key)
        else:
            # When user by @declarative, only traverse up the class inheritance to the decorated class.
            inherited_members = get_declared(base, _parameter)
        members.update(inherited_members)

    def generate_member_bindings():
        def is_a_member(maybe_member):
            return (member_class is not None and isinstance(maybe_member, member_class)) or (
                is_member is not None and is_member(maybe_member)
            )

        for name in cls.__dict__:
            if name.startswith('__'):
                continue
            obj = getattr(cls, name)
            if is_a_member(obj):
                yield name, obj
            elif type(obj) is tuple and len(obj) == 1 and is_a_member(obj[0]):
                raise TypeError(
                    f"'{name}' is a one-tuple containing what we are looking for.  Trailing comma much?  Don't... just don't."
                )  # pragma: no mutate

    bindings = generate_member_bindings()

    if sort_key is not None:
        sorted_bindings = sorted(bindings, key=lambda x: sort_key(x[1]))
        members.update(sorted_bindings)
    else:
        members.update(bindings)

    return members
