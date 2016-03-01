Changelog
=========


0.21.0 (2016-03--01)
~~~~~~~~~~~~~~~~~~~~

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

