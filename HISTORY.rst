Changelog
---------

6.1.0 (2019-10-14)
~~~~~~~~~~~~~~~~~~

* Bumped dependency for tri.declarative

* Bumped dependency for tri.form


6.0.0 (2019-06-14)
~~~~~~~~~~~~~~~~~~

* Renamed module from `tri.query` to `tri_query`

* Dropped support for python 2 and django < 2.0


5.0.2 (2019-05-03)
~~~~~~~~~~~~~~~~~~

* Fixed cases where from_model lost the type when inheriting


5.0.1 (2019-04-25)
~~~~~~~~~~~~~~~~~~

* Fixed `multi_choice_queryset` when selecting multiple items and also filtering on some other field at the same time.


5.0.0 (2019-04-12)
~~~~~~~~~~~~~~~~~~

* Make `Variable` shortcuts compatible with subclassing

* Use the new major tri.declarative, and update to follow the new style of class member shortcuts

* Added missing `Variable.multi_choice` shortcut


4.2.1 (2019-04-25)
~~~~~~~~~~~~~~~~~~

* Fixed `multi_choice_queryset` when selecting multiple items and also filtering on some other field at the same time.


4.2.0 (2019-04-01)
~~~~~~~~~~~~~~~~~~

* Make Variable shortcuts compatible with subclassing


4.1.0 (2019-02-18)
~~~~~~~~~~~~~~~~~~

* http endpoint for query validation errors: `query/errors`


4.0.4 (2018-10-23)
~~~~~~~~~~~~~~~~~~

* Support searching for quotation mark


4.0.3 (2018-10-10)
~~~~~~~~~~~~~~~~~~

* A more helpful error message if you didn't specify `value_to_q_lookup` but you need to.

* Removed buggy use of `setdefaults`. This could cause overriding of nested arguments to not take.



4.0.2 (2018-10-04)
~~~~~~~~~~~~~~~~~~

* Added `Variable.boolean_tristate` for editing boolean fields with null value allowed


4.0.1 (2018-09-21)
~~~~~~~~~~~~~~~~~~

* Made Query a `RefinableObject`


4.0.0 (2017-08-22)
~~~~~~~~~~~~~~~~~~

* Moved to tri.declarative 0.34 and tri.form 5.0

* Note that `gui__class` to specify a constructor/callable is no longer a valid parameter, because of updated tri.form. Use `gui__call_target` or just `gui`.

* You no longer need to specify the `model` parameter to `choice_queryset` or `multi_choice_queryset` if you give it a `QuerySet` as `choices` (as opposed to giving a callable)


3.3.0 (2017-04-27)
~~~~~~~~~~~~~~~~~~

* Move default behaviors out from the shortcuts so they can be used externally

* Removed jquery dependency for toggling simple/advanced filtering

* Removed support for Django 1.7


3.2.0 (2017-03-22)
~~~~~~~~~~~~~~~~~~

* `Variable` class now inherits from `object`, making the implementation more pythonic.
  (Attributes still possible to override in constructor call, see `NamespaceAwareObject`)


3.1.0 (2016-09-19)
~~~~~~~~~~~~~~~~~~

* Moved to the simplified factory system for `from_model`

* Added shortcuts to `Variable`: url, time, datetime, date, email, decimal


3.0.0 (2016-09-14)
~~~~~~~~~~~~~~~~~~

* Updated to latest major tri.form


2.2.0 (2016-08-16)
~~~~~~~~~~~~~~~~~~

* Variable.choice_queryset handles the string "null" the same way as everything else

* Queries that have multi-select inputs now work


2.1.1 (2016-08-08)
~~~~~~~~~~~~~~~~~~

* Report invalid operators for choice queryset as errors instead of crashing


2.1.0 (2016-07-12)
~~~~~~~~~~~~~~~~~~

* Check for dates that are out of range


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

