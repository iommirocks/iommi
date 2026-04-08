# RefinableStack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `RefinableNamespace` (eager dict) with `RefinableStack` (lazy, non-dict) to eliminate redundant namespace merges on every `_refine()` call.

**Architecture:** Add shims to `RefinableNamespace` so all call sites can be migrated first (tests remain green throughout). Then implement `RefinableStack` and swap it in. Migration goes file-by-file: production code first, then tests.

**Tech Stack:** Python, pytest — no new dependencies.

---

## File Map

| File | Change |
|---|---|
| `iommi/refinable.py` | Add `RefinableStack` class; add `_get_resolved()`/`.set()` shims to `RefinableNamespace`; fix internal call sites; swap `RefinableObject` to use `RefinableStack` |
| `iommi/form.py` | Migrate attribute access + one `.set()` mutation |
| `iommi/member.py` | Migrate one `[]=` mutation to `.set()` |
| `iommi/table.py` | Migrate attribute access (~10 lines) |
| `iommi/edit_table.py` | Migrate attribute access (~6 lines) |
| `iommi/query.py` | Migrate attribute access (~4 lines) |
| `iommi/fragment.py` | Migrate one attribute access |
| `iommi/panel.py` | Migrate one attribute access |
| `iommi/refinable__tests.py` | Migrate `== Namespace(...)` assertions |
| `iommi/shortcut__tests.py` | Migrate `== dict(...)` assertions |
| `iommi/table__tests.py` | Migrate `.columns.keys()` access |
| `iommi/query__tests.py` | Migrate `.filters.keys()` and `.field` access |
| `iommi/member__tests.py` | Migrate `.fruits`, `.orange`, etc. access |
| `iommi/form__tests.py` | Migrate `.is_list`, `.fields`, `.template` access |
| `iommi/page__tests.py` | Migrate `.parts` access |

---

## Task 1: Add shims to `RefinableNamespace` and fix `refinable.py` internals

**Files:**
- Modify: `iommi/refinable.py`

These shims let subsequent tasks migrate call sites while keeping the old class in place and tests green.

- [ ] **Step 1: Add `_get_resolved`, `set` shims and fix `dict()` / `flatten_items` calls in `refinable.py`**

In `iommi/refinable.py`, make these changes to `RefinableNamespace`:

```python
class RefinableNamespace(Namespace):
    __iommi_refined_stack: List[Tuple[Prio, Namespace, List[Tuple[str, Any]]]]

    def _get_resolved(self):
        # shim: RefinableNamespace IS already a resolved dict
        return self

    def set(self, key, value):
        # shim: RefinableNamespace is a dict, so plain assignment works
        self[key] = value

    def print_origin(self, refinable_name):
        ...  # unchanged
```

In `RefinableObject.refine_done()`, change line 267:
```python
# Before:
remaining_namespace = dict(result.iommi_namespace)
# After:
remaining_namespace = {k: result.iommi_namespace.get(k) for k in result.iommi_namespace.keys()}
```

In `RefinableObject.__repr__()`, change line 323:
```python
# Before:
f"<{self.__class__.__name__} " + ' '.join(f'{k}={v}' for k, v in flatten_items(self.iommi_namespace)) + ">"
# After:
f"<{self.__class__.__name__} " + ' '.join(f'{k}={v}' for k, v in flatten_items(self.iommi_namespace._get_resolved())) + ">"
```

- [ ] **Step 2: Run refinable tests to confirm still green**

```
pytest iommi/refinable__tests.py iommi/shortcut__tests.py -x -q
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add iommi/refinable.py
git commit -m "refactor: add _get_resolved/set shims to RefinableNamespace, fix dict() and flatten_items calls"
```

---

## Task 2: Migrate `refinable__tests.py` equality assertions

**Files:**
- Modify: `iommi/refinable__tests.py`

`_get_resolved()` shim (added in Task 1) makes this safe — it returns `self` on the old class.

- [ ] **Step 1: Replace all `iommi_namespace == Namespace(...)` assertions**

Find all occurrences (9 total, lines 53, 68, 81, 95, 103, 106, 207, 210, 213) and change:
```python
# Before:
assert my_refinable.iommi_namespace == Namespace(b=4711)
# After:
assert my_refinable.iommi_namespace._get_resolved() == Namespace(b=4711)
```

