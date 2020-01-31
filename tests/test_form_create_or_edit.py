import json

import pytest
from bs4 import BeautifulSoup
from iommi.base import DISPATCH_PATH_SEPARATOR
from iommi.form import (
    Form,
    INITIALS_FROM_GET,
    create_or_edit_object_redirect,
)
from tri_struct import merged

from tests.helpers import req
from tests.test_forms import remove_csrf


@pytest.mark.django_db
def test_create_and_edit_object():
    from tests.models import CreateOrEditObjectTest, Foo

    assert CreateOrEditObjectTest.objects.all().count() == 0

    # 1. View create form
    request = req('get')

    p = Form.as_create_page(
        model=CreateOrEditObjectTest,
    )
    p.bind(request=request)
    assert p.parts.create.default_child
    response = p.parts.create.__html__(render__call_target=lambda **kwargs: kwargs)
    form = p.parts.create
    assert response['context']['csrf_token']

    p = Form.as_create_page(
        model=CreateOrEditObjectTest,
        fields__f_int__initial=1,
        fields__f_float__initial=lambda form, field, **_: 2,
        template='<template name>',
    )
    p.bind(request=request)
    response = p.parts.create.__html__(
        render__context={'foo': 'FOO'},
        render__foobarbaz='render__foobarbaz',
        render__call_target=lambda **kwargs: kwargs,
    )

    form = p.parts.create
    assert form.extra.is_create is True
    assert response['context']['foo'] == 'FOO'
    assert response['context']['csrf_token']
    assert response['foobarbaz'] == 'render__foobarbaz'
    assert response['template_name'] == '<template name>'
    assert form.mode is INITIALS_FROM_GET
    assert form.fields['f_int'].initial == 1
    assert form.fields['f_int'].errors == set()
    assert form.fields['f_int'].value == 1
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
        form.own_target_marker(): '',
    })

    def on_save(form, instance, **_):
        # validate  that the arguments are what we expect
        assert form.instance is instance
        assert isinstance(instance, CreateOrEditObjectTest)
        assert instance.pk is not None

    p = Form.as_create_page(
        model=CreateOrEditObjectTest,
        on_save=on_save,  # just to check that we get called with the instance as argument
    )
    p.bind(request=request)
    response = p.render_to_response()
    assert p.parts.create._request_data
    instance = CreateOrEditObjectTest.objects.get()
    assert instance is not None
    assert instance.f_int == 3
    assert instance.f_float == 5.1
    assert instance.f_bool is True
    assert response.status_code == 302
    assert response['Location'] == '../'

    # 3. View edit form
    request = req('get')
    p = Form.as_edit_page(
        instance=instance,
    )
    p.bind(request=request)
    response = p.parts.edit.__html__(
        render=lambda **kwargs: kwargs,
    )
    form = p.parts.edit
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
        '-': '',
        # Not sending a parameter in a POST is the same thing as false
    })
    p = Form.as_edit_page(
        instance=instance,
    )
    p.bind(request=request)
    response = p.render_to_response()
    assert response.status_code == 302

    assert response['Location'] == '../../'

    instance.refresh_from_db()
    assert instance is not None
    assert instance.f_int == 7
    assert instance.f_float == 11.2
    assert not instance.f_bool

    # edit again, to check redirect
    p = Form.as_edit_page(
        instance=instance,
    )
    p.bind(request=request)
    response = p.render_to_response()
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
        '-': '',
    })
    Form.as_create_page(model=UniqueConstraintTest).bind(request=request).render_to_response()
    assert UniqueConstraintTest.objects.all().count() == 1

    p = Form.as_create_page(
        model=UniqueConstraintTest,
    ).bind(request=request)
    p.render_to_response()

    form = p.parts.create
    assert form.is_valid() is False
    assert form.get_errors() == {'global': {'Unique constraint test with this F int, F float and F bool already exists.'}}
    assert UniqueConstraintTest.objects.all().count() == 1


