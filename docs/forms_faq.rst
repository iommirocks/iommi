Forms FAQ
=========

How do I supply a custom parser for a field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable to the `parse` member of the field:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__parse=lambda field, string_value, **_: int(string_value),
    )

How do I make a field non-editable?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable or `bool` to the `editable` member of the field:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__editable=
            lambda field, form, **_: form.request().user.is_staff,
        fields__bar__editable=False,
    )

How do I make an entire form non-editable?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a very common case so there's a special syntax for this: pass a `bool` to the form:

.. code:: python

    form = Form.from_model(
        model=Foo,
        editable=False,
    )

How do I supply a custom validator?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable that has the arguments `form`, `field`, and `parsed_data`. Return a tuple `(is_valid, 'error message if not valid')`.

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__is_valid=
            lambda form, field, parsed_data: (False, 'invalid!'),
    )

How do I exclude a field?
~~~~~~~~~~~~~~~~~~~~~~~~~

See `How do I say which fields to include when creating a form from a model?`_

How do I say which fields to include when creating a form from a model?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Form.from_model()` has four methods to select which fields are included in the final form:

1. the `include` parameter: this is a list of strings for members of the model to use to generate the form.
2. the `exclude` parameter: the inverse of `include`. If you use this the form gets all the fields from the model excluding the ones with names you supply in `exclude`.
3. for more advanced usages you can also pass the `include` parameter to a specific field like `fields__my_field__include=True`. Here you can supply either a `bool` or a callable like `fields__my_field__include=lambda form, field, **_: form.request().user.is_staff`.
4. you can also add fields that are not present in the model with the `extra_fields`. This is a `dict` from name to either a `Field` instance or a `dict` containing a definition of how to create a `Field`.


How do I supply a custom initial value?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a value or callable to the `initial` member:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__initial=7,
        fields__bar__initial=lambda field, form, **_: 11,
    )

If there are `GET` parameters in the request, iommi will use them to fill in the appropriate fields. This is very handy for supplying links with partially filled in forms from just a link on another part of the site.


How do I set if a field is required?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Normally this will be handled automatically by looking at the model definition, but sometimes you want a form to be more strict than the model. Pass a `bool` or a callable to the `required` member:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__initial=7,
        fields__bar__initial=lambda field, form, **_: 11,
    )



How do I change the order of the fields?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can change the order in your model definitions as this is what iommi uses. If that's not practical you can use the `after` member. It's either the name of a field or an index. There is a special value `LAST` to put a field last.

.. code:: python

    from tri_declarative import LAST

    form = Form.from_model(
        model=Foo,
        fields__foo__after=0,
        fields__bar__after='foo',
        fields__bar__after=LAST,
    )

If there are multiple fields with the same index or name the order of the fields will be used to disambiguate.


How do I insert a CSS class or HTML attribute?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `attrs` namespace on `Field`, `Form`, `Header`, `Cell` and more is used to customize HTML attributes.

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__attrs__foo='bar',
        fields__bar__after__class__bar=True,
        fields__bar__after__style__baz='qwe,
    )

or more succinctly:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__foo__attrs=dict(
            foo='bar',
            class__bar=True,
            style__baz='qwe,
        )
    )


The thing to remember is that the basic namespace is dict with key value pairs that gets projected out into the HTML, but there are two special cases for `style` and `class`. The example above will result in the following attributes on the field tag:

.. code:: html

   <div foo="bar" class="bar" style="baz: qwe">

The values in these dicts can be callables:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__bar__after__class__bar=
            lambda form, **_: form.request().user.is_staff,
    )


How do I override rendering of an entire field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a template name or a `Template` object:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__bar__template='my_template.html',
        fields__bar__template=Template('{{ field.attrs }}'),
    )


How do I override rendering of the input field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Pass a template name or a `Template` object to the `input` namespace:

.. code:: python

    form = Form.from_model(
        model=Foo,
        fields__bar__input__template='my_template.html',
        fields__bar__input__template=Template('{{ field.attrs }}'),
    )
