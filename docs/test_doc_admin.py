from django.urls import (
    include,
    path,
)

from iommi.admin import Admin as _Admin
from docs.models import Album
from tests.helpers import (
    req,
    show_output,
    staff_req,
)

request = req('get')

import pytest
pytestmark = pytest.mark.django_db


class Admin(_Admin):
    class Meta:
        iommi_style = 'bootstrap_docs'


def test_admin(settings, small_discography):
    # language=rst
    """
    Admin
    =====

    The powerful abstractions of iommi enable us to build an admin interface
    that is automagically created based on your models, while retaining the full
    feature set of iommi.

    Index page:
    """

    # @test
    assert settings.IOMMI_DEFAULT_STYLE == 'bootstrap_docs'
    show_output(Admin.all_models(), path='admin/')
    # @end

    # language=rst
    """
    Displaying albums:
    """

    # @test
    show_output(Admin.list().as_view()(staff_req('get'), app_name='docs', model_name='album', model=Album))
    # @end

    # language=rst
    """
    Editing an album:
    """

    # @test
    show_output(Admin.edit().as_view()(request=staff_req('get'), app_name='docs', model_name='album', model=Album, pk=Album.objects.first().pk))
    # @end

    # language=rst
    """
    Delete page for an album:    
    """

    # @test
    show_output(Admin.delete().as_view()(request=staff_req('get'), app_name='docs', model_name='album', model=Album, pk=Album.objects.first().pk))
    # @end


def test_installation():
    # language=rst
    """
    Installation
    ~~~~~~~~~~~~

    First declare a subclass of `Admin`:


    """
    from iommi.admin import Admin

    class MyAdmin(Admin):
        pass

    # language=rst
    """
    This is the place you will put global configuration. If you don't need any you
    can skip this step. Next plug it into your urls:
    """

    urlpatterns = [
        # ...

        path('iommi-admin/', include(MyAdmin.urls())),
    ]

    # language=rst
    """
    Now you have the iommi admin gui for your app!
    """
    

def test_customization():
    # language=rst
    """
    Customization
    ~~~~~~~~~~~~~

    """
    

def test_add_a_model_to_the_admin():
    # language=rst
    """
    Add a model to the admin
    ------------------------

    You can add an app to your admin from your global config like this:

    """

    class MyAdmin(Admin):
        class Meta:
            apps__myapp_mymodel__include = True

    # language=rst
    """
    This is especially useful for adding config to a third party app that doesn't have built in iommi admin configuration.

    You can also add the config in the app, by creating a `iommi_admin.py` file in your app, and putting the configuration there:


    """
    class Meta:
        apps__myapp_mymodel__include = True


def test_remove_a_model_from_the_admin():
    # language=rst
    """
    Remove a model from the admin
    -----------------------------

    By default iommi displays the built in Django `User` and `Group` models. You can override this like:

    """
    class MyAdmin(Admin):
        class Meta:
            apps__auth_user__include = False

    # language=rst
    """
    This turns off the admin of the `User` table in the `auth` app. Your global config always has priority.
    """
    

def test_permissions():
    # language=rst
    """
    Permissions
    -----------

    By default staff users have access to the admin. You can change this by
    overriding `has_permission`:

    """

    from iommi.admin import Admin

    class MyAdmin(Admin):
        @staticmethod
        def has_permission(request, operation, model=None, instance=None):
            # This is the default implementation
            return request.user.is_staff

    # @test
    assert Admin.has_permission  # validate that we haven't changed the API of Admin too badly
    assert MyAdmin.has_permission(staff_req('get'), None, None, None)

    # language=rst
    """
    `operation` is one of `create`, `edit`, `delete`, `list` and `all_models`. The
    `model` parameter will be given for create/edit/delete/list, and instance will
    be supplied in edit/delete.

    """
    

def test_html_attributes(small_discography):
    # language=rst
    """
    HTML attributes
    ---------------

    You can configure attributes in the admin similarly to the rest of iommi, on
    the `Meta` class:
    """

    class MyAdmin(Admin):
        class Meta:
            parts__list_docs_album__columns__name__header__attrs__style__background = 'yellow'

    # @test
    show_output(MyAdmin.list().as_view()(staff_req('get'), app_name='docs', model_name='album', model=Album))
    # @end

    # language=rst
    """
    The easiest way to find the path for configuration is to have
    `settings.IOMMI_DEBUG` turned on (by default on if `DEBUG` is on), and use
    the pick feature and click on the element. You'll get the path and also
    the type so you can click your way to the documentation for that class.

    In the example above the `data-iommi-path` would be
    `parts__all_models__columns__model_name__cell` and `data-iommi-type` is
    :doc:`Cell`. In the docs for `Cell` you can find that cells have `attrs`.
    """
