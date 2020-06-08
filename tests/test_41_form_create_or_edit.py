import json

import pytest
from django.test import override_settings
from tri_struct import merged

from iommi.endpoint import DISPATCH_PATH_SEPARATOR
from iommi.form import (
    create_or_edit_object_redirect,
    Form,
    FULL_FORM_FROM_REQUEST,
    INITIALS_FROM_GET,
)
from tests.helpers import (
    prettify,
    remove_csrf,
    req,
)


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_create_and_edit_object():
    from tests.models import CreateOrEditObjectTest, Foo

    assert CreateOrEditObjectTest.objects.all().count() == 0

    # 1. View create form
    request = req('get')

    form = Form.create(
        auto__model=CreateOrEditObjectTest,
    )
    form = form.bind(request=request)
    response = form.__html__(render__call_target=lambda **kwargs: kwargs)
    assert response['context']['csrf_token']

    form = Form.create(
        auto__model=CreateOrEditObjectTest,
        fields__f_int__initial=1,
        fields__f_float__initial=lambda form, field, **_: 2,
        template='<template name>',
    )
    form = form.bind(request=request)
    response = form.__html__(
        render__context={'foo': 'FOO'},
        render__foobarbaz='render__foobarbaz',
        render__call_target=lambda **kwargs: kwargs,
    )

    assert form.extra.is_create is True
    assert response['context']['foo'] == 'FOO'
    assert response['context']['csrf_token']
    assert response['foobarbaz'] == 'render__foobarbaz'
    assert response['template'] == '<template name>'
    assert form.mode is INITIALS_FROM_GET
    assert form.fields['f_int'].initial == 1
    assert form.fields['f_int'].errors == set()
    assert form.fields['f_int'].value == 1
    assert form.fields['f_float'].initial == 2
    assert form.fields['f_float'].value == 2
    assert form.fields['f_bool'].value is None
    assert set(form.fields.keys()) == {'f_int', 'f_float', 'f_bool', 'f_foreign_key', 'f_many_to_many'}

    # 2. Create
    foo = Foo.objects.create(foo=7)

    request = req('post', **{
        'f_int': '3',
        'f_float': '5.1',
        'f_bool': 'True',
        'f_foreign_key': str(foo.pk),
        'f_many_to_many': [str(foo.pk)],
        form.actions.submit.own_target_marker(): '',
    })

    def on_save(form, instance, **_):
        # validate  that the arguments are what we expect
        assert form.instance is instance
        assert isinstance(instance, CreateOrEditObjectTest)
        assert instance.pk is not None

    form = Form.create(
        auto__model=CreateOrEditObjectTest,
        extra__on_save=on_save,  # just to check that we get called with the instance as argument
    )
    form = form.bind(request=request)
    response = form.render_to_response()
    assert form._request_data
    instance = CreateOrEditObjectTest.objects.get()
    assert instance is not None
    assert instance.f_int == 3
    assert instance.f_float == 5.1
    assert instance.f_bool is True
    assert response.status_code == 302
    assert response['Location'] == '../'

    # 3. View edit form
    request = req('get')
    form = Form.edit(
        auto__instance=instance,
    )
    form = form.bind(request=request)
    response = form.__html__(
        render=lambda **kwargs: kwargs,
    )
    assert form.get_errors() == {}
    assert form.fields['f_int'].value == 3
    assert form.fields['f_float'].value == 5.1
    assert form.fields['f_bool'].value is True
    assert response['context']['csrf_token']

    # 4. Edit
    request = req('POST', **{
        'f_int': '7',
        'f_float': '11.2',
        'f_foreign_key': str(foo.pk),
        'f_many_to_many': [str(foo.pk)],
        '-submit': '',
        # Not sending a parameter in a POST is the same thing as false
    })
    form = Form.edit(
        auto__instance=instance,
    )
    form = form.bind(request=request)
    assert form.mode == FULL_FORM_FROM_REQUEST
    response = form.render_to_response()
    assert response.status_code == 302

    assert response['Location'] == '../../'

    instance.refresh_from_db()
    assert instance is not None
    assert instance.f_int == 7
    assert instance.f_float == 11.2
    assert not instance.f_bool

    # edit again, to check redirect
    form = Form.edit(
        auto__instance=instance,
    )
    form = form.bind(request=request)
    response = form.render_to_response()
    assert response.status_code == 302
    assert response['Location'] == '../../'


