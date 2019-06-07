from __future__ import unicode_literals, absolute_import

from tri_form.compat import ValidationError, HttpResponseRedirect, render, csrf
from tri_form import Form, handle_dispatch, Link
from tri_declarative import setdefaults_path, dispatch, EMPTY


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
    render__call_target=render,
    render__context=EMPTY,
    redirect=lambda request, redirect_to, form: HttpResponseRedirect(redirect_to),
    on_save=lambda **kwargs: None,  # pragma: no mutate
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

    # noinspection PyProtectedMember
    if model_verbose_name is None:
        model_verbose_name = model._meta.verbose_name.replace('_', ' ')

    title = '%s %s' % ('Create' if is_create else 'Save', model_verbose_name)

    setdefaults_path(
        form,
        request=request,
        model=model,
        instance=instance,
        links=[
            Link.submit(
                attrs__value=title,
                attrs__name=form.get('name'),
            ),
        ],
    )
    form = form()

    should_return, dispatch_result = handle_dispatch(request=request, obj=form)
    if should_return:
        return dispatch_result

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
            form._valid = False  # pragma: no mutate. False here is faster, but setting it to None is also fine, it just means _valid will be calculated the next time form.is_valid() is called

        if form.is_valid():
            if is_create:  # two phase save for creation in django...
                instance.save()

            form.apply(instance)

            if not is_create:
                try:
                    instance.validate_unique()
                except ValidationError as e:
                    form.errors.update(set(e.messages))
                    form._valid = False  # pragma: no mutate. False here is faster, but setting it to None is also fine, it just means _valid will be calculated the next time form.is_valid() is called

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
        context__title=title,
    )

    render.context.update(csrf(request))

    return render(request=request)


def create_or_edit_object_redirect(is_create, redirect_to, request, redirect, form):
    if redirect_to is None:
        if is_create:
            redirect_to = "../"
        else:
            redirect_to = "../../"  # We guess here that the path ends with '<pk>/edit/' so this should end up at a good place
    return redirect(request=request, redirect_to=redirect_to, form=form)
