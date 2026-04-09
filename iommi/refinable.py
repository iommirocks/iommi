import warnings
from copy import copy
from enum import auto, \
    Enum
from typing import (
    Any,
    List,
    Tuple,
)

from iommi.base import items
from iommi.declarative import declarative
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    getattr_path,
    Namespace,
)
from iommi.declarative.with_meta import (
    get_meta,
    get_meta_flat,
)
from iommi.evaluate import get_signature


def prefixes(path):
    """
    Given a path which contains components separated by double underscores,
    return the path prefixes of increasing length (up to and including
    the full path).

    Example:

    .. code-block:: pycon

        >>> list(prefixes("foo__bar__baz__quux"))
        ['foo', 'foo__bar', 'foo__bar__baz', 'foo__bar__baz__quux']
    """
    parts = [p for p in path.split('__') if p]
    for i in range(len(parts)):
        yield '__'.join(parts[: i + 1])


class Prio(Enum):
    """
    Determines the order of priority in which refinement of attributes is performed.
    """

    refine_defaults = auto()
    table_defaults = auto()
    member_defaults = auto()
    constructor = auto()
    shortcut = auto()
    style = auto()
    meta = auto()
    base = auto()
    member = auto()
    refine = auto()


def flatten_items(namespace, _prefix=''):
    for key, value in dict.items(namespace):
        path = _prefix + key
        if isinstance(value, Namespace):
            if value:
                yield from flatten_items(value, _prefix=path + '__')
            else:
                yield path, value
        else:
            yield path, value


class RefinableNamespace(Namespace):
    __iommi_refined_stack: List[Tuple[Prio, Namespace, List[Tuple[str, Any]]]]

    def _get_resolved(self):
        # shim: RefinableNamespace IS already a resolved dict
        return self

    def set(self, key, value):
        # shim: RefinableNamespace is a dict, so plain assignment works
        self[key] = value

    def print_origin(self, refinable_name):
        for prio, params in self.as_stack():
            if refinable_name in params:
                print(prio, params[refinable_name])

    def as_stack(self):
        return [(prio.name, dict(flattened_params)) for prio, _, flattened_params in self._get_parent_stack()]

    def _get_parent_stack(self):
        try:
            return object.__getattribute__(self, '__iommi_refined_stack')
        except AttributeError:
            return [
                (Prio.base, self, list(flatten_items(self))),
            ]

    def _refine(self, prio: Prio, **kwargs):
        params = Namespace(**kwargs)

        stack = self._get_parent_stack() + [
            (prio, params, list(flatten_items(params))),
        ]
        stack.sort(key=lambda x: x[0].value)

        result = RefinableNamespace()
        object.__setattr__(result, '__iommi_refined_stack', stack)

        missing = object()

        for prio, params, flattened_params in stack:
            for path, value in flattened_params:
                found = False
                for prefix in prefixes(path):
                    existing = getattr_path(result, prefix, missing)
                    if existing is missing:
                        break
                    new_updates = getattr_path(params, prefix)

                    if isinstance(existing, RefinableObject):
                        if isinstance(new_updates, dict):
                            existing = existing.refine(prio, **new_updates)
                        else:
                            existing = new_updates
                        result.setitem_path(prefix, existing)
                        found = True

                    if isinstance(new_updates, RefinableObject):
                        result.setitem_path(prefix, new_updates)
                        found = True

                if not found:
                    result.setitem_path(path, value)

        return result