def test_redirect_default_case():
    sentinel1, sentinel2, sentinel3, sentinel4 = object(), object(), object(), object()
    expected = dict(redirect_to=sentinel2, request=sentinel3, form=sentinel4)
    assert create_or_edit_object_redirect(**merged(expected, is_create=sentinel1, redirect=lambda **kwargs: kwargs)) == expected


@pytest.mark.django_db
def test_unique_constraint_violation():
    from tests.models import UniqueConstraintTest

    request = req('post', **{
        'f_int': '3',
        'f_float': '5.1',
        'f_bool': 'True',
        '-submit': '',
    })
    Form.create(auto__model=UniqueConstraintTest).bind(request=request).render_to_response()
    assert UniqueConstraintTest.objects.all().count() == 1

    form = Form.create(
        auto__model=UniqueConstraintTest,
    ).bind(request=request)
    form.render_to_response()

    assert form.is_valid() is False, form.get_errors()
    assert form.get_errors() == {'global': {'Unique constraint test with this F int, F float and F bool already exists.'}}
    assert UniqueConstraintTest.objects.all().count() == 1


@pytest.mark.django_db
@pytest.mark.filterwarnings("ignore:Pagination may yield inconsistent results with an unordered")
@override_settings(DEBUG=True)
def test_create_or_edit_object_dispatch():
    from tests.models import Bar, Foo

    f1 = Foo.objects.create(foo=1)
    f2 = Foo.objects.create(foo=2)
    request = req('get', **{DISPATCH_PATH_SEPARATOR + 'choices': ''})

    response = Form.create(
        auto__model=Bar,
        template='<template name>',
    ).bind(request=request).render_to_response()
    assert json.loads(response.content) == {
        'results': [
            {"text": str(f1), "id": f1.pk},
            {"text": str(f2), "id": f2.pk},
        ],
        'pagination': {'more': False},
        'page': 1,
    }


@pytest.mark.django_db
def test_create_or_edit_object_validate_unique():
    from tests.models import Baz

    request = req('post', **{
        'a': '1',
        'b': '1',
        '-submit': '',
    })

    response = Form.create(auto__model=Baz).bind(request=request).render_to_response()
    assert response.status_code == 302
    assert Baz.objects.filter(a=1, b=1).exists()

    response = Form.create(auto__model=Baz).bind(request=request).render_to_response()
    assert response.status_code == 200
    assert 'Baz with this A and B already exists.' in response.content.decode('utf-8')

    request = req('post', **{
        'a': '1',
        'b': '2',  # <-- changed from 1
        '-submit': '',
    })
    response = Form.create(auto__model=Baz).bind(request=request).render_to_response()
    assert response.status_code == 302
    instance = Baz.objects.get(a=1, b=2)

    request = req('post', **{
        'a': '1',
        'b': '1',  # <-- 1 again
        '-submit': '',
    })

    response = Form.edit(auto__instance=instance).bind(request=request).render_to_response()
    assert response.status_code == 200
    assert 'Baz with this A and B already exists.' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_create_or_edit_object_full_template():
    from tests.models import Foo

    request = req('get')

    response = Form.create(auto__model=Foo).bind(request=request).render_to_response()
    assert response.status_code == 200

    expected_html = f"""
<html>
    <head>
    </head>
    <body>
        <h1>
            Create foo
        </h1>
        <form action="" enctype="multipart/form-data" method="post">
            <div>
                <label for="id_foo">
                    Foo
                </label>
                <input id="id_foo" name="foo" type="text" value=""/>
                <div class="helptext">
                    foo_help_text
                </div>
            </div>
            <div class="links">
                <input accesskey="s" name="create" type="submit" value="Create foo" name="-submit">
            </div>
        </form>
    </body>
</html>

    """
    actual = prettify(remove_csrf(response.content.decode()))
    expected = prettify(expected_html)
    assert actual == expected


def test_create_or_edit_view_name():
    from tests.models import Foo

    class MyForm(Form):
        pass

    assert MyForm(auto__model=Foo).as_view().__name__ == "MyForm.as_view"


@pytest.mark.django_db
def test_create_or_edit_object_full_template():
    from tests.models import Foo

    foo = Foo.objects.create(foo=7)
    Form.delete(auto__instance=foo).bind(request=req('post', **{'-submit': ''})).render_to_response()
    with pytest.raises(Foo.DoesNotExist):
        foo.refresh_from_db()


@pytest.mark.django_db
def test_evil_names():
    from tests.models import EvilNames
    Form.create(auto__model=EvilNames).bind(request=req('post'))
