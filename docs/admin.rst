.. imports
    from django.contrib.auth.models import User
    import pytest
    pytestmark = pytest.mark.django_db

Admin
=====

The powerful abstractions of iommi enable us to build an admin interface
that is automagically created based on your models, while retaining the full
feature set of iommi.

.. contents::
    :local:


Installation
~~~~~~~~~~~~

First declare a subclass of `Admin`:

.. code:: python

    from iommi.admin import Admin

    class MyAdmin(Admin):
        pass

This is the place you will put configuration. If you don't need any you
can skip this step. Next plug it into your urls:


.. code:: python

    urlpatterns = [
        # ...

        path('iommi-admin/', include(MyAdmin.urls())),
    ]

Now you have the iommi admin gui for your app!


Customization
~~~~~~~~~~~~~

Remove a model from the admin
-----------------------------

By default iommi displays all models of all apps. You can override this like:

.. code:: python

    class MyAdmin(Admin):
        class Meta:
            apps__sessions_session__include = False

This turns off the admin of the Session table in the sessions app. This is
actually the default already. But you can turn off any model you like here.


Permissions
-----------

By default staff users have access to the admin. You can change this by
overriding `has_permission`:

.. code:: python

    from iommi.admin import Admin

    class MyAdmin(Admin):
        @staticmethod
        def has_permission(request, operation, model=None, instance=None):
            # This is the default implementation
            return request.user.is_staff

.. test
    assert Admin.has_permission  # validate that we haven't changed the API of Admin too badly
    request = req('get')
    request.user = User.objects.create(username='foo', is_staff=True)
    assert MyAdmin.has_permission(request, None, None, None)

`operation` is one of `create`, `edit`, `delete`, `list` and `all_models`. The
`model` parameter will be given for create/edit/delete/list, and instance will
be supplied in edit/delete.

HTML attributes
---------------

You can configure attributes in the admin similarly to the rest of iommi, on
the `Meta` class:

.. code:: python

    class MyAdmin(Admin):
        class Meta:
            parts__all_models__columns__model_name__cell__attrs__style__background = 'black'


The easiest way to find the path for configuration is to have
`settings.IOMMI_DEBUG` turned on (by default on if `DEBUG` is on), and use
the pick feature and click on the element. You'll get the path and also
the type so you can click your way to the documentation for that class.

In the example above the `data-iommi-path` would be
`parts__all_models__columns__model_name__cell` and `data-iommi-type` is
:doc:`Cell`. In the docs for `Cell` you can find that cells have `attrs`.
