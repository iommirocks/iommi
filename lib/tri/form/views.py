from __future__ import unicode_literals, absolute_import

from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from tri.form import Form, handle_dispatch
from tri.declarative import setdefaults_path, dispatch, EMPTY
from django import __version__ as django_version
django_version = tuple([int(x) for x in django_version.split('.')])


def edit_object(
        request,
        instance,
        **kwargs):
    assert 'is_create' not in kwargs  # pragma: no mutate
    assert 'model' not in kwargs  # pragma: no mutate
    assert instance is not None
    model = instance.__class__
    return create_or_edit_object(
        request,
        model,
        is_create=False,  # pragma: no mutate
        instance=instance,
        **kwargs)


def create_object(
        request,
        model,
        **kwargs):
    assert 'is_create' not in kwargs  # pragma: no mutate
    return create_or_edit_object(
        request,
        model,
        is_create=True,  # pragma: no mutate
        **kwargs)


@dispatch(
    template_name='tri_form/create_or_edit_object_block.html',
    form__call_target=Form.from_model,
    form__data=None,
    render__call_target=render_to_response,
    render__context=EMPTY,
    redirect=lambda request, redirect_to, form: HttpResponseRedirect(redirect_to),
    on_save=lambda **kwargs: None,
)
def create_or_edit_object(
        request,
        model,
        is_create,
        on_save,
        render,
        redirect,
        form,
        template_name,
        instance=None,
        model_verbose_name=None,
        redirect_to=None):
    setdefaults_path(
        form,
        request=request,
        model=model,
        instance=instance,
    )
    form = form()

    should_return, dispatch_result = handle_dispatch(request=request, obj=form)
    if should_return:
        return dispatch_result

    # noinspection PyProtectedMember
    if model_verbose_name is None:
        model_verbose_name = model._meta.verbose_name.replace('_', ' ')

    if request.method == 'POST' and form.is_target() and form.is_valid():

        if is_create:
            assert instance is None
            instance = model()
            for field in form.fields:  # two phase save for creation in django, have to save main object before related stuff
                if not field.extra.get('django_related_field', False):
                    form.apply_field(field=field, instance=instance)

        try:
            instance.validate_unique()
        except ValidationError as e:
            form.errors.update(set(e.messages))
            form._valid = False

        if form.is_valid():
            if is_create:  # two phase save for creation in django...
                instance.save()

            form.apply(instance)

            if not is_create:
                try:
                    instance.validate_unique()
                except ValidationError as e:
                    form.errors.update(set(e.messages))
                    form._valid = False

            if form.is_valid():
                instance.save()
                form.instance = instance

                on_save(form=form, instance=instance)

                return create_or_edit_object_redirect(is_create, redirect_to, request, redirect, form)

    setdefaults_path(
        render,
        template_name=template_name,
        context__form=form,
        context__is_create=is_create,
        context__object_name=model_verbose_name,
    )

    if django_version < (1, 10, 0):  # pragma: no mutate
        render.context_instance = RequestContext(request, render.pop('context'))

    return render()


def create_or_edit_object_redirect(is_create, redirect_to, request, redirect, form):
    if redirect_to is None:
        if is_create:
            redirect_to = "../"
        else:
            redirect_to = "../../"  # We guess here that the path ends with '<pk>/edit/' so this should end up at a good place
    return redirect(request=request, redirect_to=redirect_to, form=form)
