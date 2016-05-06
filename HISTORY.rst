Changelog
=========

0.25.0 (2016-05-06)
~~~~~~~~~~~~~~~~~~~

* Added `EMPTY` marker to `setdefaults_path` to avoid mixup when empty dict is 
  provided in function defaults.


0.25.0 (2016-04-28)
~~~~~~~~~~~~~~~~~~~

* Added @dispatch decorator


0.24.0 (2016-04-20)
~~~~~~~~~~~~~~~~~~~

* Fix bug in `setdefault_path` tripping up on key ordering.

* Dropped `namespace_factory` keyword argument to `setdefaults_path` not likely
  ever beeing used.


0.23.0 (2016-04-15)
~~~~~~~~~~~~~~~~~~~

* `setdefaults_path` now accepts multiple default dicts. (To simplify the pattern of
  shortcuts in tri.form, tri.query and tri.table where we now will end up with:
  `new_kwargs = setdefaults_path(Struct(), kwargs, dict(....))`


0.22.0 (2016-03-24)
~~~~~~~~~~~~~~~~~~~

* `sort_after()` should produce an error when attempting to sort after non-existant keys
  
* Tweaked namespace merge in `setdefaults_path`


0.21.0 (2016-03-01)
~~~~~~~~~~~~~~~~~~~

* Fix corner case in collect_namespaces where one parameter imply a value and
  others imply a namespace.

* Added `setdefaults_path` helper with `__` namespace traversal.


0.20.0 (2016-02-29)
~~~~~~~~~~~~~~~~~~~

* Added `assert_kwargs_not_empty` convenience function.

* Improved documentation.


0.19.0 (2016-01-12)
~~~~~~~~~~~~~~~~~~~

* When making instances of a class decorated with `@declarative` the declared
  values are copied (shallow) before being passed to `__init__`.

* Instances will get an own copy of the declared attributes written to their
  `__dict__`

