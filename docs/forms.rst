.. imports
    from django.contrib.auth.models import User
    from iommi._web_compat import HttpResponseRedirect, RequestContext, render
    import pytest
    pytestmark = pytest.mark.django_db

Forms
=====

iommi forms is an alternative forms system for Django. It is inspired by, and
comes from a frustration with, the standard Django forms.

Major features compared to Django forms:

- Supports `__` syntax for going across table/object boundaries, similar to how Django does with QuerySets.
- Send in a callable that is late evaluated to determine if a field should be displayed (`include`). This is very handy for showing a slightly different form to administrators for example.
- Easy configuration without writing entire classes that are only used in one place anyway.

Read the full documentation and the :doc:`howto` for more.

.. contents::
    :local:

Examples
--------

.. test
    user = User.objects.create(username='foo')
    request = req('get')
    request.user = user


You can either create a subclass of `Form`...

.. todo
    Would be good if these things were tested...
    These examples are a bit of a mess... the good examples at the bottom and the manual stuff at the top

.. code:: python

    class UserForm(Form):
        name = Field.text()
        username = Field.text(
            is_valid=lambda parsed_data, **_: (parsed_data.startswith('demo_'), 'neeeds to start with demo_'))
        is_staff = Field.boolean(
            # show only for staff
            include=lambda request, **_: request.user.is_staff,
            label__template='tweak_label_tag.html')

    def edit_user_view(request, username):
        form = UserForm().bind(request=request)

        user = User.objects.get(username=username)
        if form.is_valid() and request.method == 'POST':
            form.apply(user)
            user.save()
            return HttpResponseRedirect('..')

        return render(
            request=request,
            template_name='edit_user.html',
            context={'form': form})

.. test

    edit_user_view(request, user.username)
    post_request = req('post', name='foo', username='demo_', is_staff='1')
    post_request.user = user
    edit_user_view(post_request, user.username)
    # restore the username
    user.username = 'foo'
    user.save()

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

or just instantiate a `Form` with a `Field` dict and use it directly:

.. code:: python

    def edit_user_view(request, username):
        form = Form(fields=dict(
            name=Field.text(
                is_valid=lambda parsed_data, **_: parsed_data.startswith('demo_'),
            ),
            username=Field.text(),
            is_staff=Field.boolean(
                # show only for staff
                include=lambda request, **_: request.user.is_staff,
                label__template='tweak_label_tag.html',
            ),
        ))

        # rest of view function...

.. test
        return form
    edit_user_view(request, user.username)


You can also generate forms from Django models automatically (but still
change the behavior!). The above example is equivalent to:

.. code:: python

    def edit_user_view(request, username):
        form = Form(
            auto__model=User,
            # the field 'name' is generated automatically and
            # we are fine with the defaults
            fields__username__is_valid=
                lambda parsed_data, **_: parsed_data.startswith('demo_'),
            fields__is_staff__label__template='tweak_label_tag.html',
            # show only for staff
            fields__is_staff__include=lambda request, **_: request.user.is_staff,
        )
        form = form.bind(request=request)

        # rest of view function...

.. test
        return form
    edit_user_view(request, user.username)


or even better: use `Form.edit`:

.. code:: python

    def edit_user_view(request, username):
        return Form.edit(
            auto__instance=User.objects.get(username=username),
            fields__username__is_valid=
                lambda parsed_data, **_: parsed_data.startswith('demo_'),
            fields__is_staff__label__template='tweak_label_tag.html',
            # show only for staff
            fields__is_staff__include=lambda request, **_: request.user.is_staff,
        )
        # no html template! iommi has a nice default for you :P

.. test
    edit_user_view(request, user.username)

iommi pre-packages sets of defaults for common field types as 'shortcuts'.
Some examples include `Field.boolean`, `Field.integer` and `Field.choice`.
The full list of shortcuts can be found in the
`API documentation for Field <api.html#iommi.Field>`_.

