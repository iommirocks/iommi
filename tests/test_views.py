from __future__ import absolute_import

import json

import pytest
from bs4 import BeautifulSoup

from tests.models import CreateOrEditObjectTest, get_saved_something, Bar, Foo, UniqueConstraintTest, reset_saved_something, NamespaceFormsTest
from tri.form import INITIALS_FROM_GET, DISPATCH_PATH_SEPARATOR
from tri.struct import Struct, merged

from tri.form.views import create_object, edit_object, create_or_edit_object_redirect


def get_request_context(response):
    if 'context_instance' in response:
        return response['context_instance']
    return response['context']


@pytest.mark.django_db
def test_create_or_edit_object():
    reset_saved_something()

    # 1. View create form
    request = Struct(method='GET', META={}, GET={}, user=Struct(is_authenticated=lambda: True))

    response = create_object(
        request=request,
        model=CreateOrEditObjectTest,
        render__call_target=lambda **kwargs: kwargs,
        model_verbose_name='baz',
    )
    assert get_request_context(response)['object_name'] == 'baz'  # check explicit model_verbose_name parameter to create_object

    response = create_object(
        request=request,
        model=CreateOrEditObjectTest,
        form__field__f_int__initial=1,
        form__field__f_float__initial=lambda form, field: 2,
        template_name='<template name>',
        render=lambda **kwargs: kwargs,  # this is the same as render__call_target=...
        render__context={'foo': 'FOO'},
        render__foobarbaz='render__foobarbaz',
    )
    assert get_request_context(response)['object_name'] == 'foo bar'  # Meta verbose_name
    assert get_request_context(response)['is_create'] is True
    form = get_request_context(response)['form']
    assert get_request_context(response)['foo'] == 'FOO'
    assert response['foobarbaz'] == 'render__foobarbaz'
    assert response['template_name'] == '<template name>'
    assert form.mode is INITIALS_FROM_GET
    assert form.fields_by_name['f_int'].initial == 1
    assert form.fields_by_name['f_int'].errors == set()
    assert form.fields_by_name['f_int'].value == 1
    assert form.fields_by_name['f_float'].value == 2
    assert form.fields_by_name['f_bool'].value is None
    assert set(form.fields_by_name.keys()) == {'f_int', 'f_float', 'f_bool', 'f_foreign_key', 'f_many_to_many'}

    # 2. Create
    foo = Foo.objects.create(foo=7)

    request.method = 'POST'
    request.POST = {
        'f_int': '3',
        'f_float': '5.1',
        'f_bool': 'True',
        'f_foreign_key': str(foo.pk),
        'f_many_to_many': [str(foo.pk)],
        '-': '-',
    }
    response = create_object(
        request=request,
        model=CreateOrEditObjectTest,
        on_save=lambda instance, **_: instance,  # just to check that we get called with the instance as argument
        render__call_target=lambda **kwargs: kwargs,
    )
    instance = get_saved_something()
    reset_saved_something()
    assert instance is not None
    assert instance.f_int == 3
    assert instance.f_float == 5.1
    assert instance.f_bool is True
    assert response.status_code == 302
    assert response['Location'] == '../'

    # 3. View edit form
    request.method = 'GET'
    del request.POST
    response = edit_object(
        request=request,
        instance=instance,
        render__call_target=lambda **kwargs: kwargs)
    form = get_request_context(response)['form']
    assert form.get_errors() == {}
    assert form.fields_by_name['f_int'].value == 3
    assert form.fields_by_name['f_float'].value == 5.1
    assert form.fields_by_name['f_bool'].value is True

    # 4. Edit
    request.method = 'POST'
    request.POST = {
        'f_int': '7',
        'f_float': '11.2',
        'f_foreign_key': str(foo.pk),
        'f_many_to_many': [str(foo.pk)],
        '-': '-',
        # Not sending a parameter in a POST is the same thing as false
    }
    response = edit_object(
        request=request,
        instance=instance,
        redirect=lambda form, **_: {'context_instance': {'form': form}},
        render__call_target=lambda **kwargs: kwargs,
    )
    instance = get_saved_something()
    reset_saved_something()
    form = get_request_context(response)['form']
    assert form.get_errors() == {}
    assert form.is_valid()
    assert instance is not None
    assert instance.f_int == 7
    assert instance.f_float == 11.2
    assert not instance.f_bool

    # edit again, to check redirect
    response = edit_object(
        request=request,
        instance=instance,
    )
    assert response.status_code == 302
    assert response['Location'] == '../../'


