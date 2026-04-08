# RefinableStack Design

**Date:** 2026-04-08
**Status:** Approved

## Problem

`RefinableNamespace` currently inherits from `Namespace` (→ `Struct` → `dict`). Every call
to `_refine()` fully rebuilds the resolved nested `Namespace` by replaying all stack entries
through `setitem_path`. Because `_refine()` is called 4–5 times per component (constructor,
optional user `.refine()` calls, meta, style) before `refine_done()` materialises the result,
the expensive merge work is repeated N times even though only the final result matters.

## Goal

Replace `RefinableNamespace` with `RefinableStack` — a class that:

1. Does **not** inherit from `Namespace`/`dict`.
2. Stores only the refinement stack (cheap on each `_refine()` call).
3. Resolves the merged `Namespace` **lazily**, on first dict-like access, and caches it.
4. Exposes a minimal, honest interface: `.get()`, `.keys()`, `.set()`, `__contains__`.
5. Keeps the existing stack-inspection API: `as_stack()`, `print_origin()`.

## Interface

```python
class RefinableStack:
    # Stack API (unchanged semantics)
    def as_stack(self) -> list: ...
    def print_origin(self, refinable_name: str) -> None: ...

    # Value access
    def get(self, key, default=None): ...   # replaces ns.key attribute access
    def keys(self): ...                      # replaces dict iteration

    # Mutation (used only inside on_refine_done hooks; .set() signals this is
    # a special/temporary pattern, easy to grep and clean up later)
    def set(self, key, value) -> None: ...

    # Containment (needed for `'title' not in self.iommi_namespace`)
    def __contains__(self, key): ...

    # Internal
    def _refine(self, prio, **kwargs) -> 'RefinableStack': ...
    def _get_resolved(self) -> Namespace: ...   # triggers lazy resolution
    def _get_parent_stack(self) -> list: ...
```

`__setitem__` and `__setattr__` are **not** implemented — callers must use `.set()`.
`__getitem__`, `__getattr__`, `__iter__`, `__eq__` are **not** implemented.

## Performance model

| Operation | Before | After |
|---|---|---|
| `_refine()` (called N times) | O(paths × N) dict construction | O(stack_size) list append + sort |
| First dict-like access | — | O(paths) — merge done once, cached |
| Subsequent dict-like access | O(1) | O(1) — cache hit |

For a typical component with N=5 refinements and 30 paths: **5× fewer merge operations**.

## `_refine()` implementation sketch

```python
def _refine(self, prio: Prio, **kwargs) -> 'RefinableStack':
    params = Namespace(**kwargs)
    stack = self._get_parent_stack() + [(prio, params, list(flatten_items(params)))]
    stack.sort(key=lambda x: x[0].value)
    result = object.__new__(RefinableStack)
    object.__setattr__(result, '_stack', stack)
    object.__setattr__(result, '_resolved', None)
    return result
```

## `_get_resolved()` implementation sketch

```python
def _get_resolved(self) -> Namespace:
    if self._resolved is None:
        # Current merge logic from _refine(), extracted verbatim:
        resolved = Namespace()
        missing = object()
        for prio, params, flattened_params in self._stack:
            for path, value in flattened_params:
                # ... prefix walking, RefinableObject delegation ...
        object.__setattr__(self, '_resolved', resolved)
    return self._resolved
```

## `__init__`

```python
def __init__(self, **kwargs):
    if kwargs:
        ns = Namespace(**kwargs)
        object.__setattr__(self, '_stack', [(Prio.base, ns, list(flatten_items(ns)))])
    else:
        object.__setattr__(self, '_stack', [])
    object.__setattr__(self, '_resolved', None)
```

## Call-site changes

### Production code (~30 lines, 8 files)

| File | Pattern | Change |
|---|---|---|
| `refinable.py` | `dict(result.iommi_namespace)` | `{k: ns.get(k) for k in ns.keys()}` |
| `refinable.py` | `flatten_items(self.iommi_namespace)` in `__repr__` | `flatten_items(self.iommi_namespace._get_resolved())` |
| `form.py` | `'title' not in self.iommi_namespace` | `__contains__` handles this unchanged |
| `form.py` | `self.iommi_namespace.non_editable_input = Namespace(...)` | `.set('non_editable_input', Namespace(...))` |
| `member.py` | `container.iommi_namespace[name] = member_by_name` | `.set(name, member_by_name)` |
| `table.py`, `edit_table.py`, `query.py`, `fragment.py`, `panel.py` | `ns.columns`, `ns.filters`, `ns.parts`, etc. | `ns.get('columns')`, `ns.get('filters')`, etc. |
| `query.py` | `ns.form.get('fields', {})` | `ns.get('form', Namespace()).get('fields', {})` |

### Test code (~25 lines, 6 files)

| File | Pattern | Change |
|---|---|---|
| `refinable__tests.py` | `ns == Namespace(a=1, b=2)` | `ns._get_resolved() == Namespace(a=1, b=2)` |
| `shortcut__tests.py` | `ns == dict(x=17, y=42)` | `ns._get_resolved() == dict(x=17, y=42)` |
| `table__tests.py` | `ns.columns.keys()` | `ns.get('columns').keys()` |
| `query__tests.py` | `ns.filters.keys()` | `ns.get('filters').keys()` |
| `member__tests.py` | `ns.fruits.banana.taste` | `ns.get('fruits').banana.taste` |
| `form__tests.py`, `page__tests.py` | `ns.template`, `ns.parts.foo` | `ns.get('template')`, `ns.get('parts').foo` |

## Naming

- Rename `RefinableNamespace` → `RefinableStack` everywhere.
- Update `RefinableObject.iommi_namespace` type annotation accordingly.
- Use `_stack` and `_resolved` as the attribute names (no mangling needed since we own the class). Use `object.__setattr__` to set them, since `__setattr__` will not be delegating to a dict.

## Testing strategy

No new tests needed — existing test suite provides full coverage. Tests fail during
implementation (call-site changes break them) and pass once all sites are updated.
This is the completion criterion.