Apply the same pattern to every `== Namespace(...)` comparison in this file. The left-hand side varies (`my_refinable.iommi_namespace`, `my_refined_namespacey.iommi_namespace`, etc.) — always append `._get_resolved()` before the `==`.

- [ ] **Step 2: Run tests**

```
pytest iommi/refinable__tests.py -x -q
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add iommi/refinable__tests.py
git commit -m "refactor: use _get_resolved() in refinable equality assertions"
```

---

## Task 3: Migrate `shortcut__tests.py` equality assertions

**Files:**
- Modify: `iommi/shortcut__tests.py`

- [ ] **Step 1: Replace `iommi_namespace == dict(...)` assertions (7 occurrences)**

Lines 106, 144, 287, 309, 320, 340, 350:
```python
# Before:
assert result.iommi_namespace == dict(x=17, y=42, z=4711)
# After:
assert result.iommi_namespace._get_resolved() == dict(x=17, y=42, z=4711)
```

- [ ] **Step 2: Run tests**

```
pytest iommi/shortcut__tests.py -x -q
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add iommi/shortcut__tests.py
git commit -m "refactor: use _get_resolved() in shortcut equality assertions"
```

---

## Task 4: Migrate `form.py` call sites

**Files:**
- Modify: `iommi/form.py`

- [ ] **Step 1: Fix `Field.on_refine_done()` — lines 841–847**

```python
# Before:
self.iommi_namespace.non_editable_input = Namespace(
    {
        **flatten(self.iommi_namespace.input),
        **self.iommi_namespace.non_editable_input,
    }
)
self.non_editable_input = self.iommi_namespace.non_editable_input(_name='non_editable_input',).refine_done(parent=self)

# After:
self.iommi_namespace.set('non_editable_input', Namespace(
    {
        **flatten(self.iommi_namespace.get('input', Namespace())),
        **self.iommi_namespace.get('non_editable_input', Namespace()),
    }
))
self.non_editable_input = self.iommi_namespace.get('non_editable_input')(_name='non_editable_input',).refine_done(parent=self)
```

- [ ] **Step 2: Fix line 2373**

```python
# Before:
include=lambda form, **_: list(keys(form.iommi_namespace.fields)) == ['iommi_default_text'],
# After:
include=lambda form, **_: list(keys(form.iommi_namespace.get('fields', {}))) == ['iommi_default_text'],
```

Note: `'title' not in self.iommi_namespace` at line 1906 uses `__contains__` and works unchanged on both old and new class — leave it as-is.

- [ ] **Step 3: Run form tests**

```
pytest iommi/form__tests.py -x -q
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add iommi/form.py
git commit -m "refactor: migrate form.py iommi_namespace call sites to .get()/.set()"
```

---

## Task 5: Migrate `member.py` call site

**Files:**
- Modify: `iommi/member.py`

- [ ] **Step 1: Fix line 178**

```python
# Before:
container.iommi_namespace[name] = member_by_name
# After:
container.iommi_namespace.set(name, member_by_name)
```

- [ ] **Step 2: Run member tests**

```
pytest iommi/member__tests.py -x -q
```
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add iommi/member.py
git commit -m "refactor: migrate member.py iommi_namespace mutation to .set()"
```

---

## Task 6: Migrate `table.py` call sites

**Files:**
- Modify: `iommi/table.py`

- [ ] **Step 1: Fix lines 234–235 (parts.page)**

```python
# Before:
if table.iommi_namespace.parts.page:
    paginator_parameter_name = table.iommi_namespace.parts.page.iommi_path
# After:
if table.iommi_namespace.get('parts', Namespace()).get('page'):
    paginator_parameter_name = table.iommi_namespace.get('parts').get('page').iommi_path
```

- [ ] **Step 2: Fix line 390 (columns dict access)**

```python
# Before:
column_definition = table.iommi_namespace.columns[traversable.iommi_name()]
# After:
column_definition = table.iommi_namespace.get('columns')[traversable.iommi_name()]
```

- [ ] **Step 3: Fix line 541 (sortable item access)**

```python
# Before:
(self.iommi_namespace['sortable'] is MISSING or self.iommi_namespace['sortable'] is default_sortable)
# After:
(self.iommi_namespace.get('sortable', MISSING) is MISSING or self.iommi_namespace.get('sortable', MISSING) is default_sortable)
```

- [ ] **Step 4: Fix lines 2072, 2102, 2147, 2176, 2205, 2311 (columns attribute access)**

```python
# Before (each occurrence):
self.iommi_namespace.columns
# After:
self.iommi_namespace.get('columns', {})
```

Apply to all 6 occurrences: `values(self.iommi_namespace.columns)` → `values(self.iommi_namespace.get('columns', {}))`, `items(self.iommi_namespace.columns)` → `items(self.iommi_namespace.get('columns', {}))`.

- [ ] **Step 5: Fix lines 2140, 2177, 2203 (filters and bulk)**

```python
# Before:
declared_filters = self.query.iommi_namespace.filters
# After:
declared_filters = self.query.iommi_namespace.get('filters', {})

