Changelog
=========

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

