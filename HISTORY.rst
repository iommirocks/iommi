Changelog
---------

2.8.12 (2021-05-18)
~~~~~~~~~~~~~~~~~~~

* Major bug: tables based on querysets would implicitly use the django result cache. This resulted in the contents of the table not changing until after process restart


2.8.11 (2021-05-07)
~~~~~~~~~~~~~~~~~~~

* `Fragment` should have `@with_meta`

* Fixed nesting tables inside forms. This would previously crash with a strange error message.

* Avoid infinite loop in sort_after on too large indicies


2.8.10 (2021-04-28)
~~~~~~~~~~~~~~~~~~~

* Read defaults from model for initial of fields

* Increased log level of SQL logging from 11 to 21 (DEBUG+1 -> INFO+1)

* Added null factory for `JSONField`

* Fixed live editing code to use the same logic as 'jump to code' to find the code

* Fixed one case where live edit broke

* Prettier debug menu for live editing

* Prettier query help text (thanks new contributor flying_sausages!)


2.8.9 (2021-03-08)
~~~~~~~~~~~~~~~~~~

* Fixed bad html escape in SQL trace magnitude graph (this is not a security problem, as it's a developer tool with very restricted access)

* Renamed freetext to freetext_search. It was too easy to collide with a user defined model with a field called freetext


2.8.8 (2021-02-23)
~~~~~~~~~~~~~~~~~~

* Automatically generating a Query from a model with a foreign key was broken in cases where the name field wasn't the same as name field of the parent model


2.8.7 (2021-02-22)
~~~~~~~~~~~~~~~~~~

* Make it possible to pass a lambda to title of Page/Form/Table

* Improved error when trying to register an already registered style


2.8.6 (2021-02-19)
~~~~~~~~~~~~~~~~~~

* Revert to the old (pre 2.8.2) way of using `search_fields` to compose queries.

  The new approach failed for cases when there was a custom `value_to_q` definition.
  A proper fix needs to have a unified approach also when using `.pk` format.


2.8.5 (2021-02-17)
~~~~~~~~~~~~~~~~~~

* Render title of `Page` objects. To turn off the rendering of the title pass `h_tag__include=False`.

* Removed the register_search_fields warning, it was 90% annoying and 10% useful


2.8.4 (2021-02-15)
~~~~~~~~~~~~~~~~~~

* Form: support passing instance as a lambda, even in combination with `auto__model`


2.8.3 (2021-02-14)
~~~~~~~~~~~~~~~~~~

* Removed bad assert that prevented passing instance as a lambda for auto__model of Form

* SQL trace was broken for postgres

* query_from_indexes should automatically generate filters for foreign keys. This especially affected the admin.


2.8.2 (2021-02-09)
~~~~~~~~~~~~~~~~~~

* Avoid using `search_fields` when composing queries from model filter values. Always using the `.pk` fallback approach is more stable when the search field values might not be unique. This will remove a bunch of warnings that weren't very helpful too.

* Fixed crash when setting `query__include=False` on `Table`

* `capitalize()` now handles safe strings properly. This will enable you to pass safe strings to `title` for example.

* Translation of Yes/No

* Fixed error message for `register_search_fields`

* Updated to fontawesome 4.7

* Renamed live edit asset to not conflict with the name 'custom' which might be fairly common

* Nicer title in the admin for apps


2.8.1 (2021-02-01)
~~~~~~~~~~~~~~~~~~

* Auto generated tables had "ID" as the column name for foreign keys, instead of the name of the remote model.

* Profiler fixed: the bind and render of iommi objects that were handled by the middleware weren't profiled

* Fixed live edit to work for views with URL arguments

* Handle settings.BASE_DIR as Path objects

* fix bulk__include = False on table

* Make DebugMenu created on demand to avoid setting of breakpoints when debugging your own code

* Models in admin are now in alphabetical order

* `Field` is not a `Tag`, so you can render a `Form` as a div if you want.

* The root menu item for the iommi admin was broken if you inherited from Admin

* Force the live edit view to be bootstrap. This avoids the live edit feature looking a big broken for your own custom styles.

* Minor bootstrap styling fix for non-editable fields


2.8.0 (2021-01-13)
~~~~~~~~~~~~~~~~~~

* Nested forms

* The paginator is now lazy. This means we can avoid a potentially expensive `.count()` database hit in many situations

* Added `Table.bulk_container`

* `Table.post_bulk_edit` takes evaluate parameters now

* Column.include=False implies that the column shouldn't get anything in the bulk form. If you want bulk editing without a visible column use Column.render_column=False

* Support auto__include=['pk']

* Fix reinvoke/reinvoke_new_defaults when shortcut is changed

* Date/datetime parsing bugs fixed after mutation testing

* Do not do form post_validation if we are in initial display mode

* Forms now don't create a submit button by default. If you have a post handler you will get a submit button though.

* SQL trace bugfixes

* Custom raw_data callback should have same semantics as constant value (and parsed_data callback)

* Improved error message on disallowed unbound object access

* Documentation improvements, for example new pages for dev tools, and styles

* Live editing on `.as_view()` style views work in the case of an explicitly declared class

* Fixed bug where the ajax enhanced table didn't work if you used `Table.div` or otherwise changed the `tag` of `Table`

* Fixed auto__model column/filter for `CharField` with choices


2.7.0 (2020-12-14)
~~~~~~~~~~~~~~~~~~

* A `Form` can now contain non-`Field` parts. Iterate over everything to render with `form.parts` and all the fields to be validated with `form.fields`. Fields that are not direct children are also collected, so you can easily add extra structure by wrapping a bunch of fields in a `html.div` for example.

* Support Django's `CharField.choices` feature

* You can now customize the name shown in the advanced search via `Filter.query_name`

* Form submit buttons (`Actions.submit`) are now rendered as `<button>` not as `<input type="submit">`.

* Added SQL trace feature

* You can now apply styles on the root object. Example: `root__assets__my_asset=Asset(...)`

* Edit button only present in debug menu when the edit middleware is installed

* Added profile button to debug menu

* Make collected assets more accessible when rendering iommi in your own templating environment: you can now access them on the iommi objects: `my_iommi_obj.iommi_collected_assets()`

* Removed broken validation of sort columns. This validation prevented sorting on annotations which was very confusing as it worked in debug mode

* Make it possible to target the live edit page with styles (via `LiveEditPage`)

* The live edit view can be flipped between horizontal and vertical layouts

* The debug tree view is slimmed down (by not including endpoints and assets on lots of things)

* `Field.raw_data_list` is removed. You can know if it's a list or not by checking `is_list`, so `raw_data` covers the uses cases.

* Include decorators in live edit

* The debug jump to code feature should work for some more scenarios, and it will not display if it has no good guess.

* DEPRECATED: `Field.choice_to_option`. This is replaced by `choice_id_formatter` and `choice_display_name_formatter`


2.6.1 (2020-12-01)
~~~~~~~~~~~~~~~~~~

* Fixed live editing to work when distributing iommi


2.6.0 (2020-12-01)
~~~~~~~~~~~~~~~~~~

* Live editing of function based views in DEBUG. Works for both iommi views and normal django views.

* Added ajax enhanced table filtering

* You can now turn off the advanced mode on queries: `Table(query__advanced__include=False)`

* `Query` has two new refinables: `filter` and `post_process`. These are hook points if you need to further customize what query is generated.

* Enable profiling when DEBUG mode is on, even if you're not staff

* Fixed multiselect on empty list

* Added missing `get_errors()` member function on `Field`

* Fixed select2 widget when the base url do not end with `/`

* Styling fixes. Primarily for bulma.


2.5.0 (2020-11-19)
~~~~~~~~~~~~~~~~~~

* include=False on a Column should imply not generating the query filter and bulk field. If you want to not render a column but still want the filters, use the render_column=False feature

* Added callbacks for saving a form: `extra__pre_save_all_but_related_fields`, `extra__on_save_all_but_related_fields`, `extra__pre_save`

* Added `extra__new_instance` callback to `Form.create` for custom object creation

* The errors list has been changed. You should always use `add_error()` to add an error on a `Field` or a `Form`

* It is now possible to call `is_valid()` and `get_errors()` and get what you expect from `post_validation` on `Field` and `Form`

* Query forms can now have additional fields, that are ignored by the filter handling code (when you want to do additional filtering outside of the query logic)

* Bug fixes with state leaking between binds

* Fixed jump to code

* Improved error message for `is_valid_filter`

* Added a nice error message if you try to shoot in `style` or `class` as raw strings

* Fixed empty table message, and invalid query form messages


2.4.0 (2020-11-04)
~~~~~~~~~~~~~~~~~~

* The given `rows` queryset and filtering were not respected for the "Select all rows" bulk feature. This could produce some pretty bad bugs!

* Support custom bulk post_handlers on lists and not just querysets

* `Table` has a few new members:
    - `initial_rows`: the rows you pass (or that gets created by `auto__model`) is stored unchanged here
    - `sorted_rows`: `initial_rows` + sorting applied
    - `sorted_and_filtered_rows`: `sorted_rows` + filtering applied
    - `visible_rows`: `sorted_and_filtered_rows` + pagination applied
    - `rows`: this is now a property and will map to the old behavior which is the "most applied" member that exists


* Fixed passing dunder paths to `auto__include`. You got a weird crash if the target of the path was a foreign key. There are still issues to be resolved adjacent to this, but the base case now works.

* Fixed the "select all" feature for pages with multiple tables.


2.3.0 (2020-10-30)
~~~~~~~~~~~~~~~~~~

* Every part can now have assets that are added to the assets of the style and included in the head. This is particularly useful for bundling small pieces of javascript or css with the components that need them and thereby gets us closer to being able to write truly self contained "component". As a proof of concept I did so for the tables javascript parts. The naming takes care of deduplication of assets.

* Only include select2 assets when needed (possible because of the point above)

* Filtering on booleans was very broken. It always returned empty querysets and didn't produce errors when you tried to do stuff like `my_boolean<3`

* It's now possible to configure stuff on the freetext field of a query

* iommi will now grab the root page title from the text from `Header` instances in addition to `Part.title`

* Render date fields as such

* Fixed date and time formatting

* Support for optgroups in forms

* Make it possible to insert fields into the form of a query, and filters into a query

* Differentiate between primary and other actions. This should make iommi pages look more in line with the majority of design systems. If you have a custom style you probably want to add a style definition for `Action.primary`.

* Fixed a case of a silent overwrite that could be surprising. This was found during reading the code and has never happened to us in practice.

* Style fixes for bulma


2.2.0 (2020-10-16)
~~~~~~~~~~~~~~~~~~

* Fix so that style application does not alter definitions destructively. This could lead to some strange behavior if you tried to switch between styles, and it could leak over definitions between things you would not expect.

* The title of `Table` is `None` when there is no model

* Assets as first class concept. You can now insert asset definitions into your style with `assets__js=...` instead of defining a `base_template`. This change also removes the base templates for all the built in styles as they are now obsolete.

* Made it easy to hide the label of a Field by setting `display_name=None`, or `include=False`


2.1.0 (2020-10-07)
~~~~~~~~~~~~~~~~~~

* Internationalization! iommi now has i18n support and ships with English, German and Swedish languages out of the box. We welcome more translations.

* Out of the box support for the Bulma CSS framework

* Make `auto__include` specifications allow foreign key paths

* By default we now grab display_name from the model fields verbose_name (if applicable)

* Sometimes you got reordering of parts when doing a post to a form for example, this is now fixed

* The `traversable` argument to lambdas is now the leaf and not the root. This was a bug.

* Support `reverse_lazy` as url argument to MenuItem

* Two id attributes were rendered on the input tags in forms (thanks Benedikt Grundmann for reporting!)


2.0.1 (2020-09-22)
~~~~~~~~~~~~~~~~~~

* `delete_object__post_handler` accessed `instance.id` which might be valid. It should have accessed `instance.pk` which is always valid.


2.0.0 (2020-09-22)
~~~~~~~~~~~~~~~~~~

* BACKWARDS INCOMPATIBLE: `Style` must now take a `base_template` argument. This replaces the setting `IOMMI_BASE_TEMPLATE`.

* BACKWARDS INCOMPATIBLE: `IOMMI_CONTENT_BLOCK` is removed. Replaced by the `content_block` setting for `Style`.

* Allow table rows to be provided from a generator. (Disabling paginator)

* Added blocks (`iommi_head_contents`, `iommi_top`, and `iommi_bottom`) as useful hook points to add custom data in the templates if you don't need a totally new template but want to just customize a little bit.

* The default sort_key on a Column.foreign_key now looks at the searchable field of the remote field ('name' by default). This means by default sorting will mostly be more what you expect.

* Changed the error from get_search_field() for non-unique name to a warning.

* Removed <table> for layout in query advanced/simple stuff.

* Don't warn for missing register_search_fields when attr=None

* Set admin to bootstrap by default.

* Added form for changing password. Used by the admin but also usable from your code.

* Added form for login. Used by the admin but also usable from your code.

* Fixed foundation styling for query form.

* Introduced `Field.help`. This is the fragment that renders the help text for a `Field`. This means you can now style and customize this part of forms more easily. For example set a CSS class: `Field(help__attrs__class__foo='foo'`.

* Use django default date and time formatting in tables.

* New shortcut for `Table`: `Table.div` for when you want to render a `Table` as a bunch of divs. This is useful because a `Table` is really a view model of a sequence of stuff, not just a `<table>`.

* Possibility to set `Actions.tag` to `None` to not get a wrapping html tag.

* Added `Table.outer` as a tag you can style that encompasses the entire table part.

* Moved `Form.h_tag` rendering inside the form tag to make it stylable as a coherent whole.

* Grab html title from first part if no title is given explicitly. This means you'll get the `<title>` tag filled more often by what you expect automatically.

* `Template` instances are now collected properly by `Part`.

* Read admin config from modules.

* The Admin is now opt in, not opt out.

* The admin is now MUCH prettier and better.

* Actions for `Table` are now rendered above the table by default. Set `actions_below` to `True` to render them the old way.

* Many misc improvements


1.0.3 (2020-08-24)
~~~~~~~~~~~~~~~~~~

* Changed `Table.bulk_form` to `Table.bulk`. The old name was a mistake as the name was always `bulk`. This meant that styling didn't work like you expected and the pick feature also lead you down the wrong path.


1.0.2 (2020-08-21)
~~~~~~~~~~~~~~~~~~

* Support user inputted relative dates/datetimes

* Support more time formats automatically

* Introduced Filter.parse() which is a hook point for handling special parsing in the query language. The query language will no longer try to convert to integers, floats and dates for you. You have to specify a parse() method.

* Added `traversable` key to evaluate parameters. Think of it like something similar to `self`.

* `cell__format` now gets all evaluate parameters like you'd expect

* Filters: If `attr` is `None` but you've specified `value_to_q` then your filter is now included

* Various bug fixes


1.0.1 (2020-06-24)
~~~~~~~~~~~~~~~~~~

* Optimizations

* Use select2 as the default for multi_choice

* Improved usability: Make icon column behavior on falsy values more guessable

* Accidentally changed default style to foundation, change back to bootstrap

* Improved usability: Don't fall back to default template name if the user specified an explicit template name: fail on TemplateNotFound

* Style on root uses correct base template

* Allow model fields called `context`


1.0.0 (2020-06-10)
~~~~~~~~~~~~~~~~~~

* Backwards incompatible: `register_search_fields` replaces `register_name_field`. This new system is a list of field names and not just a single field. There is also new searching and filtering behavior based on this that means you will get better search results

* Backwards incompatible: `field_name` as used by model factories is replaced with `model_field_name`. If you used `register_factory` you will need to change this. The field names on `Column`, `Field` and `Filter` are also renamed.

* Support fields named `keys`, `value` or `items` on Django models

* Added basic styling support for CSS frameworks Water and Foundation

* Fix include to make None mean False

* Change Filter.text to search using icontains instead of iexact by default in the basic search mode

* Change post_validation callback to receive standard evaluate parameters

* Improved help text for queries

* Field.radio was broken in the bootstrap style: it specified the input template as the template for the entire field, so the label got erased


0.7.0 (2020-05-22)
~~~~~~~~~~~~~~~~~~

* Fixed default text argument to Fragment

* Fixed issue where endpoint dispatch parameter was left over in the pagination and sorting links

* Parts that are None should not be collected. This affected the admin where it printed "None" below the "Admin" link.

* Added header for bulk edit form in tables

* Fixed textarea readonly when field is not editable

* Fixed is_paginated function on Paginator

* Add request to evaluate parameters

* Make evaluate and evaluate_recursive match even the `**_` case by default

* No dispatch command on a POST is invalid and will now produce an error

* Lazy bind() on members. This is a performance fix.

* Fixed bug where display_name could not be overridden with a lambda due to incorrect evaluate handling

* Removed Table.rendered_columns container. You have to look at the columns and check if they have render_column=False


0.6.2 (2020-04-22)
~~~~~~~~~~~~~~~~~~

* Fixed data-endpoint attribute on table


0.6.1 (2020-04-21)
~~~~~~~~~~~~~~~~~~

* Fixed tbody endpoint and added a div to make the endpoint easier to use


0.6.0 (2020-04-17)
~~~~~~~~~~~~~~~~~~

* Fixed an issue where fragments couldn't be customized later if built with the `html` builder

* `Action` inherits from `Fragment`. This should be mostly transparent.

* You can now pass multiple argument to `Fragment`/`html.foo()`. So `html.div('foo', 'bar')` is now valid and creates two child nodes `child0` and `child1`

* Uncouple `auto__*` from `row` parameter. `auto__` only suggests a default. This avoids some confusion one could get if mixing `auto__rows`, `auto__models` and `rows` in some ways.

* Fixed setting active on nested submenus where the parent had url None


0.5.0 (2020-04-01)
~~~~~~~~~~~~~~~~~~

* Include iommi/base_bootstrap.html and iommi/base_semantic_ui.html in package, and use them if no base.html is present. This improves the out of the box experience for new projects a lot

* Support mixing of `auto__model`/`auto__row` based columns and declarative columns

* Support attrs__class and attrs__style as callables

* Added support for context namespace on Page, which is passed to the template when rendering (for now only available on the root page)

* Fixed how we set title of bulk edit and delete buttons to make configuration more obvious


0.4.0 (2020-03-30)
~~~~~~~~~~~~~~~~~~

* Fixed rendering of grouped actions for bootstrap

* Respect auto__include order

* boolean_tristate should be the default for the Field of a Column.boolean

* New class Header that is used to automatically get h1/h2/etc tags according to nesting of headers

* Table.rows should be able to be evaluated

* Added feature that you can type 'now' into date/datetime/time fields

* Feature to be able to force rendering of paginator for single page tables

* Paginator fixes: it's now no longer possible to use the Django paginator, but the iommi paginator is more full features in trade.

* Removed jQuery dependency for JS parts

* Big improvements to the Menu component

* filters that have freetext mode now hide their field by default

* Added "pick" in the debug toolbar. This is a feature to quickly find the part of the document you want to configure

* Introduced Form.choice_queryset.extra.create_q_from_value

* Changed so that Query defaults to having the Field included by default

* Renamed BoundRow/bound_row to Cells/cells

* Major improvements to the admin

* Lots and lots of cleanup and bug fixes