class RefinableStack:
    """
    Stores a refinement stack and lazily resolves it to a Namespace on first
    dict-like access. Does not inherit from Namespace or dict.

    Public interface: .get(), .keys(), .set(), __contains__, as_stack(),
    print_origin(), _refine().
    """

    def __init__(self, **kwargs):
        if kwargs:
            ns = Namespace(**kwargs)
            object.__setattr__(self, '_stack', [(Prio.base, ns, list(flatten_items(ns)))])
        else:
            object.__setattr__(self, '_stack', [])
        object.__setattr__(self, '_resolved', None)

    def _get_parent_stack(self):
        return object.__getattribute__(self, '_stack')

    def _get_resolved(self):
        resolved = object.__getattribute__(self, '_resolved')
        if resolved is None:
            resolved = self._build_resolved()
            object.__setattr__(self, '_resolved', resolved)
        return resolved

    def _build_resolved(self):
        """Merge the stack into a single Namespace. Called at most once."""
        # Note: RefinableObject is defined later in this module. Python resolves
        # names at call time, so the isinstance checks below work correctly.
        stack = self._get_parent_stack()
        result = Namespace()
        missing = object()

        for prio, params, flattened_params in stack:
            for path, value in flattened_params:
                found = False
                for prefix in prefixes(path):
                    existing = getattr_path(result, prefix, missing)
                    if existing is missing:
                        break
                    new_updates = getattr_path(params, prefix)

                    if isinstance(existing, RefinableObject):
                        if isinstance(new_updates, dict):
                            existing = existing.refine(prio, **new_updates)
                        else:
                            existing = new_updates
                        result.setitem_path(prefix, existing)
                        found = True

                    if isinstance(new_updates, RefinableObject):
                        result.setitem_path(prefix, new_updates)
                        found = True

                if not found:
                    result.setitem_path(path, value)

        return result

    def _refine(self, prio: Prio, **kwargs):
        params = Namespace(**kwargs)
        stack = self._get_parent_stack() + [(prio, params, list(flatten_items(params)))]
        stack.sort(key=lambda x: x[0].value)
        result = object.__new__(RefinableStack)
        object.__setattr__(result, '_stack', stack)
        object.__setattr__(result, '_resolved', None)
        return result

    # --- Public value access ---

    def get(self, key, default=None):
        return self._get_resolved().get(key, default)

    def keys(self):
        return self._get_resolved().keys()

    def set(self, key, value):
        """Mutate the resolved namespace directly. Only for use in on_refine_done hooks.

        Note: this bypasses the stack, so as_stack() and print_origin() will not
        reflect values set this way.
        """
        self._get_resolved()[key] = value

    def __contains__(self, key):
        return key in self._get_resolved()

    def __getattr__(self, key):
        # Delegate attribute access to the resolved namespace.
        # object.__getattribute__ is used for _stack and _resolved to avoid recursion.
        try:
            resolved = object.__getattribute__(self, '_resolved')
        except AttributeError:
            raise AttributeError(key)
        if resolved is None:
            resolved = self._build_resolved()
            object.__setattr__(self, '_resolved', resolved)
        try:
            return getattr(resolved, key)
        except AttributeError:
            raise AttributeError(f"'RefinableStack' object has no attribute '{key}'")

    def __eq__(self, other):
        resolved = self._get_resolved()
        if isinstance(other, RefinableStack):
            return resolved == other._get_resolved()
        return resolved == other

    def __repr__(self):
        return repr(self._get_resolved())

    # --- Stack inspection ---

    def as_stack(self):
        return [(prio.name, dict(flattened_params)) for prio, _, flattened_params in self._get_parent_stack()]

    def print_origin(self, refinable_name):
        for prio, params in self.as_stack():
            if refinable_name in params:
                print(prio, params[refinable_name])


# Backward-compat alias — old class body will be removed in the next task
RefinableNamespace = RefinableStack


class Refinable:
    def __str__(self):
        # Prevent non-defined string conversion ending up in templates
        assert False


# decorator
def refinable(f):
    f.refinable = True
    return f


def is_refinable_function(attr):
    return getattr(attr, 'refinable', False)


class EvaluatedRefinable(Refinable):
    pass


def evaluated_refinable(f):
    f = refinable(f)
    f.__iommi__evaluated = True
    return f


def is_evaluated_refinable(x):
    return isinstance(x, EvaluatedRefinable) or getattr(x, '__iommi__evaluated', False)


_get_evaluated_attributes_cache = {}


def get_evaluated_attributes(result):
    class_ = type(result)
    try:
        return _get_evaluated_attributes_cache[class_]
    except KeyError:
        r = [k for k, v in items(result.get_declared('refinable')) if is_evaluated_refinable(v)]
        _get_evaluated_attributes_cache[class_] = r
        return r


class SpecialEvaluatedRefinable(Refinable):
    pass


def special_evaluated_refinable(f):
    f = refinable(f)
    f.__iommi__special_evaluated = True
    return f


def is_special_evaluated_refinable(x):
    return isinstance(x, SpecialEvaluatedRefinable) or getattr(x, '__iommi__special_evaluated', False)


