# TODO

(These are random notes for ideas, things we would like to fix and more)

examples.iommi.rocks

https for iommi.rocks redirect

auto__include/exclude should accept id/pk. And it should say it accepts them in the error message "You can only include fields that exist on the model..."

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