# Before:
'actions' in self.iommi_namespace.bulk   # (2 occurrences)
# After:
'actions' in self.iommi_namespace.get('bulk', {})
```

- [ ] **Step 6: Run table tests**

```
pytest iommi/table__tests.py -x -q
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add iommi/table.py
git commit -m "refactor: migrate table.py iommi_namespace call sites to .get()"
```

---

## Task 7: Migrate `edit_table.py` and `query.py`

**Files:**
- Modify: `iommi/edit_table.py`
- Modify: `iommi/query.py`

- [ ] **Step 1: Fix `edit_table.py` — lines 152–155, 527, 549, 590**

```python
# Line 152:
field.input = field.iommi_namespace.input(_name='input')
# →
field.input = field.iommi_namespace.get('input')(_name='input')

# Line 153:
field.non_editable_input = field.iommi_namespace.non_editable_input(_name='non_editable_input')
# →
field.non_editable_input = field.iommi_namespace.get('non_editable_input')(_name='non_editable_input')

# Line 154:
field.editable = field.iommi_namespace.editable
# →
field.editable = field.iommi_namespace.get('editable')

# Line 155:
field.initial = field.iommi_namespace.initial
# →
field.initial = field.iommi_namespace.get('initial')

# Line 527:
for name, column in items(self.iommi_namespace.columns):
# →
for name, column in items(self.iommi_namespace.get('columns', {})):

# Line 549:
field = column.iommi_namespace.field
# →
field = column.iommi_namespace.get('field')

# Line 590:
declared_fields = self.edit_form.iommi_namespace.fields
# →
declared_fields = self.edit_form.iommi_namespace.get('fields', {})
```

- [ ] **Step 2: Fix `query.py` — lines 765, 778, 800, 805**

```python
# Line 765:
freetext_search_config = self.iommi_namespace.form.get('fields', {}).get(FREETEXT_SEARCH_NAME, {})
# →
freetext_search_config = self.iommi_namespace.get('form', Namespace()).get('fields', {}).get(FREETEXT_SEARCH_NAME, {})

# Line 778:
for name, filter in items(self.iommi_namespace.filters):
# →
for name, filter in items(self.iommi_namespace.get('filters', {})):

# Line 800:
declared_filters = self.iommi_namespace.filters
# →
declared_filters = self.iommi_namespace.get('filters', {})

