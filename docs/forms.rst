Forms
=====

iommi forms is alternative forms system for Django. It is inspired by, and comes from a frustration with, the standard Django forms.

Major features compared to Django forms:

- Supports :code:`__` syntax for going across table/object boundaries, similar to how Django does with QuerySets.
- Send in a callable that is late evaluated to determine if a field should be displayed (:code:`show`). This is very handy for showing a slightly different form to administrators for example.
- Easy configuration without writing entire classes that are only used in one place anyway.


Example
-------

You can either create a subclass of :code:`Form`...

.. code:: python

    class UserForm(Form):
        name = Field.text()
        username = Field.text(
            is_valid=lambda parsed_data, **_: parsed_data.startswith('demo_'))
        is_admin = Field.boolean(
            # show only for staff
            show=lambda form, **_: form.request.user.is_staff,
            label_template='tweak_label_tag.html')

    def edit_user_view(request, username):
        form = UserForm(request=request)

        user = User.objects.get(username=username)
        if form.is_valid() and request.method == 'POST':
            form.apply(user)
            user.save()
            return HttpRedirect('..')

        return render(
            template_name='edit_user.html',
            context_instance=RequestContext(request, {'form': form}))

.. code:: html

    <!-- edit_user.html -->
    <form action="" method="post">{% csrf_token %}
      <div>
        <table>
          {{ form }}
        </table>
      </div>
      <input type="submit" value="Save" />
    </form>

or just instantiate a :code:`Form` with a :code:`Field` list and use it directly:

.. code:: python

    def edit_user_view(request, username):
        form = Form(fields=[
            Field.text(
                name='name',
                is_valid=lambda parsed_data, **_: parsed_data.startswith('demo_'),
            ),
            Field.text(name='username'),
            Field.boolean(
                name='is_admin',
                # show only for staff
                show=lambda form, **_: form.request().user.is_staff,
                label_template='tweak_label_tag.html',
            ),
        ])

        # rest of view function...


You can also generate forms from Django models automatically (but still change the behavior!). The above example
is equivalent to:

.. code:: python

    def edit_user_view(request, username):
        form = Form.from_model(
            data=request.POST,
            model=User,
            # the field 'name' is generated automatically and
            # we are fine with the defaults
            username__is_valid=
                lambda parsed_data, **_: parsed_data.startswith('demo_'),
            is_admin__label_template='tweak_label_tag.html',
            # show only for staff
            is_admin__show=lambda form, **_: form.request().user.is_staff,
        )

        # rest of view function...

or even better: use :code:`Form.as_edit_page`:

.. code:: python

    def edit_user_view(request, username):
        return Form.as_edit_page(
            model=User,
            instance=User.objects.get(username=username),
            username__is_valid=
                lambda parsed_data, **_: parsed_data.startswith('demo_'),
            is_admin__label_template='tweak_label_tag.html',
            # show only for staff
            is_admin__show=lambda form, **_: form.request().user.is_staff,
        )
        # no html template! iommi has a nice default for you :P

iommi pre-packages sets of defaults for common field types as 'shortcuts'. Some examples include :code:`Field.boolean`,
:code:`Field.integer` and :code:`Field.choice`. The full list of shortcuts can be found in the `API documentation for Field <api.html#iommi.Field>`_.

