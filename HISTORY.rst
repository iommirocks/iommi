Changelog
---------

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

* Make evaluate and evaluate_recursive match even the **_ case by default

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
