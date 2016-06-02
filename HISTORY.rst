Changelog
=========

2.0.0 (2016-06-02)
~~~~~~~~~~~~~~~~~~

* Cache form on Query

* Render global form errors

* Query.form() no longer takes a request parameter, since it was redundant anyway. This is a potential breaking change.

* Correctly dispatch attr to underlying tri.form

* Support for ajax backend. New parameter to Query: endpoint_dispatch_prefix.



1.11.0 (2016-04-25)
~~~~~~~~~~~~~~~~~~~

* Minor bugfix for variable-from-model handling of auto fields


1.10.0 (2016-04-21)
~~~~~~~~~~~~~~~~~~~

* Fix over-eager assert not allowing variable-less Query objects.


1.9.0 (2016-04-21)
~~~~~~~~~~~~~~~~~~

* Enable mixing variable definitions in both declared variables and class meta.

* Added `after` attribute on `Variable` to enable custom variable ordering (See `tri.declarative.sort_after()`)

* Added Variable.from_model, Query.from_model


1.8.0 (2016-04-19)
~~~~~~~~~~~~~~~~~~

* Added robustness in when arguments are passed as `dict(foo=dict(bar=17))` or `foo__bar=17`


1.7.0 (2016-04-08)
~~~~~~~~~~~~~~~~~~

* Add python 3 support


1.6.0 (2016-03-03)
~~~~~~~~~~~~~~~~~~

* `Variable.float` shortcut added
  
* Add support for Django 1.7 and 1.8.

