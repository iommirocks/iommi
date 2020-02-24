Registrations
=============

To make iommi understand the specifics of your code base you can register various handlers and behaviors.

.. contents::
    :local:

Django custom fields
~~~~~~~~~~~~~~~~~~~~

To tell iommi how to handle your custom fields you have these options:


* `register_factory`: register behavior for everything at once
* `register_column_factory`: specific to `Column`
* `register_filter_factory`: specific to `Variable`
* `register_field_factory`: specific to `Field`


You use the `register_factory` function to register your own factory. The simplest way is:

.. code:: python

    register_factory(
        TimeField,
        shortcut_name='time'
    )

When iommi then sees a Django `TimeField` it will call the `Column.time` shortcut to create a column, `Variable.time` to create a `Variable` and `Field.time` to create a field.

I you need different behavior for the three classes you need to use the more specific registration functions.

You can also register `None` to tell iommi to just ignore the field type whenever it sees it.

For more advanced behavior you can pass a `Shortcut` instance or a callable that returns a shortcut. This is the iommi definition for booleans:


.. code:: python

    register_field_factory(
        BooleanField,
        factory=lambda model_field, **kwargs: (
            Shortcut(call_target__attribute='boolean')
            if not model_field.null
            else Shortcut(call_target__attribute='boolean_tristate')
        )
    )


Rendering of your custom types in a table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

iommi renders `bool`, `list`, `set`, `tuple`, `QuerySet` and any type that has a `__html__` method with special logic to make it look nice in a table. If you have a type where you can't or don't want to implement a `__html__` method (or you want more complex rendering) you can plug into this system yourself with `register_cell_formatter`:

.. code:: python

    register_cell_formatter(MyType, lambda value, **_: f'hello {value}')

The callable you register gets the keyword arguments `value`, `table`, `column` and `row`.


The name field of your Django models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When searching for an object with `Query` we need to know which field is the canonical name field. This enables the advanced query language to be `my_car_brand='toyota'` instead of `my_car_brand.pk=42` which is a lot nicer. iommi will automatically use a field called `name` if it exists and is unique. If you have another name field that is also unique you can register it like this:


.. code:: python

    register_name_field(User, 'username')

On startup iommi registers just this one particular canonical name for you since you probably want it. Note also that you can can use `__` separated paths here if you have a one-to-one with another model where the name field exists.


Custom styles
~~~~~~~~~~~~~

You can register your own styles with `register_style`. By default the style `bootstrap` is used. You can use it as the basis of your custom look and feel or start with the `base` style and work from there.


