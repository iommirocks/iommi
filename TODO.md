# TODO

(These are random notes for ideas, things we would like to fix and more)

examples.iommi.rocks

https for iommi.rocks redirect

A nice API to manually handle ajax/post dispatch

Formsets

json endpoints for table contents, paginator. General purpose end point for accessing any part of a part?

No imports to django outside _*_compat, statically checked in CI. flask.current_app.config == django.conf.settings

fiddle.iommi.rocks would be damn cool - just redirect to a repl.it session?

T-shirt and/or picks give aways for conferences

Make is possible to have two Column.select. Maybe set the name of the column as a css class? Then do something smart in the select_all js to make sure we only check all the checkboxes for the chosen column.

"compile" step for creating an optimized row view model extractor: compile away evaluate when applicable. We can know at Table creation time if the row and cell attrs are static. If so we can render them once. 

Get rid of reinvoke/reinvoke_new_defaults and avoid the merge of different sets of parameter (from styles, shorcuts or kwargs) until bind.

Separate crud shortcuts to a separate beast than Form. (So that callbacks and what not don't need to pollute all Form instances)

Maybe revise inheritance semantics: should class Meta on subclass override shortcut on parent? It doesn't now.

## Tests

We should have something like @pytest.mark.subject('Query.postprocess') so we can know which tests are for which method/member/etc. Then we can know which refinable members aren't tested.


## Docs

Fix docs that show priority of config

API reference for free functions

endpoints

Tutorial for how to build a site

Admin customization how to

"How to create your own iommi component": own_evaluate_parameters, on_bind, collect_members/bind_members, Refinable, EvaluatedRefinable, `__html__`

Document the assumed URL schema

Document Query.filter and Query.postprocess


## Nice to have

Breadcrumbs


## iommi.admin

generate the python config code for setting up an app and show it to the user, with a message saying where to put it (in the app if it's your app, in the global config if it's a third party app)

GUI with descriptions on how to configure stuff... like bulk editing, calculated columns, etc

Magic future stuff:

* add/change/remove columns from Models
* add entire tables
* use djangos migrations to do the schema evolution


Form field sets (aka groups). `field__group='foo'` maybe? Is this like header groups in Table where they must be contiguous? Or do we group first? Is it bad that table groups must be contiguous?

## Kill `reinvoke`

Replace fefinable baseclass from tri.declarative with a new `RefinableObject`

The `RefinableObject` will be declarative on marker classes `Refinable`, `EvaluatedRefinable` and `RefinableMembers`:

```python
class Form(RefinableObject, Traversable):
    fields = RefinableMembers()
    title = EvaluatedRefinable
    some_special_thing = Refinable()
```

- The RefinableObject constructor takes all the kwargs and those with matching declarations are added to a `.namespace` attribute. (Any spill is error reported)

- After that there are two methods on the RefinableObject, `obj.refine(foo=17)` and `obj.refine_defaults(foo=0)`, that can be used to obtain a new copy of the object with modified config in the `.namespace` attribute. (The namespace will actually be a special case of `Namespace` that retains the history in which the values were refined, for later inspection)

- When no further refinement is needed. (i.e. when all styling and what not is applied) there is a method on `RefinableObject`, `done_refining` that can be invoked to traverse the `.namespace` and apply the values to corresponding attributes. 

- When invoking `done_refining()` is called there is a callback invoked, `.on_done_refine` that typically will contain all the functionallity currently in the object constructors.

- All `reinvoke` and `set_and_remember_for_reinvoke` cruft could be refactored to just be `.refine()`

- What is currently done in `collect_members`/`bind_members` should move somewhere, but could probably be handled by the `RefinableObject` since there is a `RefinableMembers` decorator indicating which one to collect. (And the extra parameters like for the string passthrough of members, could be indicated by constants on the field declaration)

- The application of style will be done with a new traversal method on `Traversable`, `apply_styles()`. It should look for styles for the config in the `.namespace`.

- The `get_declared` functionallity should not be needed since the relevant config should be available in the `.namespace` attribute.

- TODO: 

  - Where does `form_class` et al fit in?

  - Should `on_done_refine` be a refinable attribute even?
  
  - The details on when a `on_done_refine` method want to add somethin (typically a new member e.g. the freetext field in query). The new thingy can be completed with mixing existing config from the container .namespace, applying style and `.done_refining()` so it should be doable.
  
  - Invoke this by using the easy 80% of this implemented with different naming in the `namespacey` branch.
  
