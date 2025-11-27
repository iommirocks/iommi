from django.urls import path

from docs.models import *
from iommi import *
from iommi.docs import show_output
from tests.helpers import (
    req,
    user_req,
)

request = req('get')

from django.contrib.auth.models import User
from iommi._web_compat import HttpResponseRedirect
import pytest
pytestmark = pytest.mark.django_db


def test_forms():
    # language=rst
    """
    .. _forms:

    Forms
    =====

    iommi forms is an alternative forms system for Django. It is inspired by the standard Django forms, while improving on its weaknesses.
    """

    # language=rst
    """
    Major features compared to Django forms:

    - Nice rendering to HTML out of the box. Default bootstrap but more built in and can be adapted to your design system.
    - AJAX-backed select widgets for your foreign key relationships.
    - Supports `__` syntax for going across table/object boundaries, similar to how Django does with QuerySets.
    - Send in a callable that is late evaluated to determine if a field should be displayed (`include`). This is very handy for showing a slightly different form to administrators for example.
    - Easily add a CSS class or style to just the thing you need just now.
    - Easy configuration without writing entire classes that are only used in one place anyway.

    Read the full documentation and the :doc:`cookbook` for more.

    iommi pre-packages sets of defaults for common field types as 'shortcuts'.
    Some examples include `Field.boolean`, `Field.integer` and `Field.choice`.
    The full list of shortcuts can be found in the
    `API documentation for Field <api.html#iommi.Field>`_.

    iommi also comes with full `edit`, `create` and `delete` views. See below for more.


    """


def test_fully_automatic_forms(settings):
    # @test
    settings.DEBUG = True
    user = User.objects.create(username='foo')
    # @end

    # language=rst
    """
    Fully automatic forms
    ---------------------

    Generating forms from Django models automatically is the most powerful and common use for iommi forms:
    
    """

    form = Form.create(auto__model=Album)

    # @test
    show_output(form)
    # @end

    # language=rst
    """
    Forms in iommi scale with higher complexity:
    """

    edit_user_form = Form.edit(
        auto__model=User,
        instance=lambda user_pk, **_: User.objects.get(pk=user_pk),
        fields__username__is_valid=
            lambda parsed_data, **_: (
                parsed_data.startswith('demo_'),
                'needs to start with demo_'
            ),
        fields__is_staff__label__template='tweak_label_tag.html',
        # show only for staff
        fields__is_staff__include=lambda request, **_: request.user.is_staff,
    )

    # language=rst
    """
    Install like this:
    """

    urlpatterns = [
        path('users/<user_pk>/edit/', edit_user_form.as_view()),
    ]

    # @test
    edit_user_view = urlpatterns[0].callback

    show_output(edit_user_view(user_req('get'), user_pk=user.pk))
    post_request = req('post', first_name='foo', last_name='example', username='demo_foo', email='foo@example.com', is_staff='1', date_joined='2020-01-01 12:02:10', password='asd', **{'-submit': ''})
    post_request.user = user
    f = edit_user_view(post_request, user_pk=user.pk)
    assert isinstance(f, HttpResponseRedirect)
    # @end

    # language=rst
    """
    In this case the default behavior for the post handler for `Form.edit` is a save function like the one we had to define ourselves in the previous example.

    """


def test_declarative_forms():
    # language=rst
    """
    Declarative forms
    -----------------

    You can create forms declaratively, similar to Django forms. There are some important differences between iommi forms and Django forms in this mode, maybe the most important being that in iommi you can pass a callable as a parameter to late evaluate what the value of something is. This is used to restrict a field for staff users in this example:
    """
    class UserForm(Form):
        first_name = Field.text()
        username = Field.text(
            is_valid=lambda parsed_data, **_: (
                parsed_data.startswith('demo_'),
                'needs to start with demo_'
            )
        )
        is_staff = Field.boolean(
            # show only for staff
            include=lambda request, **_: request.user.is_staff,
            label__template='tweak_label_tag.html',
        )

        class Meta:
            instance = lambda params, **_: User.objects.get(pk=params.user_pk)

            @staticmethod
            def actions__submit__post_handler(user, form, **_):
                if not form.is_valid():
                    return  # pragma: no cover

                form.apply(user)
                user.save()
                return HttpResponseRedirect('..')

    # language=rst
    """
    Install like this:
    """

    urlpatterns = [
        # Note `UserForm()`, not `UserForm`!
        path('users/<user_pk>/edit/', UserForm().as_view()),
    ]

    # @test

    user = User.objects.create(username='username here', first_name='First name here')
    view = urlpatterns[0].callback

    show_output(view(req('get'), user_pk=user.pk))

    post_request = req('post', first_name='foo', username='demo_', is_staff='1', **{'-submit': ''})
    post_request.user = user

    r = view(post_request, user_pk=user.pk)
    assert isinstance(r, HttpResponseRedirect)
    # @end

    # language=rst
    """
    Note that we don't need any template here.
    """


