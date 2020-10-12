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


iommi pre-packages sets of defaults for common field types as 'shortcuts'.
Some examples include `Field.boolean`, `Field.integer` and `Field.choice`.
The full list of shortcuts can be found in the
`API documentation for Field <api.html#iommi.Field>`_.

iommi also comes with full edit, create and delete views. See below for an example of `Form.edit`.


Declarative forms
-----------------

You can create forms declaratively, similar to Django forms. There are some important differences between iommi forms and Django forms in this mode, maybe the most important being that in iommi you can pass a callable as a parameter to late evaluate what the value of something is. This coupled with the `include` flag that is used to totally remove or turn on a part (most commonly an entire field), as we've done for the `is_staff` field in this example:


.. code:: python

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
                    return

                form.apply(user)
                user.save()
                return HttpResponseRedirect('..')

    def edit_user_view(request, username):
        user = User.objects.get(username=username)
        return UserForm(instance=user)

.. test

    user = User.objects.create(username='foo')

    post_request = req('post', first_name='foo', username='demo_', is_staff='1', **{'-submit': ''})
    post_request.user = user

    f = edit_user_view(post_request, user.username).bind(request=post_request)
    f.render_to_response()
    assert not f.get_errors()


Note that we don't need any template here.


Programmatic forms
------------------

The declarative style is very readable, but sometimes you don't know until runtime what the form should look like. In iommi forms creating forms programmatically is easy (and equivalent to doing it the declarative way:


.. code:: python

    def edit_user_save_post_handler(form, **_):
        if not form.is_valid():
            return

        form.apply(user)
        user.save()
        return HttpResponseRedirect('..')

    def edit_user_view(request, username):
        return Form(
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

.. test

    user = User.objects.create(username='foo')
    edit_user_view(user_req('get'), user.username).bind(request=user_req('get'))
    post_request = req('post', first_name='foo', username='demo_foo', is_staff='1', **{'-submit': ''})
    post_request.user = user
    f = edit_user_view(post_request, user.username).bind(request=post_request)
    f.render_to_response()
    assert not f.get_errors()


Fully automatic forms
---------------------

You can also generate forms from Django models automatically (but still
customize the behavior!). The above example is equivalent to:

.. test

    def edit_user_save_post_handler(form, **_):
        if not form.is_valid():
            return

        form.apply(user)
        user.save()
        return HttpResponseRedirect('..')

.. code:: python

    def edit_user_view(request, username):
        return Form(
            auto__model=User,
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

.. test

    user = User.objects.create(username='foo')
    edit_user_view(user_req('get'), user.username)
    post_request = req('post', first_name='foo', last_name='example', username='demo_foo', email='foo@example.com', is_staff='1', date_joined='2020-01-01 12:02:10', password='asd', **{'-submit': ''})
    post_request.user = user
    f = edit_user_view(post_request, user.username).bind(request=post_request)
    f.render_to_response()
    assert not f.get_errors()
    # restore the username for the next test below
    user.username = 'foo'
    user.save()


or even better: use `Form.edit`:

.. code:: python

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

.. test
    edit_user_view(user_req('get'), user.username)
    post_request = req('post', first_name='foo', last_name='example', username='demo_foo', email='foo@example.com', is_staff='1', date_joined='2020-01-01 12:02:10', password='asd', **{'-submit': ''})
    post_request.user = user
    f = edit_user_view(post_request, user.username).bind(request=post_request)
    f.render_to_response()
    assert not f.get_errors()


In this case the default behavior for the post handler for `Form.edit` is a save function like the one we had to define ourselves in the previous example.

