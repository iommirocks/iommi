import pytest
from django.contrib.auth.models import (
    Group,
    User,
)
from django.core.exceptions import FieldDoesNotExist
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
    NoRegisteredSearchFieldException,
    SearchFieldsAlreadyRegisteredException,
    get_field,
    get_field_path,
    get_search_fields,
    register_search_fields,
)
from iommi.shortcut import with_defaults
from tests.helpers import req
from tests.models import (
    Foo,
    FormFromModelTest,
    OtherModel,
    SomeModel,
)


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
    from django.db.models import Field as DjangoField
    from django.db.models import Model

    class CustomField(DjangoField):
        pass

    class FooFromModelTestModel(Model):
        foo = CustomField()

    with pytest.raises(AssertionError) as error:
        Field.from_model(FooFromModelTestModel, 'foo')

    assert (
        str(error.value)
        == "No factory for FooFromModelTestModel.foo of type CustomField. Register a factory with register_factory or register_field_factory, you can also register one that returns None to not handle this field type"
    )


def test_from_model():
    f = Form(
        auto__model=SomeModel,
        auto__include=['foo__bar'],
    ).bind()
    declared_fields = f.fields
    assert list(declared_fields.keys()) == ['foo_bar']
    assert declared_fields['foo_bar'].attr == 'foo__bar'


def test_from_model_declarative_style():
    class MyForm(Form):
        foo = Field.from_model(model_field=SomeModel.foo.field)
        foo_bar = Field.from_model(attr='foo__bar', model_field=OtherModel.bar.field)

    f = MyForm().bind()
    declared_fields = f.fields
    assert list(declared_fields.keys()) == ['foo', 'foo_bar']
    assert declared_fields['foo_bar'].attr == 'foo__bar'


@pytest.mark.skip('This would require major reshuffle of how auto__ is done...')
def test_from_model_using_attr():
    class MyForm(Form):
        foo = Field.from_model()
        foo_bar = Field.from_model(attr='foo__bar')

    f = MyForm().bind()
    declared_fields = f.fields
    assert list(declared_fields.keys()) == ['foo', 'foo_bar']
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
    foo__somemodel_set'''
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


@pytest.fixture
def MyField():  # noqa: N802
    class MyField(Field):
        @classmethod
        @with_defaults(
            extra__value='this is my shortcut',
        )
        def my_integer(cls, **kwargs):
            return cls.integer(**kwargs)

    return MyField


def test_weird_override_bug_working_case(MyField):  # noqa: N803
    # This works...
    form = Form(
        fields__foo__call_target=MyField.my_integer,
    )
    assert form.bind().fields.foo.extra.value == 'this is my shortcut'


def test_weird_override_bug_working_case_2(MyField):  # noqa: N803
    # This also works
    form = Form(
        auto__model=Foo,
        auto__include=['foo'],
        fields__foo=MyField.my_integer(),
    )
    assert form.bind().fields.foo.extra.value == 'this is my shortcut'


def test_get_field_many_to_many_reverse():
    # This test looks weird because Django's API is weird. `Group.user_set` is not the same as the "field", and the "field" is misnamed as "user" for some reason
    assert get_field(Group, 'user_set') == Group._meta.get_field('user')

    with pytest.raises(FieldDoesNotExist):
        get_field(Group, 'user')


def test_error_includes_reverse_field(MyField):  # noqa: N803
    form = Form(
        auto__model=Group,
        auto__include=['does_not_exist'],
    )
    with pytest.raises(AssertionError) as e:
        form.bind()

    assert 'user_set' in str(e.value)