def test_programmatic_forms():
    # language=rst
    """
    Programmatic forms
    ------------------

    The declarative style is very readable, but sometimes you don't know until runtime what the form should look like. Creating forms programmatically in iommi is easy (and equivalent to doing it the declarative way):



    """
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

    # @test
    user = User.objects.create(username='foo')
    response = edit_user_view(user_req('get'), user.username).bind(request=user_req('get'))

    show_output(response)

    post_request = req('post', first_name='foo', username='demo_foo', is_staff='1', **{'-submit': ''})
    post_request.user = user
    f = edit_user_view(post_request, user.username).bind(request=post_request)
    f.render_to_response()
    assert not f.get_errors()
    # @end


def test_post_handlers():
    # language=rst
    """
    Post handlers
    -------------

    In the simplest cases, like in a create form, you only have one post handler.
    You can do this yourself in the classic Django way:

    """
    # @test

    request = req('post', foo='foo', **{'-submit': True})
    form = Form(fields__foo=Field()).bind(request=request)
    assert not form.get_errors()

    def do_your_thing():
        pass

    # @end

    if form.is_valid() and request.method == 'POST':
        do_your_thing()

    # language=rst
    """
    This is fine. But what if you have two buttons? What if you have two forms?
    What if there are two forms, one with two submit buttons, and a table with a
    bulk action? Suddenly writing the if statement above becomes very difficult.
    Post handlers in iommi handle this for you. iommi makes sure that the parts
    compose cleanly and the right action is called.

    By default for create/edit/delete forms you get one post handler by the name
    `submit`. Adding more is easy:

    """
    # @test

    # This test is a bit silly as User doesn't have a "disabled" property, but the docs don't say what type is actually here, so let's play along :P
    instance = User.objects.create(username='foo')

    # @end

    def disable_action(form, **_):
        form.instance.disabled = True
        form.instance.save()
        return HttpResponseRedirect('.')

    form = Form.edit(
        auto__instance=instance,
        actions__disable__post_handler=disable_action,
    )

    # @test
    request = req('post', username='foo', **{'-disable': True})
    form.bind(request=request).render_to_response()
    # @end

    # language=rst
    """
    Post handlers can return a few different things:

    - a `HttpResponse` object which will get returned all the way up the stack
    - a *bound* `Part` of some kind. This could be a `Table`, `Form`, `Page`, etc. This is rendered into a `HttpResponse`
    - `None` will result in the page being rendered like normal
    - everything else iommi will attempt to json encode and return as a json response
    """


def test_customization_of_save_behavior():
    # language=rst
    """

    .. _Field-hardcoded:

    Customization of save behavior on `Form.create`/`edit`
    ------------------------------------------------------

    There are some useful hooks for customizing the save behavior on `Form.create` and `Form.edit`. The most common use case
    is to set some hardcoded value for a field that is not in the form. This is best done by using `Field.hardcoded`, so
    that should be your first option.

    Saving a model in Django models SQL quite closely and iommi have hooks for all the steps in a multi-step commit.

    The callbacks are executed in this order:

    - `extra__new_instance`: This is called to create a new instance of the model. By default it just calls `form.model()`.
    - `extra__save`: This is called to save each model_object. By default it calls `model_object.save()`.
    - `extra__pre_save_all_but_related_fields` (only called for `Form.create`)
    - `extra__on_save_all_but_related_fields` (only called for `Form.create`)
    - `extra__pre_save` (before `instance.save()`)
    - `extra__on_save` (after `instance.save()`)

    **IMPORTANT**: Be careful when using `extra__save`!

    #. the passed kwarg for object instance, which we need to save is `model_object` *and not instance*!
    #. always test the instance of `model_object` to avoid possible bugs! Because quite often you need to edit objects from multiple models, for example:
    """

    class AlbumForm(Form):
        class Meta:
            auto__model = Album
            auto__include = ["name", "artist__name"]

            @classmethod
            def extra__save(model_object, **_):
                if isinstance(model_object, Album):
                    # IMPORTANT: always test the proper model when overriding save
                    model_object.save(foo="bar")
                else:
                    # because this gets called for saving the artist.name
                    model_object.save()

    # language=rst
    """
    After a POST is completed, the `extra__redirect` callback is executed if present, otherwise `extra__redirect_to`
    is used to determine where to redirect to.
    """
