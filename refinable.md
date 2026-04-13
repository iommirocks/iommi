# The iommi Refinable System

## Overview

The refinable system is the configuration backbone of iommi. Every UI component — `Form`, `Table`, `Fragment`, `Action`, `Query`, `Menu`, and everything in between — inherits from `RefinableObject`. The system answers one central design question:

> How can a component be configured at multiple, independent layers (framework defaults, style, class Meta, shortcut methods, parent containers, and end-user code) without any layer stomping unexpectedly on another?

The answer is a two-phase lifecycle. During the **refinement phase** each configuration layer records its intent at a declared priority. During the **finalisation phase** (`refine_done()`) all recorded intents are merged in priority order and written onto the object as real attributes. Nothing is evaluated, no rendering happens, and no request is needed until a third, later phase (`bind()`).

### Typical usage at a glance

```python
from iommi import Form, Field
from iommi.refinable import Refinable, EvaluatedRefinable, RefinableObject

# 1. Declare a refinable component
class MyWidget(RefinableObject):
    label: str = Refinable()
    visible: bool = EvaluatedRefinable()

# 2. Construct — values are stored in iommi_namespace, not yet on the object
w = MyWidget(label="Username", visible=True)

# 3. Optionally add more configuration at a lower priority (will not override
#    values already set at a higher priority)
w = w.refine_defaults(label="Default label")

# 4. Finalise — namespace is resolved and attributes are written
w = w.refine_done()
assert w.label == "Username"   # constructor wins over refine_defaults
assert w.visible is True
```

Because `refine_done()` returns a copy you can safely keep both the pre- and post-finalised objects.

---

## How components actually use it

### Declaring refinable attributes

Every attribute that users of iommi are allowed to configure is declared as a class-level descriptor:

```python
class Part(Traversable):                       # iommi/part.py
    include: bool = SpecialEvaluatedRefinable()
    after: Union[int, str] = EvaluatedRefinable()
    extra: Dict[str, Any] = Refinable()
    assets: Namespace = RefinableMembers()
    endpoints: Namespace = RefinableMembers()
```

```python
class Form(Part, Tag):                         # iommi/form.py
    fields: Namespace = RefinableMembers()
    actions: Namespace = RefinableMembers()
    instance: Any = Refinable()
    editable: bool = Refinable()
    member_class: Type[Field] = Refinable()
    attrs: Attrs = SpecialEvaluatedRefinable()
    actions_template: Union[str, Template] = EvaluatedRefinable()
```

The descriptor types control what happens to the value during `refine_done()` and `bind()`:

| Descriptor | Resolved at | Notes |
|---|---|---|
| `Refinable()` | `refine_done()` | Plain value; stored as-is |
| `@refinable` | `refine_done()` | Marks a *method* as replaceable by a callable kwarg |
| `EvaluatedRefinable()` | `bind()` | If the resolved value is callable it is called with available kwargs |
| `@evaluated_refinable` | `bind()` | Marks a *method* that is also callable-evaluated |
| `SpecialEvaluatedRefinable()` | `bind()` | Like `EvaluatedRefinable` but with additional special-case handling (e.g. `attrs`) |
| `RefinableMembers()` | `on_refine_done()` hook | A namespace of child `RefinableObject` instances finalised together |

### Class Meta defaults

A `Meta` inner class provides per-class defaults without polluting `__init__` signatures:

```python
class Fragment(Part, Tag):
    attrs: Attrs = SpecialEvaluatedRefinable()
    children = RefinableMembers()

    class Meta:
        children = EMPTY
        attrs__class = EMPTY
        attrs__style = EMPTY
```

`Meta` values are applied at `Prio.meta` priority, so they lose to styles, shortcuts, and explicit user configuration, but win over built-in defaults.

### Shortcut methods

Class methods that pre-configure a component for a common use case refine at `Prio.shortcut`:

```python
class Action(Fragment):            # iommi/action.py
    @classmethod
    def icon(cls, icon, *, display_name=None, **kwargs):
        return cls(**kwargs).refine(
            Prio.shortcut,
            display_name=...,
            extra__icon=icon,
        )
```