@pytest.mark.django_db
def test_namespace_forms():
    from tests.models import NamespaceFormsTest

    assert NamespaceFormsTest.objects.all().count() == 0

    # Create object
    request = req('post', **{
        'f_int': '3',
        'f_float': '5.1',
        'f_bool': 'True',
        '-': '',
    })
    response = Form.as_create_page(
        model=NamespaceFormsTest,
        on_save=lambda instance, **_: instance,  # just to check that we get called with the instance as argument
    ).bind(request=request).render_to_response()
    instance = NamespaceFormsTest.objects.get()
    assert instance is not None
    assert response.status_code == 302

    form_name = 'my_form'
    # Edit should NOT work when the form name does not match the POST
    request = req('post', **{
        f'{form_name}{DISPATCH_PATH_SEPARATOR}f_int': '7',
        f'{form_name}{DISPATCH_PATH_SEPARATOR}f_float': '11.2',
        '-some_other_form': '',
    })
    p = Form.as_edit_page(
        instance=instance,
        name=form_name,
        default_child=False,
    ).bind(request=request)
    p.render_to_response()
    form = p.parts[form_name]
    assert form.get_errors() == {}
    assert form.is_valid() is True
    assert not form.is_target()
    instance.refresh_from_db()
    assert instance is not None
    assert instance.f_int == 3
    assert instance.f_float == 5.1
    assert instance.f_bool

    # Edit should work when the form name is in the POST
    request = req('post', **{
        f'{form_name}{DISPATCH_PATH_SEPARATOR}f_int': '7',
        f'{form_name}{DISPATCH_PATH_SEPARATOR}f_float': '11.2',
        f'-{form_name}': '',
    })
    p = Form.as_edit_page(
        instance=instance,
        redirect=lambda form, **_: {'context_instance': {'form': form}},
        name=form_name,
        default_child=False,
    ).bind(request=request)
    p.render_to_response()
    form = p.parts[form_name]
    assert form.path() == form_name
    instance.refresh_from_db()
    assert form.get_errors() == {}
    assert form.is_valid() is True
    assert form.is_target()
    assert instance is not None
    assert instance.f_int == 7
    assert instance.f_float == 11.2
    assert not instance.f_bool


@pytest.mark.django_db
@pytest.mark.filterwarnings("ignore:Pagination may yield inconsistent results with an unordered")
def test_create_or_edit_object_dispatch():
    from tests.models import Bar, Foo

    f1 = Foo.objects.create(foo=1)
    f2 = Foo.objects.create(foo=2)
    request = req('get', **{DISPATCH_PATH_SEPARATOR + 'fields' + DISPATCH_PATH_SEPARATOR + 'foo': ''})

    response = Form.as_create_page(
        model=Bar,
        fields__foo__extra__endpoint_attr='foo',
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
        '-': '',
    })

    response = Form.as_create_page(model=Baz).bind(request=request).render_to_response()
    assert response.status_code == 302
    assert Baz.objects.filter(a=1, b=1).exists()

    response = Form.as_create_page(model=Baz).bind(request=request).render_to_response()
    assert response.status_code == 200
    assert 'Baz with this A and B already exists.' in response.content.decode('utf-8')

    request = req('post', **{
        'a': '1',
        'b': '2',  # <-- changed from 1
        '-': '',
    })
    response = Form.as_create_page(model=Baz).bind(request=request).render_to_response()
    assert response.status_code == 302
    instance = Baz.objects.get(a=1, b=2)

    request = req('post', **{
        'a': '1',
        'b': '1',  # <-- 1 again
        '-': '',
    })

    response = Form.as_edit_page(instance=instance).bind(request=request).render_to_response()
    assert response.status_code == 200
    assert 'Baz with this A and B already exists.' in response.content.decode('utf-8')


@pytest.mark.django_db
@pytest.mark.parametrize('name', [None, 'baz'])
def test_create_or_edit_object_full_template(name):
    from tests.models import Foo

    request = req('get')

    response = Form.as_create_page(model=Foo, name=name).bind(request=request).render_to_response()
    assert response.status_code == 200

    name = name or 'create'

    expected_html = f"""
<html>
    <head>
    </head>
    <body>
        <h1>
            Create foo
        </h1>
        <form action="" method="post">
            <div>
                <label for="id_foo">
                    Foo
                </label>
                <input id="id_foo" name="foo" type="text" value=""/>
                <div class="form-text text-muted">
                    foo_help_text
                </div>
            </div>
            <input name="-" type="hidden" value=""/>
            <div class="links">
                <input accesskey="s" name="{name}" type="submit" value="Create foo"/>
            </div>
        </form>
    </body>
</html>

    """
    actual = BeautifulSoup(remove_csrf(response.content.decode()), 'html.parser').prettify()
    expected = BeautifulSoup(expected_html, 'html.parser').prettify()
    assert actual == expected