def test_redirect_default_case():
    sentinel1, sentinel2, sentinel3, sentinel4 = object(), object(), object(), object()
    expected = dict(redirect_to=sentinel2, request=sentinel3, form=sentinel4)
    assert create_or_edit_object_redirect(**merged(expected, is_create=sentinel1, redirect=lambda **kwargs: kwargs)) == expected


@pytest.mark.django_db
def test_unique_constraint_violation():
    request = Struct(method='POST', META={}, GET={}, user=Struct(is_authenticated=lambda: True))
    request.POST = {
        'f_int': '3',
        'f_float': '5.1',
        'f_bool': 'True',
        '-': '-',
    }
    create_object(
        request=request,
        model=UniqueConstraintTest)
    assert UniqueConstraintTest.objects.all().count() == 1

    response = create_object(
        request=request,
        model=UniqueConstraintTest,
        render__call_target=lambda **kwargs: kwargs)

    form = get_request_context(response)['form']
    assert not form.is_valid()
    assert form.get_errors() == {'global': {'Unique constraint test with this F int, F float and F bool already exists.'}}
    assert UniqueConstraintTest.objects.all().count() == 1


@pytest.mark.django_db
def test_namespace_forms():
    reset_saved_something()

    # Create object
    request = Struct(method='POST', META={}, GET={}, user=Struct(is_authenticated=lambda: True))
    request.POST = {
        'f_int': '3',
        'f_float': '5.1',
        'f_bool': 'True',
        '-': '-',
    }
    response = create_object(
        request=request,
        model=NamespaceFormsTest,
        on_save=lambda instance, **_: instance,  # just to check that we get called with the instance as argument
        render__call_target=lambda **kwargs: kwargs)
    instance = get_saved_something()
    reset_saved_something()
    assert instance is not None
    assert response.status_code == 302

    # Edit should NOT work when the form name does not match the POST
    request.POST = {
        'f_int': '7',
        'f_float': '11.2',
        'some_other_form': '',
        '-': '-',
    }
    response = edit_object(
        request=request,
        instance=instance,
        form__name='create_or_edit_object_form',
        render__call_target=lambda **kwargs: kwargs)
    form = get_request_context(response)['form']
    assert form.get_errors() == {}
    assert form.is_valid()
    assert not form.is_target()
    assert instance is not None
    assert instance.f_int == 3
    assert instance.f_float == 5.1
    assert instance.f_bool

    # Edit should work when the form name is in the POST
    del request.POST['some_other_form']
    request.POST['create_or_edit_object_form'] = ''
    response = edit_object(
        request=request,
        instance=instance,
        redirect=lambda form, **_: {'context_instance': {'form': form}},
        form__name='create_or_edit_object_form',
        render__call_target=lambda **kwargs: kwargs)
    form = get_request_context(response)['form']
    instance = get_saved_something()
    reset_saved_something()
    assert form.get_errors() == {}
    assert form.is_valid()
    assert form.is_target()
    assert instance is not None
    assert instance.f_int == 7
    assert instance.f_float == 11.2
    assert not instance.f_bool


@pytest.mark.django_db
def test_create_or_edit_object_dispatch():
    Foo.objects.create(foo=1)
    Foo.objects.create(foo=2)
    request = Struct(method='GET', META={}, GET={DISPATCH_PATH_SEPARATOR + 'field' + DISPATCH_PATH_SEPARATOR + 'foo': ''}, user=Struct(is_authenticated=lambda: True))

    response = create_object(
        request=request,
        model=Bar,
        form__field__foo__extra__endpoint_attr='foo',
        template_name='<template name>',
        render=lambda **kwargs: kwargs,
        render__context={'foo': 'FOO'},
    )
    assert json.loads(response.content) == [{"text": 1, "id": 1}, {"text": 2, "id": 2}]


@pytest.mark.django_db
def test_create_or_edit_object_default_template():
    request = Struct(method='GET', META={}, GET={}, user=Struct(is_authenticated=lambda: True))

    response = create_object(request=request, model=Foo)
    assert response.status_code == 200

    expected = """
        <div class="form_buttons clear">
            <input accesskey="s" class="button" type="submit" value="Create foo"/>
        </div>
    """
    assert BeautifulSoup(response.content, 'html.parser').select('.form_buttons')[0].prettify() == BeautifulSoup(expected, 'html.parser').prettify()
