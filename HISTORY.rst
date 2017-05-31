Changelog
---------

0.31.0 (2017-06-15)
~~~~~~~~~~~~~~~~~~~

* Improve `sort_after` to allow more combinations of `after=...` specifications.
  e.g. by name of an entry also moved by spec.

* Changed name of first parameter of `setdefaults_path` to `__target__` to avoid
  collitions with namespace parameters.

* Added `RefinableObject` base for reuse by classes wanting to be able to be configured
  via constructor kwarg parameters in a declarative fashion. (The namespace of possible 
  constructor overrides are declared with `Refinable()` for values and the decorator 
  `@refinable` for methods.

* Added first incarnation of crawling the definitions to recursively find available 
  parameters on objects and their aggregates.

* Added `Shortcut` abstraction to be able to find pre-defined set of overrides of 
  `RefinableObject` classes.


0.30.0 (2017-02-10)
~~~~~~~~~~~~~~~~~~~

* `evaluate` and `evaluate_recursive` also works for methods as well as for functions.


0.29.0 (2016-09-12)
~~~~~~~~~~~~~~~~~~~

* Fixed loop detection in flatten for `Namespace`s. This resulted in data
  corruption.


0.28.0 (2016-07-15)
~~~~~~~~~~~~~~~~~~~

* Added `Namespace` subclass of `tri.struct.Struct` to explicit capture the
  path splitting semantics. (And added method for flattening a `Namespace` back
  to path notation.)


0.27.0 (2016-07-13)
~~~~~~~~~~~~~~~~~~~

* Fix bug in `evaluate` signature detection with optional arguments. 
  (`lambda a, b=17: a+b` was correctly matched but `lambda b, a=17: a+b` was not)


0.26.0 (2016-05-06)
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

