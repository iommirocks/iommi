Changelog
---------

5.1.1 (2020-02-11)
------------------

* Improve namespace merge in @with_meta to not trip up @declarative


5.1.0 (2020-02-11)
------------------

* Fix @with_meta argument injector to merge namespaces


5.0.1 (2019-02-03)
------------------

* A minor update to the documentation generation to make it play nice with rST


5.0.0 (2019-01-30)
------------------

* Added private field to shortcuts: `__tri_declarative_shortcut_stack`. This is useful to be able to figure out a shortcut stack after the fact

* `get_callable_description` thought stuff that contained a lambda in its string representation was a lambda

* Removed all deprecated APIs/behaviors:
    * `creation_ordered`
    * The promotion of string values to keys in `Namespace`

* Much improved error messages


4.0.1 (2019-10-23)
------------------

* Bugfix to correctly handle Namespace as callable/not callable depending on content


4.0.0 (2019-10-11)
------------------

* `get_meta()` now collects extra arguments in a `Namespace` to get consistent override behaviour.

* `should_show` no longer accepts a callable as a valid return value. It will assert on this, because it's always a mistake.

* Added `evaluate_strict` and `evaluate_recursive_strict` that will not accept callables left over after the evaluation. If possible prefer these methods because they will stop the user of your library from making the mistake of not matching the given signature and ending up with an unevaluated callable in the output.


3.1.0 (2019-06-28)
------------------

* Fixed issues when Namespace contained a key called any of items, values, keys, or get

* Removed sorting on Namespace kwargs that isn't needed in python 3 anymore. The sorting also destroys the given order which can be surprising

* Removed old obsolete functions collect_namespaces, extract_subkeys, and setdefaults


3.0.0 (2019-06-10)
------------------

* Renamed module from `tri.declarative` to `tri_declarative`. This is a breaking change

* Dropped support for python2


2.0.0 (2019-04-12)
------------------

* Fixed `get_signature` cache to not pollute struct-like dicts

* New call_target semantics for class method shortcuts, this is a potential breaking change


1.2.1 (2019-13-15)
------------------

* Improved documentation output


1.2.0 (2019-13-14)
------------------

* Add get_members function to enable reuse of @declarative attribute collection

* Add @class_shortcut decorator to enable @with_meta aware class shortcuts


1.1.0 (2018-11-22)
------------------

* Added `generate_rst_docs` function.


1.0.6 (2018-09-28)
------------------

* `Shortcut` is now a special case when merging `Namespace` objects.
  When already in a Namespace, a Shortcut now get overwritten by `setitem_path()`, not merged into the written value.


1.0.5 (2018-09-21)
------------------

* Fix broken handling of empty key


1.0.4 (2018-09-21)
------------------

* Cleanup Namespace path logic and make sure it is symmetrical and tested.

* Added deprecation warning on string to dict promotion on namespace merge.


1.0.3 (2018-06-26)
~~~~~~~~~~~~~~~~~~

* Fixed release functionality


1.0.2 (2018-06-18)
~~~~~~~~~~~~~~~~~~

* Don't support `RefinableObject` in `evaluate_recursive`. This was a mistake.


1.0.1 (2018-06-15)
~~~~~~~~~~~~~~~~~~

* Support `RefinableObject` in `evaluate_recursive`.


1.0.0 (2018-05-23)
~~~~~~~~~~~~~~~~~~

* Cleanup deprecation warnings from inspect.getargspec


0.34.0 (2017-08-21)
~~~~~~~~~~~~~~~~~~~

* Fix bug in 0.33.0 when promoting callable to `Namespace`.


0.33.0 (2017-08-21)
~~~~~~~~~~~~~~~~~~~

* Fix bug when promoting callable to `Namespace`.

* Fix handling of `EMPTY` marker.


0.32.0 (2017-07-04)
~~~~~~~~~~~~~~~~~~~

* Added promoting callable namespace members to `Namespace` with `call_target` in 
  `setdefaults_path`.


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

* Fixed loop detection in flatten for `Namespace`\ s. This resulted in data
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

