from __future__ import absolute_import

import pytest
from tests.models import CreateOrEditObjectTest, get_saved_something
from tri.form import INITIALS_FROM_GET
from tri.struct import Struct

from tri.form.views import create_object, edit_object


@pytest.mark.django_db
def test_create_or_edit_object():
    # 1. View create form
    request = Struct(method='GET', META={}, GET={}, user=Struct(is_authenticated=lambda: True))

    response = create_object(
        request=request,
        model=CreateOrEditObjectTest,
        form__field__f_int__initial=1,
        form__field__f_float__initial=lambda form, field: 2,
        render__context={'foo': 'FOO'},
        render=lambda **kwargs: kwargs)
    assert response['context_instance']['object_name'] == 'create or edit object test'
    assert response['context_instance']['is_create'] is True
    form = response['context_instance']['form']
    assert response['context_instance']['foo'] == 'FOO'
    assert form.mode is INITIALS_FROM_GET
    assert form.fields_by_name['f_int'].initial == 1
    assert form.fields_by_name['f_int'].errors == set()
    assert form.fields_by_name['f_int'].value == 1
    assert form.fields_by_name['f_float'].value == 2
    assert form.fields_by_name['f_bool'].value is None
    assert set(form.fields_by_name.keys()) == {'f_int', 'f_float', 'f_bool'}

    # 2. Create
    request.method = 'POST'
    request.POST = {
        'f_int': '3',
        'f_float': '5.1',
        'f_bool': 'True',
        '-': '-',
    }
    create_object(
        request=request,
        model=CreateOrEditObjectTest,
        render=lambda **kwargs: kwargs)
    assert get_saved_something() is not None
    assert get_saved_something().f_int == 3
    assert get_saved_something().f_float == 5.1
    assert get_saved_something().f_bool is True

    # 3. View edit form
    request.method = 'GET'
    del request.POST
    response = edit_object(
        request=request,
        instance=get_saved_something(),
        render=lambda **kwargs: kwargs)
    form = response['context_instance']['form']
    assert form.get_errors() == {}
    assert form.fields_by_name['f_int'].value == 3
    assert form.fields_by_name['f_float'].value == 5.1
    assert form.fields_by_name['f_bool'].value is True

    # 4. Edit
    request.method = 'POST'
    request.POST = {
        'f_int': '7',
        'f_float': '11.2',
        '-': '-',
        # Not sending a parameter in a POST is the same thing as false
    }
    response = edit_object(
        request=request,
        instance=get_saved_something(),
        redirect=lambda form, **_: {'context_instance': {'form': form}},
        render=lambda **kwargs: kwargs)
    form = response['context_instance']['form']
    assert form.get_errors() == {}
    assert form.is_valid()
    assert get_saved_something() is not None
    assert get_saved_something().f_int == 7
    assert get_saved_something().f_float == 11.2
    assert not get_saved_something().f_bool
