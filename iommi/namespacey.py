from copy import copy

from tri_declarative import (
    declarative,
    flatten,
    Namespace,
    Refinable,
)
from tri_declarative.refinable import is_refinable_function

from iommi.base import items


class RefinedNamespace(Namespace):
    __iommi_refined_description: str
    __iommi_refined_parent: Namespace
    __iommi_refined_delta: Namespace
    __iommi_refined_defaults: bool

    def __init__(self, description, parent, defaults=False, *args, **kwargs):
        delta = Namespace(*args, **kwargs)
        object.__setattr__(self, '__iommi_refined_description', description)
        object.__setattr__(self, '__iommi_refined_parent', parent)
        object.__setattr__(self, '__iommi_refined_delta', delta)
        object.__setattr__(self, '__iommi_refined_defaults', defaults)
        if defaults:
            super().__init__(delta, parent)
        else:
            super().__init__(parent, delta)

    def as_stack(self):
        refinements = []
        default_refinements = []
        node = self

        while isinstance(node, RefinedNamespace):
            try:
                description = object.__getattribute__(node, '__iommi_refined_description')
                parent = object.__getattribute__(node, '__iommi_refined_parent')
                delta = object.__getattribute__(node, '__iommi_refined_delta')
                defaults = object.__getattribute__(node, '__iommi_refined_defaults')
                value = (description, flatten(delta))
                if defaults:
                    default_refinements = default_refinements + [value]
                else:
                    refinements = [value] + refinements
                node = parent
            except AttributeError:
                break

        return default_refinements + [('base', flatten(node))] + refinements


@declarative(
    member_class=Refinable,
    parameter='refinable_members',
    is_member=is_refinable_function,
    add_init_kwargs=False,
)
class Namespacey:
    namespace: Namespace
    finalized: bool

    def __init__(self, namespace=None, **kwargs):
        if namespace is None:
            namespace = Namespace()
        else:
            namespace = Namespace(namespace)

        declared_items = self.get_declared('refinable_members')
        for name in list(kwargs):
            prefix, _, _ = name.partition('__')
            if prefix in declared_items:
                namespace.setitem_path(name, kwargs.pop(name))

        self.namespace = namespace
        self.finalized = False

    def finalize(self):
        assert not self.finalized, f"{self} already finalized"

        declared_items = self.get_declared('refinable_members')
        remaining_namespace = Namespace(self.namespace)
        for k, v in items(declared_items):
            if isinstance(v, Refinable):
                setattr(self, k, remaining_namespace.pop(k, None))
            else:
                if k in remaining_namespace:
                    setattr(self, k, remaining_namespace.pop(k))

        if remaining_namespace:
            available_keys = '\n    '.join(sorted(declared_items.keys()))
            raise TypeError(
                f"""\
'{self.__class__.__name__}' object has no refinable attribute(s): {', '.join(sorted(remaining_namespace.keys()))}.
Available attributes:
    {available_keys}
""")

        self.finalized = True

        self.on_finalize()

        return self

    def on_finalize(self):
        pass

    def refine(self, **args):
        assert not self.finalized, f"{self} already finalized"
        result = copy(self)
        result.namespace = RefinedNamespace('refine', self.namespace, **args)
        return result

    def refine_defaults(self, **args):
        assert not self.finalized, f"{self} already finalized"
        result = copy(self)
        result.namespace = RefinedNamespace('refine defaults', self.namespace, defaults=True, **args)
        return result
