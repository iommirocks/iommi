
Forms
-----




.. _Field.parse:


How do I supply a custom parser for a field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable to the `parse` member of the field:


.. code-block:: python

    form = Form(
        auto__model=Track,
        fields__index__parse=
            lambda field, string_value, **_: int(string_value[:-3]),
    )


.. _Field.editable:

How do I make a field non-editable?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable or `bool` to the `editable` member of the field:


.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__name__editable=
            lambda request, **_: request.user.is_staff,
        fields__artist__editable=False,
    )


.. _Form.editable:

How do I make an entire form non-editable?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a very common case so there's a special syntax for this: pass a `bool` to the form:


.. code-block:: python

    form = Form.edit(
        auto__instance=album,
        editable=False,
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('20ce4ea8-dbe6-4ea0-be62-fc1c82031be0', this)">▼ Hide result</div>
        <iframe id="20ce4ea8-dbe6-4ea0-be62-fc1c82031be0" src="doc_includes/cookbook_forms/test_how_do_i_make_an_entire_form_non_editable.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. _Field.is_valid:

How do I supply a custom validator?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a callable that has the arguments `form`, `field`, and `parsed_data`. Return a tuple `(is_valid, 'error message if not valid')`.


.. code-block:: python

    form = Form.create(
        auto__model=Album,
        auto__include=['name'],
        fields__name__is_valid=
            lambda form, field, parsed_data: (False, 'invalid!'),
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('9a1a96aa-8b24-464e-aa34-8e49a47c7e5d', this)">▼ Hide result</div>
        <iframe id="9a1a96aa-8b24-464e-aa34-8e49a47c7e5d" src="doc_includes/cookbook_forms/test_how_do_i_supply_a_custom_validator.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    
How do I validate multiple fields together?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Refine the `post_validation` hook on the `form`. It is run after all the individual fields validation
has run. But note that it is run even if the individual fields validation was not successful.




How do I exclude a field?
~~~~~~~~~~~~~~~~~~~~~~~~~

See `How do I say which fields to include when creating a form from a model?`_





How do I say which fields to include when creating a form from a model?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Form()` has four methods to select which fields are included in the final form:

1. the `auto__include` parameter: this is a list of strings for members of the model to use to generate the form.
2. the `auto__exclude` parameter: the inverse of `include`. If you use this the form gets all the fields from the model excluding the ones with names you supply in `exclude`.
3. for more advanced usages you can also pass the `include` parameter to a specific field like `fields__my_field__include=True`. Here you can supply either a `bool` or a callable like `fields__my_field__include=lambda request, **_: request.user.is_staff`.
4. you can also add fields that are not present in the model by passing configuration like `fields__foo__attr='bar__baz'` (this means create a `Field` called `foo` that reads its data from `bar.baz`). You can either pass configuration data like that, or pass an entire `Field` instance.




.. _Field.initial:

How do I supply a custom initial value?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a value or callable to the `initial` member:


.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__name__initial='Paranoid',
        fields__year__initial=lambda field, form, **_: 1970,
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('8b263338-5e2e-47ab-b7dc-fb3a336494d7', this)">▼ Hide result</div>
        <iframe id="8b263338-5e2e-47ab-b7dc-fb3a336494d7" src="doc_includes/cookbook_forms/test_how_do_i_supply_a_custom_initial_value.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    
If there are `GET` parameters in the request, iommi will use them to fill in the appropriate fields. This is very handy for supplying links with partially filled in forms from just a link on another part of the site.




.. _Field.required:

How do I set if a field is required?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Normally this will be handled automatically by looking at the model definition, but sometimes you want a form to be more strict than the model. Pass a `bool` or a callable to the `required` member:


.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__name__required=True,
        fields__year__required=lambda field, form, **_: True,
    )


.. _Field.after:

How do I change the order of the fields?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can change the order in your model definitions as this is what iommi uses. If that's not practical you can use the `after` member. It's either the name of a field or an index. There is a special value `LAST` to put a field last.


.. code-block:: python

    from tri_declarative import LAST

    form = Form(
        auto__model=Album,
        fields__name__after=LAST,
        fields__year__after='artist',
        fields__artist__after=0,
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('13392965-2636-43e9-81c0-f27b33875d95', this)">▼ Hide result</div>
        <iframe id="13392965-2636-43e9-81c0-f27b33875d95" src="doc_includes/cookbook_forms/test_how_do_i_change_the_order_of_the_fields.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    
This will make the field order `artist`, `year`, `name`.

If there are multiple fields with the same index or name the order of the fields will be used to disambiguate.




.. _Field.search_fields:

How do I specify which model fields the search of a choice_queryset use?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Form.choice_queryset` uses the registered search fields for filtering and ordering.
See :doc:`registrations` for how to register one. If present it will default
to a model field `name`.


In special cases you can override which attributes it uses for
searching by specifying `search_fields`:


.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__name__search_fields=('name', 'year'),
    )


This last method is discouraged though, because it will mean searching behaves
differently in different parts of your application for the same data.





How do I insert a CSS class or HTML attribute?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See :doc:`Attrs`.




.. _Field.template:

How do I override rendering of an entire field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass a template name:


.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__year__template='my_template.html',
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('b0d25cb4-bf44-494c-bdf6-9387a4eb7deb', this)">▼ Hide result</div>
        <iframe id="b0d25cb4-bf44-494c-bdf6-9387a4eb7deb" src="doc_includes/cookbook_forms/test_how_do_i_override_rendering_of_an_entire_field.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
        

or a `Template` object:

.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__year__template=Template('This is from the inline template'),
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('cd5f9ba5-4b8b-47b2-b4d5-d938688156c5', this)">▼ Hide result</div>
        <iframe id="cd5f9ba5-4b8b-47b2-b4d5-d938688156c5" src="doc_includes/cookbook_forms/test_how_do_i_override_rendering_of_an_entire_field1.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


.. _Field.input:

How do I override rendering of the input field?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Pass a template name or a `Template` object to the `input` namespace:


.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__year__input__template='my_template.html',
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('17b3e892-80c7-40fe-b31c-316c3b874936', this)">▼ Hide result</div>
        <iframe id="17b3e892-80c7-40fe-b31c-316c3b874936" src="doc_includes/cookbook_forms/test_how_do_i_override_rendering_of_the_input_field.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
        



.. code-block:: python

    form = Form(
        auto__model=Album,
        fields__year__input__template=Template('This is from the inline template'),
    )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('f70bcb43-379f-44fe-9d14-fdf7c3f3607c', this)">▼ Hide result</div>
        <iframe id="f70bcb43-379f-44fe-9d14-fdf7c3f3607c" src="doc_includes/cookbook_forms/test_how_do_i_override_rendering_of_the_input_field1.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


How do I change how fields are rendered everywhere in my project?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Define a custom style and override the appropriate fields. For
example here is how you could change `Field.date` to use a text
based input control (as opposed to the date picker that `input type='date'`
uses).


.. code-block:: python

    my_style = Style(bootstrap, Field__shortcuts__date__input__attrs__type='text')


When you do that you will get English language relative date parsing
(e.g. "yesterday", "3 days ago") for free, because iommi used to use a
text based input control and the parser is applied no matter what
(its just that when using the default date picker control it will
always only see ISO-8601 dates).

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('c4f68613-f0ed-46d8-a45a-ba854c91fd29', this)">▼ Hide result</div>
        <iframe id="c4f68613-f0ed-46d8-a45a-ba854c91fd29" src="doc_includes/cookbook_forms/test_how_do_i_change_how_fields_are_rendered_everywhere_in_my_project.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    