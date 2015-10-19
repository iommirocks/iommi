.. image:: https://travis-ci.org/TriOptima/tri.form.svg?branch=master
    :target: https://travis-ci.org/TriOptima/tri.form

.. image:: http://codecov.io/github/TriOptima/tri.form/coverage.svg?branch=master
    :target: http://codecov.io/github/TriOptima/tri.form?branch=master


tri.form
==========

tri.form is alternative forms library for Django. It is inspired by, and comes from a frustration with, the standard Django forms.

Major features compared to Django forms:

- Supports :code:`__` syntax for going across table boundaries, similar to how Django does with QuerySets.
- Send in a callable that is late evaluated to determine if a field should be displayed (:code:`show`). This is very handy for showing a slightly different form to administrators for example.
- Easy configuration without writing entire classes that are only used in one place anyway.


Example
-------

You can either create a subclass of :code:`Form`...

.. code:: python

    class UserForm(Form):
        name = Field.text()
        username = Field.text(is_valid=lambda form, field, parsed_data: parsed_data.startswith('demo_'))
        is_admin = Field.boolean(
            show=lambda form, field: form.request.user.is_staff, # show only for staff
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
                is_valid=lambda form, field, parsed_data: parsed_data.startswith('demo_')),
            Field.text(name='username'),
            Field.boolean(
                name='is_admin',
                show=lambda form, field: form.request.user.is_staff, # show only for staff
                label_template='tweak_label_tag.html',)])

        # rest of view function...


You can also generate forms from Django models automatically (but still change the behavior!). The above example
is equivalent to:

.. code:: python

    def edit_user_view(request, username):
        form = Form.from_model(
            request.POST,
            User,
            # the field 'name' is generated automatically and we are fine with the defaults
            username__is_valid=lambda form, field, parsed_data: parsed_data.startswith('demo_'),
            is_admin__label_template='tweak_label_tag.html',
            is_admin__show=lambda form, field: form.request.user.is_staff) # show only for staff

        # rest of view function...

or even better: use :code:`tri.form.views.create_or_edit_object`:

.. code:: python

    def edit_user_view(request, username):
        return create_or_edit_object(
            request,
            model=User,
            is_create=False,
            instance=User.objects.get(username=username),

            form__username__is_valid=lambda form, field, parsed_data: parsed_data.startswith('demo_'),
            form__is_admin__label_template='tweak_label_tag.html',
            form__is_admin__show=lambda form, field: form.request.user.is_staff) # show only for staff
        # no html template! tri.form has a nice default for you :P

tri.form pre-packages sets of defaults for common field types as 'shortcuts'. Some examples include :code:`Field.boolean`,
:code:`Field.integer` and :code:`Field.choice`. The full list of shortcuts can be found in the `API documentation for Field <api.html#tri.form.Field>`_.


Running tests
-------------

You need tox installed then just `make test`.


License
-------

BSD


Documentation
-------------

http://triform.readthedocs.org.