Because `Prio.shortcut` sits below `Prio.refine`, the end-user can always override whatever the shortcut sets.

### Member collections

`RefinableMembers` lets you refine individual members of a collection via the double-underscore path syntax:

```python
# Refine a specific basket member
basket = Basket(fruits__banana=Fruit(color='yellow'))
basket = basket.refine(fruits__banana__taste='good').refine_done()
banana = basket.fruits.banana.refine_done()
assert banana.color == 'yellow'
assert banana.taste == 'good'
```

The double-underscore syntax (`fruits__banana__taste`) drills into nested namespaces and nested `RefinableObject`s transparently.

### Replaceable methods via @refinable

The `@refinable` decorator turns a method into a replaceable default:

```python
class MyRefinable(RefinableObject):
    @staticmethod
    @refinable
    def display_name():
        return 'Default name'

# Override at construction time
obj = MyRefinable(display_name=lambda: 'Custom name').refine_done()
assert obj.display_name() == 'Custom name'

# Default is used when not overridden
obj = MyRefinable().refine_done()
assert obj.display_name() == 'Default name'
```

---

## Priority ordering

When multiple layers configure the same attribute, the `Prio` enum decides who wins. Higher enum value = higher priority = wins:

```
Prio.refine_defaults   ← lowest  (framework-level soft defaults)
Prio.table_defaults              (Table container defaults for its columns)
Prio.member_defaults             (container defaults applied to each member)
Prio.constructor                 (values passed to __init__)
Prio.shortcut                    (values set by shortcut class methods)
Prio.style                       (iommi style/theme)
Prio.meta                        (inner class Meta)
Prio.base                        (initial namespace before any refinement)
Prio.member                      (per-member overrides from the container)
Prio.refine          ← highest  (explicit .refine() calls from user code)
```

```python
w = MyWidget(label="from constructor")           # Prio.constructor
w = w.refine_defaults(label="soft default")      # Prio.refine_defaults
w = w.refine_done()
assert w.label == "from constructor"             # constructor wins

w2 = MyWidget()
w2 = w2.refine_defaults(label="soft default")
w2 = w2.refine_done()
assert w2.label == "soft default"                # only value present
```

---

## Technical analysis of the internal workings

### RefinableStack — the refinement stack

`RefinableStack` is a standalone class (not a `Namespace` subclass) that carries `_stack`: a list of `(Prio, raw_params, flattened_items)` tuples, one entry per `.refine()` call. It also holds a `_resolved` cache and a `_value_set` flag.

`_refine(prio, **kwargs)` builds a new `RefinableStack` by:
1. Appending the new `(prio, params, flattened_items)` entry to a copy of the stack.
2. Sorting the copy by `prio.value` (ascending = lowest priority first).
3. Returning a fresh `RefinableStack` with the sorted stack and `_resolved = None`.

Resolution is **lazy**: the sorted stack is only collapsed into a final `Namespace` when `as_namespace()` is first called (which triggers `_build_resolved()`). During `_build_resolved()`:
- For each `(path, value)` in priority order:
  - Walk every prefix of the path looking for an existing `RefinableObject` in the result.
  - If found and the incoming update is dict-like, delegate to `existing.refine(prio, **sub_kwargs)` — recursion into nested objects.
  - If the incoming value is itself a `RefinableObject`, write it directly.
  - Otherwise write the value at the path.

The result is cached on `_resolved` so subsequent `as_namespace()` calls are O(1).

Additional public methods on `RefinableStack`:
- `get(key, default=None)` — read a key from the resolved namespace.
- `set(key, value)` — mutate the resolved namespace directly; only for use in `on_refine_done()` hooks (sets `_value_set = True`, preventing further `_refine()` calls).
- `__contains__(key)` — membership test against the resolved namespace.
- `as_stack()` — returns the raw stack as a list of `(prio_name, flattened_dict)` pairs for debugging.
- `print_origin(refinable_name)` — prints, for each stack layer, the value of `refinable_name` if present.

