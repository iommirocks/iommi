Changelog
=========

1.12.0 ()
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
