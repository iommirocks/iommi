Changelog
---------

4.1.0 (2017-03-22)
~~~~~~~~~~~~~~~~~~

* `Column` class now inherits from `object`, making the implementation more pythonic.
  (Attributes still possible to override in constructor call, see `NamespaceAwareObject`)

* `*.template` overrides can now be specified as `django.template.Template` instances.

* The `template_name` parameter to `render_table` is now deprecated and superceeded by a `template` parameter.


4.0.0 (2016-09-15)
~~~~~~~~~~~~~~~~~~

* Updated to newest tri.form, tri.query, tri.declarative. This gives us simpler factories for `from_model` methods.

* Added shortcuts to `Column`: `time` and `decimal`

* The following shortcuts have been updated to use the corresponding `Variable` shortcuts: date, datetime and email

* Fix failure in endpoint result return on empty payload.
  `[]` is a valid endpoint dispatch result.

* `render_table`/`render_table_to_response` no longer allow table to be passed as a positional argument


3.0.1 (2016-09-06)
~~~~~~~~~~~~~~~~~~

* Fix crash on unidentified sort parameter.


3.0.0 (2016-09-02)
~~~~~~~~~~~~~~~~~~

* `bound_row` is passed to row level callables. This is a potential breaking
  change if you didn't do `**_` at the end of your function signatures (which you
  should!)

* `bound_row` and `bound_column` is passed to cell level callables. This is a
  potential breaking change like above.

* `BoundRow` now supports `extra`.

* compatibible with Django 1.9 & 1.10

* Added strict check on the kwargs config namespace of `Table`

* Added `extra` namespace to `Table`

* Added `bound_cell` parameter to rendering of cell templates.


2.5.0 (2016-07-14)
~~~~~~~~~~~~~~~~~~

* Added optional `endpoint_dispatch_prefix` table configuration to enable multiple
  tables on the same endpoint.


2.4.0 (2016-07-13)
~~~~~~~~~~~~~~~~~~

* Made more parts of `BoundCell` available for reuse.


2.3.0 (2016-07-12)
~~~~~~~~~~~~~~~~~~

* Added pass-through of extra arguments to `Link` objects for custom attributes.


2.2.0 (2016-06-23)
~~~~~~~~~~~~~~~~~~

* Fix missing namespace collection for column custimization of Table.from_model


2.1.0 (2016-06-16)
~~~~~~~~~~~~~~~~~~

* Renamed `db_compat.register_field_factory` to the clearer `register_column_factory`

* Improved error reporting on missing django field type column factory declaration.

* Added iteration interface to table to loop over bound rows

* Added `endpoint` meta class parameter to table to enable custom json endpoints


2.0.0 (2016-06-02)
~~~~~~~~~~~~~~~~~~

* Support for ajax backend

* Dependent tri.form and tri.query libraries have new major versions


1.16.0 (2016-04-25)
~~~~~~~~~~~~~~~~~~~

* Minor bugfix for fields-from-model handling of auto fields


1.15.0 (2016-04-21)
~~~~~~~~~~~~~~~~~~~

* Table.from_model implemented


1.14.0 (2016-04-19)
~~~~~~~~~~~~~~~~~~~

* Added `after` attribute on `Column` to enable custom column ordering (See `tri.declarative.sort_after()`)

* Enable mixing column definitions in both declared fields and class meta.

* Don't show any results if the form is invalid


1.13.0 (2016-04-08)
~~~~~~~~~~~~~~~~~~~

* Add python 3 support


1.12.0 (2016-02-29)
~~~~~~~~~~~~~~~~~~~

* Changed syntax for specifying html attributes and classes. They are now use the same way of addressing as
  other things, e.g.: Column(attrs__foo="bar", attrs__class__baz=True) will yield something like
  `<th class="baz" foo=bar>...</th>`


1.11.0 (2016-02-04)
~~~~~~~~~~~~~~~~~~~

* Fix missing evaluation of row__attr et al.


1.10.0 (2016-01-28)
~~~~~~~~~~~~~~~~~~~

* Changed cell__template and row__template semantics slightly to enable customized cell ordering in templates.

  row__template implementations can now access a BoundCell object to use the default cell rendering.

  cell__template implementation are now assumed to render the <td> tags themself.


1.9.0 (2016-01-19)
~~~~~~~~~~~~~~~~~~

* Fixed to work with latest version of tri.form
