Changelog
---------

1.0.0 (2020-01-??)
~~~~~~~~~~~~~~~~~~

* Initial release of iommi. This is a merge of the libraries tri.form, tri.query, and tri.table.


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
