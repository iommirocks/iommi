Changelog
---------

7.0.0 (2019-06-10)
~~~~~~~~~~~~~~~~~~

* Renamed package from `tri.form` to `tri_form`. This is a breaking change

* Dropped python2 support

* Dropped Django < 2.0 support


6.0.2 (2019-06-03)
~~~~~~~~~~~~~~~~~~

* Changed the default value for `parse_emtpy_string_as_none` to be based on the model fields `null` property.

* `from_model` should not overwrite defaults too early

* `Field.choice` now has a sane default parser using `choice_to_option`

* Changed render_attrs to stop you from making some common mistakes

* Fixed `time_render_value()`

* Fixes and improved tests for from_model_expand

* Fixed `from_model` for Django `TextField`. Should be `Field.textarea`, not `Field.text`


6.0.1 (2019-05-06)
~~~~~~~~~~~~~~~~~~

* Fixed cases where from_model lost the type when inheriting


6.0.0 (2019-04-12)
~~~~~~~~~~~~~~~~~~

* Make `Field` shortcuts compatible with subclassing. Previous fix didn't work all the way.

* Use the new major tri.declarative, and update to follow the new style of class member shortcuts

* Major fixes to how `from_model` works. Subclassing `Form` and `Field` now works like you'd expect. This is a breaking change.

* Removed `Field.comma_separated` shortcut. This was never used, and poorly tested.

5.4.0 (2019-04-01)
~~~~~~~~~~~~~~~~~~

* Make `Field` shortcuts compatible with subclassing


5.3.1 (2019-03-20)
~~~~~~~~~~~~~~~~~~

* Fix that Django's DoesNotExist events don't leak out of the field-validation code


5.3.0 (2019-02-18)
~~~~~~~~~~~~~~~~~~

* If you subclass Form this custom class is now used properly in the `from_model` code paths

* `Form` now has a refinable attribute `field_class` which you should use to point to your `Field` subclass if you have one. This is best accomplished in the `Meta` class on the class inheriting from `Form`.

* Added `Form.create_or_edit_object` that will respect your subclass if you have one.


5.2.2 (2019-01-28)
~~~~~~~~~~~~~~~~~~

* Fixed escaping bug introduced in 5.2.0: You could get a KeyError crash if you had `{` and `}` in attributes.


5.2.1 (2019-01-16)
~~~~~~~~~~~~~~~~~~

* Fixed coverage build (this also broke the travis build and as a consequence the pypi release process)


5.2.0 (2019-01-16)
~~~~~~~~~~~~~~~~~~

* Rendering of submit button is now a `Link` and you can now supply your own buttons and links here.

* Fixed crash in rendering fields in some cases. This was due to an incorrect use of `format_html`.

* Flask and Jinja2 support

* Updated examples for modern django, and added an example

* Modernize attrs rendering on Field (this introduces a few deprecations)

* render_attrs support for style attributes. This means you can now do `Link(attrs__style__display='none')` for example.


5.1.1 (2018-10-23)
~~~~~~~~~~~~~~~~~~

* File field tried to render the binary contents on form validation errors. This is a crash in Django 2.1

* `from_model` was broken when traversing a foreign key relation with `__`


5.1.0 (2018-10-09)
~~~~~~~~~~~~~~~~~~

* Dropped Django 1.8 support

* Fixed deprecation warnings for Django 2.0


5.0.12 (2018-10-03)
~~~~~~~~~~~~~~~~~~~

* Added `Field.boolean_tristate` for editing boolean fields with null value allowed


5.0.11 (2018-09-21)
~~~~~~~~~~~~~~~~~~~

* Simplified `MISSING` definition


5.0.10 (2018-06-29)
~~~~~~~~~~~~~~~~~~~

* Fix evaluation of Link attributes


5.0.9 (2018-06-19)
~~~~~~~~~~~~~~~~~~

* Fixed python3 compability for release check.
* Fixed release check on shallow git clone

5.0.8 (2018-06-19)
~~~~~~~~~~~~~~~~~~

* Fixed release functionality

5.0.7 (2018-06-18)
~~~~~~~~~~~~~~~~~~

* Stepped tri.declarative dependency.


5.0.6 (2018-06-15)
~~~~~~~~~~~~~~~~~~

* Fix non-editable mode on multi_choice fields.

* member_from_model support for __ paths.

* Made `Link` attributes lazy on form parameter.


5.0.5 (2018-04-11)
~~~~~~~~~~~~~~~~~~

* Fix form submit link rendering.


5.0.4 (2017-10-16)
~~~~~~~~~~~~~~~~~~

* Revert new default parser on `Field.choice`.


5.0.3 (2017-10-16)
~~~~~~~~~~~~~~~~~~

* Improve default parser implementation on `Field.choice`. A reasonable implementation of `__str__` is enough for objects in `choices`.

