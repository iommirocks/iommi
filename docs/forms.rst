
Forms
=====

iommi forms is an alternative forms system for Django. It is inspired by the standard Django forms, while improving on weaknesses.

.. code-block:: python

    form = Form.create(auto__model=Album)

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('98400e7e-e31e-460d-9db7-f6df607365f8', this)">▼ Hide result</div>
        <iframe id="98400e7e-e31e-460d-9db7-f6df607365f8" src="doc_includes/forms/test_forms.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

Major features compared to Django forms:

- Nice rendering to HTML out of the box. Default bootstrap but more built in and can be adapted to your design system.
- AJAX-backed select widgets for your foreign key relationships.
- Supports `__` syntax for going across table/object boundaries, similar to how Django does with QuerySets.
- Send in a callable that is late evaluated to determine if a field should be displayed (`include`). This is very handy for showing a slightly different form to administrators for example.
- Eeasily add a CSS class or style to just the thing you need just now.
- Easy configuration without writing entire classes that are only used in one place anyway.

Read the full documentation and the :doc:`cookbook` for more.

iommi pre-packages sets of defaults for common field types as 'shortcuts'.
Some examples include `Field.boolean`, `Field.integer` and `Field.choice`.
The full list of shortcuts can be found in the
`API documentation for Field <api.html#iommi.Field>`_.

iommi also comes with full `edit`, `create` and `delete` views. See below for an example of `Form.edit`.


    


Declarative forms
-----------------

You can create forms declaratively, similar to Django forms. There are some important differences between iommi forms and Django forms in this mode, maybe the most important being that in iommi you can pass a callable as a parameter to late evaluate what the value of something is. This is used to restrict a field for staff users in this example:



.. code-block:: python

    class UserForm(Form):
        first_name = Field.text()
        username = Field.text(
            is_valid=lambda parsed_data, **_: (
                parsed_data.startswith('demo_'),
                'needs to start with demo_')
           )
        is_staff = Field.boolean(
            # show only for staff
            include=lambda request, **_: request.user.is_staff,
            label__template='tweak_label_tag.html',
        )

        class Meta:
            @staticmethod
            def actions__submit__post_handler(form, **_):
                if not form.is_valid():
                    return  # pragma: no cover

                form.apply(user)
                user.save()
                return HttpResponseRedirect('..')

    def edit_user_view(request, username):
        user = User.objects.get(username=username)
        return UserForm(instance=user)

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('74f8e549-e44f-4c70-ac14-713edb968247', this)">▼ Hide result</div>
        <iframe id="74f8e549-e44f-4c70-ac14-713edb968247" src="doc_includes/forms/test_declarative_forms.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    

Note that we don't need any template here.



Programmatic forms
------------------

The declarative style is very readable, but sometimes you don't know until runtime what the form should look like. Creating forms programmatically in iommi is easy (and equivalent to doing it the declarative way):



.. code-block:: python

    def edit_user_save_post_handler(form, **_):
        if not form.is_valid():
            return  # pragma: no cover

        form.apply(form.instance)
        form.instance.save()
        return HttpResponseRedirect('..')

    def edit_user_view(request, username):
        return Form(
            instance=User.objects.get(username=username),
            fields=dict(
                first_name=Field.text(),
                username=Field.text(
                    is_valid=lambda parsed_data, **_: (
                        parsed_data.startswith('demo_'),
                        'needs to start with demo_'
                    ),
                ),
                is_staff=Field.boolean(
                    # show only for staff
                    include=lambda request, **_: request.user.is_staff,
                    label__template='tweak_label_tag.html',
                ),
            ),
            actions__submit__post_handler=edit_user_save_post_handler,
        )

.. raw:: html

    
        <div class="iframe_collapse" onclick="toggle('87abd96a-711c-4de9-a719-00c62aa2e15a', this)">▼ Hide result</div>
        <iframe id="87abd96a-711c-4de9-a719-00c62aa2e15a" src="doc_includes/forms/test_programmatic_forms.html" style="background: white; display: ; width: 100%; min-height: 100px; border: 1px solid gray;"></iframe>
    


Fully automatic forms
---------------------

You can also generate forms from Django models automatically (but still
customize the behavior!). The above example is equivalent to:


.. code-block:: python

    def edit_user_view(request, username):
        return Form(
            auto__instance=User.objects.get(username=username),
            # the field 'first_name' is generated automatically and
            # we are fine with the defaults
            fields__username__is_valid=
                lambda parsed_data, **_: (
                    parsed_data.startswith('demo_'),
                    'needs to start with demo_'
                ),
            fields__is_staff__label__template='tweak_label_tag.html',
            # show only for staff
            fields__is_staff__include=lambda request, **_: request.user.is_staff,
            actions__submit__post_handler=edit_user_save_post_handler,
        )



or even better: use `Form.edit`:


.. code-block:: python

    def edit_user_view(request, username):
        return Form.edit(
            auto__instance=User.objects.get(username=username),
            fields__username__is_valid=
                lambda parsed_data, **_: (
                    parsed_data.startswith('demo_'),
                    'needs to start with demo_'
                ),
            fields__is_staff__label__template='tweak_label_tag.html',
            # show only for staff
            fields__is_staff__include=lambda request, **_: request.user.is_staff,
        )



In this case the default behavior for the post handler for `Form.edit` is a save function like the one we had to define ourselves in the previous example.





Post handlers
-------------

In the simplest cases, like in a create form, you only have one post handler.
You can do this yourself in the classic Django way:


.. code-block:: python

    if form.is_valid() and request.method == 'POST':
        do_your_thing()


This is fine. But what if you have two buttons? What if you have two forms?
What if there are two forms, one with two submit buttons, and a table with a
bulk action? Suddenly writing the if statement above becomes very difficult.
Post handlers in iommi handle this for you. iommi makes sure that the parts
compose cleanly and the right action is called.

By default for create/edit/delete forms you get one post handler by the name
`submit`. Adding more is easy:


.. code-block:: python

    def disable_action(form, **_):
        form.instance.disabled = True
        form.instance.save()
        return HttpResponseRedirect('.')

    form = Form.edit(
        auto__instance=instance,
        actions__disable__post_handler=disable_action,
    )




Post handlers can return a few different things:

- a `HttpResponse` object which will get returned all the way up the stack
- a *bound* `Part` of some kind. This could be a `Table`, `Form`, `Page`, etc. This is rendered into a `HttpResponse`
- `None` will result in the page being rendered like normal
- everything else iommi will attempt to json encode and return as a json response