_get_special_evaluated_attributes_cache = {}


def get_special_evaluated_attributes(result):
    class_ = type(result)
    try:
        return _get_special_evaluated_attributes_cache[class_]
    except KeyError:
        r = [k for k, v in items(result.get_declared('refinable')) if is_special_evaluated_refinable(v)]
        _get_special_evaluated_attributes_cache[class_] = r
        return r


class RefinableMembers(Refinable):
    pass


@declarative(
    member_class=Refinable,
    parameter='refinable',
    is_member=is_refinable_function,
    add_init_kwargs=False,
)
class RefinableObject:
    iommi_namespace: RefinableStack
    is_refine_done: bool

    @dispatch
    def __init__(self, **kwargs):
        self.is_refine_done = False
        self.iommi_namespace = RefinableStack(**kwargs)
        declared_items = self.get_declared('refinable')
        unknown_args = [name for name in kwargs if name not in declared_items]
        if unknown_args:
            available_keys = '\n    '.join(sorted(declared_items.keys()))
            raise TypeError(
                f'{self.__class__.__name__} object has no refinable attribute(s): '
                + ', '.join(f'"{k}"' for k in sorted(unknown_args))
                + '.\n'
                + 'Available attributes:\n    '
                + available_keys
                + '\n'
            )

    @classmethod
    def get_meta(cls):
        return get_meta(cls)

    @classmethod
    def get_meta_flat(cls):
        return get_meta_flat(cls)

    def refine_done(self, parent=None):
        result = copy(self)
        del self

        assert not result.is_refine_done, f"refine_done() already invoked on {result!r}"

        meta_params = result.get_meta()
        if meta_params:
            if getattr(result, '__iommi_with_meta', False):
                warnings.warn(
                    f'RefinableObject {result.__class__} should not merge class Meta attributes into the constructor invocation. '
                    f'Drop @with_meta decorator.'
                )
            result.iommi_namespace = result.iommi_namespace._refine(Prio.meta, **meta_params)

        if hasattr(result, 'apply_style'):
            is_root = parent is None
            enclosing_style = None if is_root else parent.iommi_style
            iommi_style = result.iommi_namespace.get('iommi_style')

            from iommi.style import resolve_style

            iommi_style = resolve_style(iommi_style, enclosing_style=enclosing_style)
            result = result.apply_style(iommi_style, is_root=is_root)

        # Apply config from result.namespace to result
        declared_items = result.get_declared('refinable')
        remaining_namespace = {k: result.iommi_namespace.get(k) for k in result.iommi_namespace.keys()}
        for k, v in items(declared_items):
            if k == 'iommi_style':
                remaining_namespace.pop(k, None)
                continue
            if isinstance(v, Refinable):
                setattr(result, k, remaining_namespace.pop(k, None))
            else:
                if k in remaining_namespace:
                    setattr(result, k, remaining_namespace.pop(k))

        if remaining_namespace:
            unknown_args = list(remaining_namespace.keys())
            available_keys = '\n    '.join(sorted(declared_items.keys()))
            raise TypeError(
                f'{result.__class__.__name__} object has no refinable attribute(s): '
                + ', '.join(f'"{k}"' for k in sorted(unknown_args))
                + '.\n'
                + 'Available attributes:\n    '
                + available_keys
                + '\n'
            )
        result.is_refine_done = True

        result.on_refine_done()

        # dict instead of set() to respect order
        refinables_dynamic = dict()
        for k in get_evaluated_attributes(result):
            v = getattr(result, k)
            if callable(v):
                get_signature(v)  # warm the signature cache
                refinables_dynamic[k] = True
        result._refinables_dynamic = refinables_dynamic
        return result

    def on_refine_done(self):
        pass

    def refine(self, prio: Prio = Prio.refine, **kwargs):
        assert not self.is_refine_done, f"Already called refine_done on {self!r}"
        if prio == Prio.constructor:
            # Inplace
            result = self
        else:
            result = copy(self)

        result.iommi_namespace = self.iommi_namespace._refine(prio, **kwargs)

        return result

    def refine_defaults(self, **kwargs):
        return self.refine(Prio.refine_defaults, **kwargs)

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} " + ' '.join(f'{k}={v}' for k, v in flatten_items(self.iommi_namespace._get_resolved())) + ">"
        )