* Fix evaluation order so that `Field.initial`/`Field.initial_list` is available when fields are evaluated. (`Field.show` is still invoked early)


5.0.2 (2017-10-06)
~~~~~~~~~~~~~~~~~~

* `Field.from_model` produced incorrect parser for foreign keys.


5.0.1 (2017-09-15)
~~~~~~~~~~~~~~~~~~

* Correctly check unique constraints when editing object

* Bug where `form.instance` was set too late in `Form` constructor, resulting in `AttributeError` in certain lambdas


5.0.0 (2017-08-22)
~~~~~~~~~~~~~~~~~~

* Refactored to use new tri.declarative: using `RefinableObject`, `Shortcut`, and the new `call_target` parameter of `Namespace`

* Changed dispatch separator from `__` to `/`

* Changed `label` on `Field` to `display_name`. This is in line with tri.query and tri.table.

* `Field.choice` incorrectly handles post_validation (fixes github issue #9)

* `Form` now doesn't try to read initial data and form data from Fields that are show=False

* `create_or_edit_object` doesn't take a parameter `render_context` anymore, use `render__context`

* You no longer need to specify the `model` parameter to `choice_queryset` or `multi_choice_queryset` if you give it a `QuerySet` as `choices` (as opposed to giving a callable)

* `Field.choice_queryset` and `Field.multi_choice_queryset` now reevaluates the QuerySet on each usage (fixes tri.table github issue 16)


4.10.1 (2017-06-20)
~~~~~~~~~~~~~~~~~~~

* Bugfix: `on_save` callback for `create_or_edit_object` was missing `form` parameter


4.10.0 (2017-06-12)
~~~~~~~~~~~~~~~~~~~

* Fixed bug where namespaced form was not rendered when the other namespaced form had an error


4.9.0 (2017-05-31)
~~~~~~~~~~~~~~~~~~

* Added attribute 'name' to Form in order to namespace POSTs in cases where there are more than one form


4.8.0 (2017-05-23)
~~~~~~~~~~~~~~~~~~

* Added useful return value on `Form.apply(...)`

* Improve repr on `Field`

* Added `Form.editable` settings for setting all fields at once


4.7.1 (2017-04-24)
~~~~~~~~~~~~~~~~~~

* Bugfix for endpoint dispatch: we must allow a result to be an empty list/dict


4.7.0 (2017-04-24)
~~~~~~~~~~~~~~~~~~

* Added `Link` class, and redefined the submit button on the form in terms of a `Link`

* Fixed incorrect handling of template rendering and `RequestContext` between django before and after 1.10

* Dropped official support of django 1.7

* Added `attrs` member on `Form`, and added method `render_attrs` that you use to render the attributes into html

* Added six as a dependency


4.6.2 (2017-04-18)
~~~~~~~~~~~~~~~~~~

* Fixed `render_attrs` to escape quotation marks


4.6.1 (2017-04-11)
~~~~~~~~~~~~~~~~~~

* Fixed non-editable fields so that you can override the rendering

* Fixed bug where raw_data was sent to render_value when there was an error on the field


4.6.0 (2017-03-15)
~~~~~~~~~~~~~~~~~~

* `Field` class now inherits from `object`, making the implementation more pythonic.
  (Attributes still possible to override in constructor call, see `NamespaceAwareObject`)

* Added `Form.extra` namespace for custom data.


4.5.0 (2016-12-19)
~~~~~~~~~~~~~~~~~~

* Add `raw_data` and `raw_data_list` attributes to `Field` definition to enable custom handling on django file download


4.4.0 (2016-12-13)
~~~~~~~~~~~~~~~~~~

* Set instance on form just after save to be able to use newly created pk in a redirect


4.3.1 (2016-12-08)
~~~~~~~~~~~~~~~~~~

* Prevent code from running on import


4.3.0 (2016-10-20)
~~~~~~~~~~~~~~~~~~

* Lazy evaluation of select choices.


4.2.0 (2016-10-06)
~~~~~~~~~~~~~~~~~~

* Add `endpoint` namespace to `Form` and `Field` constructor to add custom endpoint callbacks.

* Add `config` and `validate` endpoint implementations


4.1.0 (2016-09-20)
~~~~~~~~~~~~~~~~~~

* Fix formatting of form field error output when there are multiple field errors

* Fix bug in form validation signaling required field missing on choices where the value is falsy, e.g. 0

* Implement djangos uniqueness validation on save in forms/views.py

* Fixed input type on url field


4.0.0 (2016-09-14)
~~~~~~~~~~~~~~~~~~

* Improved handling of `from_model`. You can now do the following without issues:

.. code:: python

    form = Form.from_model(field__foo__class=Form.integer)

* The incorrectly named parameter `db_field` to `Form.fields_from_model` has been renamed to the correct `field`.

* The parameter `db_field` to `create_members_from_model` has been renamed to `member_params_by_member_name`.

* Better logic for figuring out which mode we're in when POST-ing

* Allow `None` as `endpoint_dispatch_prefix`.


3.8.0 (2016-09-12)
~~~~~~~~~~~~~~~~~~

* Fixed namespace dispatch bugs in `create_or_edit_object`


3.7.0 (2016-08-17)
~~~~~~~~~~~~~~~~~~

* Compatible with Django 1.9 & 1.10


3.6.0 (2016-08-16)
~~~~~~~~~~~~~~~~~~

* Field.datetime is more forgiving in the formats it receives: it will not accept ISO8601 formats but missing seconds or seconds+minutes

* Field.boolean field didn't respect specified input_template

* Inputs that were parsed to lists where the field was a list now works properly: None is not passed to the validation function.

* Fixed pypi rendering of documentation

* More honest coverage numbers


3.5.0 (2016-06-16)
~~~~~~~~~~~~~~~~~~

* Added `is_full_form` parameter to form to optionally control the rendering of the "-"="-" marker form field


3.4.0 (2016-06-15)
~~~~~~~~~~~~~~~~~~

* Added better error messages when missing django model mappings

* Fix population of read-only fields from initial value


3.3.0 (2016-06-02)
~~~~~~~~~~~~~~~~~~

* bugfixes


3.2.0 (2016-05-26)
~~~~~~~~~~~~~~~~~~

* default_help_text should not blow up on invalid references

* Removed some dead code


3.1.0 (2016-05-26)
~~~~~~~~~~~~~~~~~~

* Fixed confusing naming of Field.text to Field.textarea

* Support for ajax backend. New parameters to Field: endpoint_path and endpoint_dispatch. For now only implemented for Field.choice_queryset and tailored for select2. To use it: specify template_name='tri_form/choice_select2.html'.


3.0.0 (2016-05-26)
~~~~~~~~~~~~~~~~~~

* Parse modes introduced. This fixes validation of partially submitted forms, using tri.form for filters and other problems.

* Refactored to use tri.declarative @dispatch

* Added __field__ endpoint handling. This is useful for e.g. loading choices with ajax instead of up front.

* Form.errors is now a set

* views.create_object/edit_object/create_or_edit_object now default parameter `render` to render_to_response instead of render_to_string. This is a potential braking change.


2.2.0 (2016-04-25)
~~~~~~~~~~~~~~~~~~

* Minor bugfix for fields-from-model handling of auto fields


2.1.0 (2016-04-20)
~~~~~~~~~~~~~~~~~~

* Fix broken blank field value on fields from django model when django model
  blank setting is True.


2.0.0 (2016-04-18)
~~~~~~~~~~~~~~~~~~

* Changed Form.from_model method to require database field kwargs under `field__` namespace. This is a breaking change.

* Fixed saving of foreign keys in django create view

* Enable mixing column definitions in both declared fields and class meta.


1.16.0 (2016-04-15)
~~~~~~~~~~~~~~~~~~~

* Fix table mode render in python 2


1.15.0 (2016-04-08)
~~~~~~~~~~~~~~~~~~~

* Fixed radio button render


1.14.0 (2016-04-01)
~~~~~~~~~~~~~~~~~~~

* Added python 3 support

* Added render helper functions for reuse by tri.table et al


1.13.0 (2016-03-10)
~~~~~~~~~~~~~~~~~~~

* Fixed many_to_one field


1.12.0 (2016-03-03)
~~~~~~~~~~~~~~~~~~~

* Add support for Django 1.8


1.11.0 (2016-02-29)
~~~~~~~~~~~~~~~~~~~

* Datetime fields used to not roundtrip cleanly via the form (they output
  milliseconds then failed on parsing them) Field.file didn't exist.

* Changed syntax for specifying html attributes and classes. They are now use
  the same way of addressing as other things, e.g.:
  Field.choice(attrs__foo="bar", attrs__class__baz=True) will yield something
  like `<select ... class="baz" foo=bar>...</select>`


1.10.0 (2016-02-08)
~~~~~~~~~~~~~~~~~~~

* Made sure form validation is only run once

* Fixed input form class and render context to create_or_edit_object view


1.9.0 (2016-01-15)
~~~~~~~~~~~~~~~~~~

* Fixed default value initialization on Field attributes to not reuse containers.

* Added support for ManyToManyField when generating forms for model objects.

* Added 'read_from_instance' and 'write_to_instance' callbacks for customized instance marshalling.


1.8.0 (2016-01-13)
~~~~~~~~~~~~~~~~~~

Bugfix release.

* Added missing 'after' attribute on Field prohibiting form order customization

* Fixed default value handling of 'attr' to make None a valid value when no attribute should be read.

* Fixed CSS handling on required fields.


1.7.0 (2016-01-13)
~~~~~~~~~~~~~~~~~~

* Made evaluation of choices lazy even when there is a None alternative.
