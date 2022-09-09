import functools

from .namespace import Namespace
from .util import add_args_to_init_call


def with_meta(class_to_decorate=None, add_init_kwargs=True):
    """
    Class decorator to enable a class (and it's sub-classes) to have a 'Meta' class attribute.

    :type class_to_decorate: class
    :param bool add_init_kwargs: Pass Meta class members to constructor

    :rtype: class
    """

    if class_to_decorate is None:
        return functools.partial(with_meta, add_init_kwargs=add_init_kwargs)

    if add_init_kwargs:

        def get_extra_args_function(self):
            return {k: v for k, v in self.get_meta().items() if not k.startswith('_')}

        add_args_to_init_call(class_to_decorate, get_extra_args_function, True)

    setattr(class_to_decorate, 'get_meta', classmethod(get_meta))

    return class_to_decorate


def get_meta(cls):
    """
    Collect all members of any contained :code:`Meta` class declarations from the given class or any of its base classes.
    (Sub class values take precedence.)

    :type cls: class
    :rtype: Struct
    """
    merged_attributes = Namespace()
    for class_ in reversed(cls.mro()):
        if hasattr(class_, 'Meta'):
            for key in class_.Meta.__dict__:
                if not key.startswith('__'):
                    value = getattr(class_.Meta, key)
                    merged_attributes.setitem_path(key, value)
    return merged_attributes
