import functools

from iommi.declarative.namespace import Namespace
from iommi.declarative.util import add_args_to_init_call
from iommi.struct import Struct


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
    setattr(class_to_decorate, 'get_meta_flat', classmethod(get_meta_flat))
    setattr(class_to_decorate, '__iommi_with_meta', True)
    setattr(class_to_decorate, '__iommi_with_meta_add_init_kwargs', add_init_kwargs)

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
            for meta_class_ in reversed(class_.Meta.mro()):
                for key in meta_class_.__dict__:
                    if not key.startswith('__'):
                        value = getattr(class_.Meta, key)
                        merged_attributes.setitem_path(key, value)
    return merged_attributes


def get_meta_flat(cls):
    attributes = Struct()
    for class_ in reversed(cls.mro()):
        if hasattr(class_, 'Meta'):
            for meta_class_ in reversed(class_.Meta.mro()):
                for key in meta_class_.__dict__:
                    if not key.startswith('__'):
                        value = getattr(class_.Meta, key)
                        attributes[key] = value

    return attributes