The stack can be inspected for debugging:

```python
basket = Basket(fruits__banana=Fruit(color='yellow'))
basket = basket.refine(fruits__banana__taste='good').refine_done()
print(basket.iommi_namespace.as_stack())
# [('base', {'fruits__banana': <Fruit color=yellow>}),
#  ('refine', {'fruits__banana__taste': 'good'})]
```

### refine_done() — materialisation

`refine_done()` is always non-mutating on the original object (it operates on a `copy(self)`):

1. **Meta injection** — reads `cls.Meta` via `get_meta()` and calls `._refine(Prio.meta, ...)`.
2. **Style application** — if the class has `apply_style`, resolves the active style and applies it (this adds more `_refine(Prio.style, ...)` calls internally).
3. **Attribute assignment** — iterates over all declared `refinable` items; for each one that is a `Refinable` subclass, pops the value from `iommi_namespace` and assigns it as a real Python attribute (`setattr`).
4. **Validation** — anything left in `iommi_namespace` after the above loop is an unknown key; raises `TypeError`.
5. **Hook** — calls `on_refine_done()` (overridden by subclasses to finalise child members).
6. **Signature warming** — caches argument signatures of all `EvaluatedRefinable` callables to speed up `bind()`.

### on_refine_done() — child finalisation

`Part.on_refine_done()` calls `refine_done_members()` for `endpoints` and `assets`. Each concrete component adds its own overrides. For example `Form.on_refine_done()` resolves `fields`, `actions`, and calls `refine_done()` on sub-components like `self.input`, `self.label`, etc.

### bind() — request-time evaluation

After `refine_done()` the object is still static. `bind(parent, request)` makes it live:

- Evaluates all `EvaluatedRefinable` attributes: if the stored value is callable it is called with named kwargs drawn from the current context (request, parent, bound siblings, etc.).
- Recursively binds child members.
- Returns `None` if `include` evaluates to `False`, allowing declarative conditional inclusion.

### Prio.constructor — the one in-place exception

All priorities create a copy of the object. `Prio.constructor` is the sole exception: it mutates in place. This is used inside `__init__` methods (e.g. `Fragment.__init__` setting `children__text`) where a copy would be immediately thrown away and immutability is not yet needed.

### Descriptor resolution

`@declarative(member_class=Refinable, parameter='refinable', is_member=is_refinable_function)` scans each class at definition time and collects all attributes that are instances of `Refinable` or are methods decorated with `@refinable`. The result is stored in a `get_declared('refinable')` registry used by both `__init__` validation and `refine_done()` assignment.

The `_get_evaluated_attributes_cache` and `_get_special_evaluated_attributes_cache` dicts are module-level keyed by class object, providing O(1) lookup of which attributes need callable evaluation at bind time.

---

## Potential improvements

The following are areas where the implementation could be improved. None require a full rewrite, and the public API semantics can be preserved or adjusted only minimally.

### 1. The `refine_defaults` shadowing trap

**Current behaviour:** When a `Fruit(color='yellow')` is placed at `Prio.base` and `Prio.refine_defaults` tries to set `fruits__banana__taste='good'`, the taste is silently dropped. The `Fruit` object already exists at a higher priority, so the path prefix check finds it and attempts `existing.refine(Prio.refine_defaults, taste='good')` — but then the base-priority `Fruit` instance wins over that refinement.

```python
basket = Basket(fruits__banana=Fruit(color='yellow'))
basket = basket.refine_defaults(fruits__banana__taste='good').refine_done()
banana = basket.fruits.banana.refine_done()
assert banana.taste is None   # surprising: the default was silently dropped
```

**Possible fix:** When a `RefinableObject` is encountered at a higher-priority prefix and the incoming refinement is at a lower priority, apply the refinement to the sub-object at that lower priority rather than discarding it. This requires tracking the priority of the existing object's "base" vs. the incoming refinement's priority more carefully.

### 2. Inconsistent in-place mutation for `Prio.constructor`