# Line 805:
if name in declared_filters and name not in self.iommi_namespace.filters:
# →
if name in declared_filters and name not in self.iommi_namespace.get('filters', {}):
```

- [ ] **Step 3: Run tests**

```
pytest iommi/edit_table__tests.py iommi/query__tests.py -x -q
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add iommi/edit_table.py iommi/query.py
git commit -m "refactor: migrate edit_table.py and query.py iommi_namespace call sites to .get()"
```

---

## Task 8: Migrate `fragment.py` and `panel.py`

**Files:**
- Modify: `iommi/fragment.py`
- Modify: `iommi/panel.py`

- [ ] **Step 1: Fix `fragment.py` line 226**

```python
# Before:
members_from_namespace=self.iommi_namespace.children,
# After:
members_from_namespace=self.iommi_namespace.get('children', {}),
```

- [ ] **Step 2: Fix `panel.py` line 59**

```python
# Before:
return self.iommi_namespace.children
# After:
return self.iommi_namespace.get('children')
```

- [ ] **Step 3: Run tests**

```
pytest iommi/ -x -q --ignore=iommi/js --ignore=examples -p no:xdist
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add iommi/fragment.py iommi/panel.py
git commit -m "refactor: migrate fragment.py and panel.py iommi_namespace call sites to .get()"
```

---

## Task 9: Migrate remaining test files

**Files:**
- Modify: `iommi/table__tests.py`
- Modify: `iommi/query__tests.py`
- Modify: `iommi/member__tests.py`
- Modify: `iommi/form__tests.py`
- Modify: `iommi/page__tests.py`

- [ ] **Step 1: Fix `table__tests.py` (5 occurrences of `.columns.keys()`)**

Lines 2272, 2283, 2293, 2308, 2315:
```python
# Before:
set(t.iommi_namespace.columns.keys())
list(t.iommi_namespace.columns.keys())
# After:
set(t.iommi_namespace.get('columns').keys())
list(t.iommi_namespace.get('columns').keys())
```

- [ ] **Step 2: Fix `query__tests.py`**

Lines 698, 715, 736 (`.filters.keys()`):
```python
# Before:
set(t.iommi_namespace.filters.keys())
# After:
set(t.iommi_namespace.get('filters').keys())
```

Line 980 (`.field.call_target.attribute`):
```python
# Before:
shortcut(**kwargs).iommi_namespace.field.call_target.attribute == name
# After:
shortcut(**kwargs).iommi_namespace.get('field').call_target.attribute == name
```

- [ ] **Step 3: Fix `member__tests.py`**

Lines 29, 34, 42, 50, 51, 59, 347, 350, 358:
```python
# Before:
Basket().refine_done().iommi_namespace.fruits == {}
basket.iommi_namespace.fruits.banana.taste
basket.iommi_namespace.fruits.orange.taste
basket.iommi_namespace.fruits.pear.taste
basket.iommi_namespace.fruits.orange._name
'orange' not in basket.iommi_namespace.fruits
# After:
Basket().refine_done().iommi_namespace.get('fruits') == {}
basket.iommi_namespace.get('fruits').banana.taste
basket.iommi_namespace.get('fruits').orange.taste
basket.iommi_namespace.get('fruits').pear.taste
basket.iommi_namespace.get('fruits').orange._name
'orange' not in basket.iommi_namespace.get('fruits', {})
```

Note: `.banana`, `.orange`, `.taste`, `._name` after `.get('fruits')` all work because `fruits` is itself a `Namespace` (dict-like), which supports attribute access.

- [ ] **Step 4: Fix `form__tests.py`**

Line 223:
```python
# Before:
assert f.iommi_namespace.is_list
# After:
assert f.iommi_namespace.get('is_list')
```

Line 668:
```python
# Before:
assert list(form.iommi_namespace.fields.keys()) == ['foo', 'bar']
# After:
assert list(form.iommi_namespace.get('fields').keys()) == ['foo', 'bar']
```

Lines 4115–4116:
```python
# Before:
assert MyForm.case1().refine_done().iommi_namespace.template == 'case1'
assert MyForm.case2().refine_done().iommi_namespace.template == 'case2'
# After:
assert MyForm.case1().refine_done().iommi_namespace.get('template') == 'case1'
assert MyForm.case2().refine_done().iommi_namespace.get('template') == 'case2'
```

- [ ] **Step 5: Fix `page__tests.py`**

Line 48:
```python
# Before:
assert list(my_page.iommi_namespace.parts.keys()) == ['h1', 'foo', 'bar']
# After:
assert list(my_page.iommi_namespace.get('parts').keys()) == ['h1', 'foo', 'bar']
```

Line 97:
```python
# Before:
assert isinstance(page.iommi_namespace.parts.foo, Fragment)
# After:
assert isinstance(page.iommi_namespace.get('parts').foo, Fragment)
```

- [ ] **Step 6: Run all tests**

```
pytest iommi/ -x -q --ignore=iommi/js --ignore=examples -p no:xdist
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add iommi/table__tests.py iommi/query__tests.py iommi/member__tests.py iommi/form__tests.py iommi/page__tests.py
git commit -m "refactor: migrate test files to use iommi_namespace.get() and ._get_resolved()"
```

---

## Task 10: Implement `RefinableStack`

**Files:**
- Modify: `iommi/refinable.py`
- Modify: `iommi/refinable__tests.py` (add one test)

- [ ] **Step 1: Write the laziness test first**

Add to `iommi/refinable__tests.py`:

```python
def test_refinable_stack_lazy_resolution():
    """_refine() must not trigger resolution; first .get() resolves and caches."""
    from iommi.refinable import RefinableStack

    class MyObj(RefinableObject):
        a = Refinable()
        b = Refinable()

    obj = MyObj(a=1)
    stack = obj.iommi_namespace
    stack2 = stack._refine(Prio.refine, b=2)
    stack3 = stack2._refine(Prio.refine_defaults, a=99)  # lower prio, loses

    # No resolution has happened yet
    assert object.__getattribute__(stack3, '_resolved') is None

    # First access triggers resolution
    assert stack3.get('a') == 1   # Prio.refine wins over Prio.refine_defaults
    assert stack3.get('b') == 2

    # Subsequent access uses cache
    resolved_id = id(object.__getattribute__(stack3, '_resolved'))
    _ = stack3.get('a')
    assert id(object.__getattribute__(stack3, '_resolved')) == resolved_id
