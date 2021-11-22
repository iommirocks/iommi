import pytest
from django.contrib.auth.models import User
from django.db.models import (
    CASCADE,
    CharField,
    ForeignKey,
    IntegerField,
    Model,
)
from iommi import (
    Field,
    Form,
)
from iommi.from_model import (
    get_field_path,
    get_search_fields,
    NoRegisteredSearchFieldException,
    register_search_fields,
    SearchFieldsAlreadyRegisteredException,
)
from tests.helpers import req
from tests.models import (
    Foo,
    FormFromModelTest,
)
from tri_declarative import class_shortcut


def test_get_name_field_for_model_error():
    class NoRegisteredNameExceptionModel(Model):
        pass

    with pytest.raises(NoRegisteredSearchFieldException) as e:
        get_search_fields(model=NoRegisteredNameExceptionModel)

    assert (
        str(e.value)
        == 'NoRegisteredNameExceptionModel has no registered search fields. Please register a list of field names with register_search_fields.'
    )


def test_get_name_field_for_model_error_non_unique():
    class NoRegisteredNameException2Model(Model):
        name = IntegerField()

    with pytest.warns(Warning) as records:
        get_search_fields(model=NoRegisteredNameException2Model)

    assert (
        str(records[0].message)
        == "The model NoRegisteredNameException2Model is using the default `name` field as a search field, but it's not unique. You can register_search_fields(model=NoRegisteredNameException2Model, search_fields=['name'], allow_non_unique=True) to silence this warning. The reason we are warning is because you won't be able to use the advanced query language with non-unique names."
    )


def test_register_search_fields_error():
    class RegisterNameExceptionModel(Model):
        foo = CharField(max_length=100)

    with pytest.raises(TypeError) as e:
        register_search_fields(model=RegisterNameExceptionModel, search_fields=['foo'])

    assert (
        str(e.value) == 'Cannot register search field "foo" for model RegisterNameExceptionModel. foo must be unique.'
    )


def test_register_search_fields_error_nested():
    class AModel(Model):
        bar = CharField(max_length=100)

    class RegisterNestedNameExceptionModel(Model):
        foo = ForeignKey(AModel, on_delete=CASCADE)

    with pytest.raises(TypeError) as e:
        register_search_fields(model=RegisterNestedNameExceptionModel, search_fields=['foo__bar'])

    assert str(e.value) == 'Cannot register search field "foo__bar" for model AModel. bar must be unique.'


def test_respect_include_ordering():
    include = [
        'f_bool',
        'f_float',
        'f_file',
        'f_int',
    ]
    f = Form(
        auto__model=FormFromModelTest,
        auto__include=include,
    ).bind(request=req('get'))
    assert list(f.fields.keys()) == include


def test_exclude():
    f = Form(
        auto__model=FormFromModelTest,
        auto__exclude=[
            'f_bool',
            'f_int',
        ],
    ).bind(request=req('get'))
    assert list(f.fields.keys()) == ['f_float', 'f_file', 'f_int_excluded']


def test_include_not_existing_error():
    with pytest.raises(AssertionError) as e:
        Form(
            auto__model=FormFromModelTest,
            auto__include=['does_not_exist'],
        ).bind()

    assert (
        str(e.value)
        == 'You can only include fields that exist on the model: does_not_exist specified but does not exist\nExisting fields:\n    f_bool\n    f_file\n    f_float\n    f_int\n    f_int_excluded\n    id\n    pk'
    )


def test_exclude_not_existing_error():
    with pytest.raises(AssertionError) as e:
        Form(
            auto__model=FormFromModelTest,
            auto__exclude=['does_not_exist'],
        ).bind()

    assert (
        str(e.value)
        == 'You can only exclude fields that exist on the model: does_not_exist specified but does not exist\nExisting fields:\n    f_bool\n    f_file\n    f_float\n    f_int\n    f_int_excluded\n    id\n    pk'
    )


@pytest.mark.django
@pytest.mark.filterwarnings("ignore:Model 'tests.foomodel' was already registered")
def test_field_from_model_factory_error_message():
    from django.db.models import Field as DjangoField, Model

    class CustomField(DjangoField):
        pass

    class FooFromModelTestModel(Model):
        foo = CustomField()

    with pytest.raises(AssertionError) as error:
        Field.from_model(FooFromModelTestModel, 'foo')

    assert (
        str(error.value)
        == "No factory for CustomField. Register a factory with register_factory or register_field_factory, you can also register one that returns None to not handle this field type"
    )


class OtherModel(Model):
    bar = CharField()


class SomeModel(Model):
    foo = ForeignKey(OtherModel, on_delete=CASCADE)


def test_from_model():

    f = Form(
        auto__model=SomeModel,
        auto__include=['foo__bar'],
    ).bind()
    declared_fields = f.fields
    assert list(declared_fields.keys()) == ['foo_bar']
    assert declared_fields['foo_bar'].attr == 'foo__bar'


def test_from_model_missing_subfield():
    with pytest.raises(Exception) as e:
        Form(
            auto__model=SomeModel,
            auto__include=['foo__barf'],
        ).bind()
    assert (
        str(e.value)
        == '''\
You can only include fields that exist on the model: foo__barf specified but does not exist
Existing fields:
    foo__bar
    foo__id
    foo__pk
    foo__somemodel'''
    )


def test_get_field_path():
    assert get_field_path(SomeModel, 'foo__bar') == OtherModel._meta.get_field('bar')
    assert get_field_path(OtherModel, 'bar') == OtherModel._meta.get_field('bar')


def test_register_search_fields_already_registered():
    with pytest.raises(SearchFieldsAlreadyRegisteredException):
        register_search_fields(model=User, search_fields=['username'])


def test_register_search_fields_pk_special_case():
    # pk doesn't exist on the model but it's still valid
    register_search_fields(model=User, search_fields=['pk'], overwrite=True)

    # restore at the end
    register_search_fields(model=User, search_fields=['username'], overwrite=True)


# noinspection PyPep8Naming
@pytest.fixture
def MyField():
    class MyField(Field):
        @classmethod
        @class_shortcut(
            call_target__attribute='integer',
            extra__value='this is my shortcut',
        )
        def my_integer(cls, call_target=None, **kwargs):
            return call_target(**kwargs)
    return MyField


def test_weird_override_bug_working_case(MyField):

    # This works...
    form = Form(
        fields__foo__call_target=MyField.my_integer,
    )
    assert form.bind().fields.foo.extra.value == 'this is my shortcut'


def test_weird_override_bug_working_case_2(MyField):
    # This also works
    form = Form(
        auto__model=Foo,
        auto__include=['foo'],
        fields__foo=MyField.my_integer(),
    )
    assert form.bind().fields.foo.extra.value == 'this is my shortcut'


@pytest.mark.skip('This fails after from_model cleanup. Do we really need it?')
def test_weird_override_bug_failing_case(MyField):
    form = Form.edit(
        auto__model=Foo,
        auto__include=['foo'],
        fields__foo__call_target=MyField.my_integer,
    )
    assert form.bind().fields.foo.extra.value == 'this is my shortcut'


@pytest.mark.skip('This fails after from_model cleanup. Do we really need it?')
def test_weird_override_bug_failing_case2(MyField):
    form = Form.edit(
        auto__model=Foo,
        auto__include=['foo'],
        fields__foo__call_target__attribute='float',
    )
    assert form.bind().fields.foo.__tri_declarative_shortcut_stack == ['float']