`Prio.constructor` mutates the object in place while every other priority returns a copy. This makes `refine()` have surprising return-value semantics depending on the priority passed, and makes the callers (inside `__init__`) look like they are ignoring the return value.

**Possible fix:** Remove the in-place path. Let `__init__` methods call `.refine(Prio.constructor, ...)` and capture the result. Since `__init__` is constructing the object anyway, a cheap copy at this stage has negligible cost and removes the special case.

### 3. `@refinable` inheritance without the decorator loses the default

A subclass that overrides a `@refinable` method without re-applying `@refinable` silently keeps the base-class default rather than using the subclass method:

```python
class MySubclass(MyRefinable):
    @staticmethod          # no @refinable here
    def foo():
        return 'MySubclass'

assert MySubclass().refine_done().foo() == 'MyRefinable'   # base default wins
```

This is noted as "somewhat unexpected" in the test file. The declarative scanner stops at the first class in the MRO where the attribute is marked `refinable`, so the subclass override is invisible to the system.

**Possible fix:** When `is_refinable_function` walks the MRO, prefer the most-derived method as the default value even if it lacks the `@refinable` marker, provided an ancestor declared the name as refinable.

### 4. `as_stack()` accumulates duplicate `Prio` entries

`_refine()` appends to the stack without deduplication. Multiple calls at the same priority level produce multiple entries at that priority. The sort is stable so they are replayed in call order, which is correct, but `as_stack()` shows them as separate entries with the same priority label:

```python
# From test_refined_as_stack:
[('refine_defaults', {'c': 3}),
 ('refine_defaults', {'e': 5}),   # two separate refine_defaults entries
 ('base', {'a': 1}),
 ('refine', {'b': 2}),
 ('refine', {'d': 4})]
```

**Possible fix:** Merge entries of the same priority in `as_stack()` for readability, or merge them in `_refine()` (only safe if same-priority order does not matter within a level, which it currently does not since later same-priority calls override earlier ones via the replay loop).

### 5. Module-level class caches are never invalidated

`_get_evaluated_attributes_cache` and `_get_special_evaluated_attributes_cache` use the class object as key and are never cleared. This is correct for production but can cause stale results during development when Django's auto-reloader re-imports modules and creates new class objects that share names with old ones. Old entries accumulate.

**Possible fix:** Use `weakref.WeakKeyDictionary` so entries are evicted when the class object is garbage-collected.

### 6. `refine_done()` does not prevent subsequent `.refine()` on the original

`refine()` guards against being called after `is_refine_done`, but because `refine_done()` copies first, the original object's `is_refine_done` stays `False`. This means you can call `.refine()` on an object that has already been finalised into a different copy, which can lead to subtle double-configuration bugs.

**Possible fix:** Set `is_refine_done = True` on the original inside `refine_done()` before returning the copy (or use a sentinel flag specifically for "source was consumed"). Minor semantic change: calling `.refine()` after `.refine_done()` would then always raise rather than silently producing an orphaned object.

### 7. Type annotation ergonomics

`Refinable()`, `EvaluatedRefinable()`, etc. are used as class-level descriptors but appear as instance values. Type checkers (mypy, pyright) cannot understand that `label: str = Refinable()` means "label is a str at runtime after refine_done". This silently suppresses type errors on attribute access.

**Possible fix:** Use `typing.overload` or a `__class_getitem__` approach, or adopt [PEP 681](https://peps.python.org/pep-0681/) (`typing.dataclass_transform`) to annotate `RefinableObject` so that type checkers treat declared fields as typed constructor parameters. This would be purely additive and require no runtime changes.

### 8. `flatten_items` double-underscore protocol leaks into error messages

The `__` path notation is an internal serialisation detail of `Namespace`, but it surfaces in error messages ("no refinable attribute(s): `foo__bar`"). Users seeing such messages may not immediately understand the notation.

**Possible fix:** In the error-reporting paths, translate double-underscore paths back to a human-readable format (e.g. `foo.bar`) and add a brief note explaining the convention.