```

- [ ] **Step 2: Run it — expect ImportError or AttributeError (RefinableStack not yet defined)**

```
pytest iommi/refinable__tests.py::test_refinable_stack_lazy_resolution -x -v
```
Expected: FAIL.

- [ ] **Step 3: Implement `RefinableStack` in `iommi/refinable.py`**

Add the class directly after the `RefinableNamespace` class:

```python
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
        """Mutate the resolved namespace directly. Only for use in on_refine_done hooks."""
        self._get_resolved()[key] = value

    def __contains__(self, key):
        return key in self._get_resolved()

    # --- Stack inspection ---

    def as_stack(self):
        return [(prio.name, dict(flattened_params)) for prio, _, flattened_params in self._get_parent_stack()]

    def print_origin(self, refinable_name):
        for prio, params in self.as_stack():
            if refinable_name in params:
                print(prio, params[refinable_name])
```

- [ ] **Step 4: Run the laziness test**

```
pytest iommi/refinable__tests.py::test_refinable_stack_lazy_resolution -x -v
```
Expected: PASS.

- [ ] **Step 5: Run all refinable tests (RefinableStack not yet wired in, so all still pass)**

```
pytest iommi/refinable__tests.py iommi/shortcut__tests.py -x -q
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add iommi/refinable.py iommi/refinable__tests.py
git commit -m "feat: add RefinableStack with lazy resolution"
```

---

## Task 11: Swap `RefinableObject` to use `RefinableStack`

**Files:**
- Modify: `iommi/refinable.py`

- [ ] **Step 1: Swap the class used in `RefinableObject.__init__` and update type annotation**

In `RefinableObject.__init__` (line 218):
```python
# Before:
self.iommi_namespace = RefinableNamespace(**kwargs)
# After:
self.iommi_namespace = RefinableStack(**kwargs)
```

Change the type annotation (line 212):
```python
# Before:
iommi_namespace: RefinableNamespace
# After:
iommi_namespace: RefinableStack
```

Add a backward-compat alias **after** the `RefinableStack` class definition (near the end of the class definitions section), so any external code importing `RefinableNamespace` still works:
```python
# Backward-compat alias — old class body will be removed in Task 12
RefinableNamespace = RefinableStack
```

Do NOT touch the old `RefinableNamespace` class body yet — Task 12 removes it. The alias overwrites the name in the module namespace, so all `RefinableNamespace(...)` calls will produce `RefinableStack` instances.

- [ ] **Step 2: Run full test suite**

```
pytest iommi/ -x -q --ignore=iommi/js --ignore=examples -p no:xdist
```
Expected: all pass. If any fail, check that the failed file was migrated in Tasks 1–9.

- [ ] **Step 3: Commit**

```bash
git add iommi/refinable.py
git commit -m "feat: wire RefinableStack into RefinableObject, alias RefinableNamespace"
```

---

## Task 12: Final cleanup and verification

**Files:**
- Modify: `iommi/refinable.py` (remove dead `RefinableNamespace` class body)

- [ ] **Step 1: Remove the old `RefinableNamespace` class body**

The old class inherits from `Namespace` and carries the `__iommi_refined_stack` attribute logic. Since `RefinableNamespace = RefinableStack` now, remove the old class definition entirely and keep only the alias:

```python
# Remove this entire class:
class RefinableNamespace(Namespace):
    __iommi_refined_stack: ...
    def print_origin(...): ...
    def as_stack(...): ...
    def _get_parent_stack(...): ...
    def _refine(...): ...

# Keep only:
RefinableNamespace = RefinableStack
```

- [ ] **Step 2: Run full test suite**

```
pytest iommi/ -q --ignore=iommi/js --ignore=examples -p no:xdist
```
Expected: all pass.

- [ ] **Step 3: Final commit**

```bash
git add iommi/refinable.py
git commit -m "refactor: remove old RefinableNamespace class body, keep alias for compat"
```
