import pytest
from django.db.models import (
    CharField,
    IntegerField,
    Model,
    ForeignKey,
    CASCADE,
)

from iommi.from_model import (
    get_name_field,
    NoRegisteredNameException,
    register_name_field,
)


def test_get_name_field_for_model_error():
    class NoRegisteredNameExceptionModel(Model):
        pass

    with pytest.raises(NoRegisteredNameException) as e:
        get_name_field(model=NoRegisteredNameExceptionModel)

    assert str(e.value) == 'NoRegisteredNameExceptionModel has no registered name field. Please register a name with register_name_field.'


def test_get_name_field_for_model_error_non_unique():
    class NoRegisteredNameException2Model(Model):
        name = IntegerField()

    with pytest.raises(NoRegisteredNameException) as e:
        get_name_field(model=NoRegisteredNameException2Model)

    assert str(e.value) == "The model NoRegisteredNameException2Model has no registered name field. Please register a name with register_name_field. It has a field `name` but it's not unique in the database so we can't use that."


def test_register_name_field_error():
    class RegisterNameExceptionModel(Model):
        foo = CharField(max_length=100)

    with pytest.raises(TypeError) as e:
        register_name_field(model=RegisterNameExceptionModel, name_field='foo')

    assert str(e.value) == 'Cannot register name "foo" for model RegisterNameExceptionModel. foo must be unique.'


def test_register_name_field_error_nested():
    class AModel(Model):
        bar = CharField(max_length=100)

    class RegisterNestedNameExceptionModel(Model):
        foo = ForeignKey(AModel, on_delete=CASCADE)

    with pytest.raises(TypeError) as e:
        register_name_field(model=RegisterNestedNameExceptionModel, name_field='foo__bar')

    assert str(e.value) == 'Cannot register name "foo__bar" for model AModel. bar must be unique.'
