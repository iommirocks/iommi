Changelog
---------

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
