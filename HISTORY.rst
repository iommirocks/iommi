Changelog
---------

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
