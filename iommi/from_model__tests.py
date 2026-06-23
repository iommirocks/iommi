import django
import pytest
from django.contrib.auth.models import (
    Group,
    User,
)
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import (
    CASCADE,
    CharField,
    F,
    ForeignKey,
    IntegerField,
    ManyToOneRel,
    Model,
    Value,
)
from django.db.models.functions import Concat

from iommi import (
    Field,
    Form,
    Query,
    Table,
)
from iommi.from_model import (
    NoRegisteredSearchFieldException,
    SearchFieldsAlreadyRegisteredException,
    create_members_from_model,
    get_field,
    get_field_by_name,
    get_field_name,
    get_field_path,
    get_search_fields,
    member_from_model,
    register_search_fields,
    setup_db_compat_django,
    setup_db_compat_iommi,
)
from iommi.shortcut import with_defaults
from tests.helpers import req
from tests.models import (
    ChoicesModel,
    Foo,
    FormFromModelTest,
    OtherModel,
    SomeModel,
    UniqueConstraintTest,
    Bar,
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


# An item in the `auto__include` list may be a dict carrying the field path under its `attr` key
# and additional configuration passed to that entry, instead of only a plain string.


def test_include_with_dict_items():
    f = Form(
        auto__model=FormFromModelTest,
        auto__include=[
            dict(attr='f_bool', display_name='Boolean!'),
            dict(attr='f_int', display_name='Integer!'),
        ],
    ).bind(request=req('get'))
    assert list(f.fields.keys()) == ['f_bool', 'f_int']
    assert f.fields.f_bool.display_name == 'Boolean!'
    assert f.fields.f_int.display_name == 'Integer!'


def test_include_with_dict_items_respects_ordering():
    # Mixing plain strings and dict items must preserve order *and* apply the per-entry config.
    f = Form(
        auto__model=FormFromModelTest,
        auto__include=[
            dict(attr='f_float', display_name='Float!'),
            'f_bool',
            'f_int',
        ],
    ).bind(request=req('get'))
    assert list(f.fields.keys()) == ['f_float', 'f_bool', 'f_int']
    assert f.fields.f_float.display_name == 'Float!'


def test_include_with_dict_items_dunder_path():
    f = Form(
        auto__model=SomeModel,
        auto__include=[dict(attr='foo__bar', display_name='Bar!')],
    ).bind()
    assert list(f.fields.keys()) == ['foo_bar']
    assert f.fields.foo_bar.attr == 'foo__bar'
    assert f.fields.foo_bar.display_name == 'Bar!'


def test_include_with_dict_items_dunder_path_no_config():
    # A dict item with only `attr` behaves just like including the plain string.
    f = Form(
        auto__model=SomeModel,
        auto__include=[dict(attr='foo__bar')],
    ).bind()
    assert list(f.fields.keys()) == ['foo_bar']
    assert f.fields.foo_bar.attr == 'foo__bar'


def test_include_with_dict_items_config_merges_with_fields_override():
    # An explicit `fields__...` override should win over the config supplied inline in the
    # `auto__include` dict item, while config keys not overridden still come from the dict item.
    f = Form(
        auto__model=FormFromModelTest,
        auto__include=[dict(attr='f_bool', display_name='From include', help_text='From include')],
        fields__f_bool__display_name='From fields override',
    ).bind(request=req('get'))
    assert f.fields.f_bool.display_name == 'From fields override'
    assert f.fields.f_bool.help_text == 'From include'


@pytest.mark.django
@pytest.mark.filterwarnings("ignore:Model 'tests.foomodel' was already registered")
def test_field_from_model_factory_error_message():
    from django.db.models import Field as DjangoField
    from django.db.models import Model

    class CustomField(DjangoField):
        pass

    class FooFromModelTestModel(Model):
        foo = CustomField()

    # Resolution (and therefore the missing-factory error) is now deferred until the containing
    # Form is refine_done'd, so we trigger it by binding a Form built from the model.
    with pytest.raises(AssertionError) as error:
        Form(auto__model=FooFromModelTestModel, auto__include=['foo']).bind()

    assert (
        str(error.value)
        == "No factory for FooFromModelTestModel.foo of type CustomField.\nRegister a factory with register_factory or register_field_factory, you can also register one that returns `None` to not handle this field type."
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


def test_from_model_using_attr():
    class MyForm(Form):
        foo = Field.from_model()
        dunder = Field.from_model(attr='foo__foo')

    f = MyForm(model=Bar).bind()
    declared_fields = f.fields
    assert list(declared_fields.keys()) == ['foo', 'dunder']
    assert declared_fields['dunder'].attr == 'foo__foo'
    assert f.fields.dunder.help_text == 'foo_help_text'

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
    with pytest.raises(SearchFieldsAlreadyRegisteredException) as e:
        register_search_fields(model=User, search_fields=['username'])

    assert 'Cannot register search fields' in str(e.value)
    assert 'overwrite=True' in str(e.value)


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


def test_override_call_target():
    form = Form(
        auto__model=ChoicesModel,
        fields__color__call_target=Field.radio,
    )
    assert form.bind().fields.color.iommi_shortcut_stack == ['radio', 'choice']


def test_override_call_target2():
    form = Form(
        auto__model=ChoicesModel,
        fields__color__call_target__attribute='radio',
    )
    assert form.bind().fields.color.iommi_shortcut_stack == ['radio', 'choice']


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


@pytest.mark.skipif(not django.VERSION[:2] >= (5, 0), reason='Requires django 5.0+')
def test_generated_field():
    from django.db.models import GeneratedField

    class AModel(Model):
        generated_field = GeneratedField(expression=Concat(Value('foo:'), F('pk')), output_field=CharField(max_length=100), db_persist=True)

    form = Form(auto__model=AModel).bind(request=req('get'))
    assert form.fields.generated_field.iommi_shortcut_stack == ['text']


def test_get_field_error_message_lists_valid_field_names():
    class GetFieldErrorModel(Model):
        apple = IntegerField()
        banana = IntegerField()

    with pytest.raises(FieldDoesNotExist) as e:
        get_field(GetFieldErrorModel, 'cherry')

    assert str(e.value) == (
        "GetFieldErrorModel has no field with name 'cherry', valid names are:\n\n"
        "    apple\n    banana\n    id"
    )


def test_get_field_path_error_message():
    class GetFieldPathErrorModel(Model):
        apple = IntegerField()

    with pytest.raises(FieldDoesNotExist) as e:
        get_field_path(GetFieldPathErrorModel, 'nope')

    assert str(e.value) == "GetFieldPathErrorModel has no field with path 'nope'"


def test_get_field_name_excludes_plus_reverse_relation():
    class GetFieldNamePlusTarget(Model):
        pass

    class GetFieldNamePlusSource(Model):
        target = ForeignKey(GetFieldNamePlusTarget, on_delete=CASCADE, related_name='+')

    # A reverse relation declared with related_name='+' is hidden and must not get a name.
    reverse_rel = [
        f
        for f in GetFieldNamePlusTarget._meta.get_fields(include_hidden=True)
        if isinstance(f, ManyToOneRel) and f.related_name == '+'
    ]
    assert len(reverse_rel) == 1
    assert get_field_name(reverse_rel[0]) is None


def test_get_field_by_name_is_cached():
    class GetFieldByNameCacheModel(Model):
        apple = IntegerField()

    first = get_field_by_name(GetFieldByNameCacheModel)
    second = get_field_by_name(GetFieldByNameCacheModel)
    assert first is second


def test_register_search_fields_allows_member_of_unique_together():
    # f_int is not unique on its own, but it is part of a unique_together, so registering
    # it as a search field is allowed and must not raise.
    register_search_fields(
        model=UniqueConstraintTest,
        search_fields=['f_int'],
        overwrite=True,
    )


def test_member_from_model_requires_field_or_name():
    with pytest.raises(AssertionError) as e:
        member_from_model(
            cls=Field,
            model=Foo,
            factory_lookup={},
            defaults_factory=lambda model_field: {},
            factory_lookup_register_function=lambda: None,
            related_factory_lookup={},
            related_multiple_factory_lookup={},
        )

    assert str(e.value) == "Field can't be automatically created from model, you must specify it manually"


def test_create_members_from_model_default_included_false_sets_include_false():
    members = create_members_from_model(member_class=Field, model=SomeModel, default_included=False)

    assert members
    for member in members.values():
        assert member.config_from_model.get('include') is False


def test_register_search_fields_pk_does_not_short_circuit_validation():
    # 'pk'/'id' are skipped via `continue`, not `break`: a later invalid field must still be validated.
    class PkContinueModel(Model):
        foo = CharField(max_length=100)  # not unique

    with pytest.raises(TypeError):
        register_search_fields(model=PkContinueModel, search_fields=['pk', 'foo'], overwrite=True)


def test_register_search_fields_stores_the_given_fields():
    register_search_fields(model=User, search_fields=['username'], overwrite=True)

    assert get_search_fields(model=User) == ['username']


class ShortcutFromModelTest(Model):
    f_char = models.CharField(max_length=10)
    f_int = models.IntegerField()
    f_uuid = models.UUIDField()
    f_time = models.TimeField()
    f_email = models.EmailField()
    f_decimal = models.DecimalField(max_digits=5, decimal_places=2)
    f_date = models.DateField()
    f_datetime = models.DateTimeField()
    f_float = models.FloatField()
    f_file = models.FileField()
    f_ip = models.GenericIPAddressField()
    f_filepath = models.FilePathField()
    f_duration = models.DurationField()
    f_bool = models.BooleanField()
    f_bool_null = models.BooleanField(null=True)
    f_text = models.TextField()
    f_url = models.URLField()
    f_image = models.ImageField()
    # Registered with factory=None / include=False respectively, so neither is auto-generated:
    f_binary = models.BinaryField()
    f_json = models.JSONField()

    class Meta:
        app_label = 'tests'


# `setup_db_compat_django()` runs once at iommi import time, so the field-type -> shortcut
# registrations it performs are not re-executed during any test. The tests below re-invoke it
# (it just re-registers the same factories) so that the registration code actually runs while
# the test is executing — this both exercises the contract and lets mutation testing attribute
# the registrations to these tests. The values asserted are the full, exact mapping, so changing
# any single registration is caught.


def test_form_field_shortcuts_for_model_field_types():
    setup_db_compat_django()
    form = Form(auto__model=ShortcutFromModelTest).bind(request=req('get'))

    assert {name: field.iommi_shortcut_stack for name, field in form.fields.items()} == {
        'f_char': ['text'],
        'f_int': ['integer', 'number'],
        'f_uuid': ['text'],
        'f_time': ['time'],
        'f_email': ['email'],
        'f_decimal': ['decimal', 'number'],
        'f_date': ['date'],
        'f_datetime': ['datetime'],
        'f_float': ['float', 'number'],
        'f_file': ['file'],
        'f_ip': ['text'],
        'f_filepath': ['text'],
        'f_duration': ['duration', 'text'],
        'f_bool': ['boolean'],
        'f_bool_null': ['boolean_tristate', 'choice'],
        'f_text': ['textarea'],
        'f_url': ['url'],
        'f_image': ['image', 'file'],
    }


def test_column_shortcuts_for_model_field_types():
    setup_db_compat_django()
    table = Table(auto__model=ShortcutFromModelTest).bind(request=req('get'))

    assert {name: column.iommi_shortcut_stack for name, column in table.columns.items()} == {
        'f_char': ['text'],
        'f_int': ['integer', 'number'],
        'f_uuid': ['text'],
        'f_time': ['time'],
        'f_email': ['email'],
        'f_decimal': ['decimal'],
        'f_date': ['date'],
        'f_datetime': ['datetime'],
        'f_float': ['float', 'number'],
        'f_file': ['file'],
        'f_ip': ['text'],
        'f_filepath': ['text'],
        'f_duration': ['duration', 'text'],
        'f_bool': ['boolean'],
        'f_bool_null': ['boolean'],
        'f_text': ['text'],
        'f_url': ['text'],
        'f_image': ['file'],
    }


def test_filter_shortcuts_for_model_field_types():
    setup_db_compat_django()
    query = Query(auto__model=ShortcutFromModelTest).bind(request=req('get'))

    assert {name: f.iommi_shortcut_stack for name, f in query.filters.items()} == {
        'f_char': ['text'],
        'f_int': ['integer', 'number'],
        'f_uuid': ['text'],
        'f_time': ['time'],
        'f_email': ['email'],
        'f_decimal': ['decimal', 'number'],
        'f_date': ['date'],
        'f_datetime': ['datetime'],
        'f_float': ['float', 'number'],
        'f_file': ['file'],
        'f_ip': ['text'],
        'f_filepath': ['text'],
        'f_duration': ['duration', 'text'],
        'f_bool': ['boolean'],
        'f_bool_null': ['boolean'],
        'f_text': ['text'],
        'f_url': ['url'],
        'f_image': ['file'],
    }


def test_json_field_excluded_by_default_but_text_when_included():
    setup_db_compat_django()
    form = Form(auto__model=ShortcutFromModelTest).bind(request=req('get'))
    assert 'f_json' not in form.fields
    assert 'f_binary' not in form.fields

    form = Form(auto__model=ShortcutFromModelTest, auto__include=['f_char', 'f_json']).bind(request=req('get'))
    assert form.fields.f_json.iommi_shortcut_stack == ['text']


def test_relation_field_shortcuts_from_model():
    from tests.models import (
        FieldFromModelForeignKeyTest,
        FieldFromModelManyToManyTest,
        FieldFromModelOneToOneTest,
    )

    setup_db_compat_django()
    fk_field = Form(auto__model=FieldFromModelForeignKeyTest, auto__include=['foo_fk']).bind(request=req('get')).fields.foo_fk
    o2o_field = Form(auto__model=FieldFromModelOneToOneTest, auto__include=['foo_one_to_one']).bind(request=req('get')).fields.foo_one_to_one
    m2m_field = Form(auto__model=FieldFromModelManyToManyTest, auto__include=['foo_many_to_many']).bind(request=req('get')).fields.foo_many_to_many

    assert fk_field.iommi_shortcut_stack[0] == 'related'
    assert o2o_field.iommi_shortcut_stack[0] == 'related'
    assert m2m_field.iommi_shortcut_stack[0] == 'related_multiple'


def test_choice_field_shortcuts_from_model():
    setup_db_compat_django()
    form = Form(auto__model=ChoicesModel, auto__include=['color']).bind(request=req('get'))
    table = Table(auto__model=ChoicesModel, auto__include=['color']).bind(request=req('get'))
    query = Query(auto__model=ChoicesModel, auto__include=['color']).bind(request=req('get'))

    assert form.fields.color.iommi_shortcut_stack == ['choice']
    assert table.columns.color.iommi_shortcut_stack == ['choice']
    assert query.filters.color.iommi_shortcut_stack == ['choice']


def test_choice_field_display_name_formatter_from_model():
    # The CharField factory builds a formatter that maps the stored choice value to its label,
    # falling back to the raw value for anything not in the choices. This is wired into the form
    # field, the table column's cell formatting, and the filter's field.
    setup_db_compat_django()
    field = Form(auto__model=ChoicesModel, auto__include=['color']).bind(request=req('get')).fields.color
    column = Table(auto__model=ChoicesModel, auto__include=['color']).bind(request=req('get')).columns.color
    filter = Query(auto__model=ChoicesModel, auto__include=['color']).bind(request=req('get')).filters.color

    assert field.choices == ['purple', 'orange']
    assert field.choice_display_name_formatter('purple') == 'Purple'
    assert field.choice_display_name_formatter('orange') == 'Orange'
    # Unknown values fall back to the value itself rather than None.
    assert field.choice_display_name_formatter('not_a_choice') == 'not_a_choice'

    assert column.cell.format(value='purple') == 'Purple'
    assert column.cell.format(value='not_a_choice') == 'not_a_choice'
    # The column also wires the same formatter into its own filter's field.
    assert column.filter.field.choice_display_name_formatter('purple') == 'Purple'

    assert filter.field.choice_display_name_formatter('purple') == 'Purple'
    assert filter.field.choice_display_name_formatter('not_a_choice') == 'not_a_choice'


@pytest.mark.django_db
def test_choices_from_model_field_resolves_callable_limit_choices_to():
    from tests.models import CallableLimitTarget, LimitChoicesToCallableFKTest

    CallableLimitTarget.objects.create(foo=2)
    b = CallableLimitTarget.objects.create(foo=3)
    c = CallableLimitTarget.objects.create(foo=5)

    class MyForm(Form):
        class Meta:
            model = LimitChoicesToCallableFKTest

        foo_fk = Field.from_model()

    form = MyForm().bind(request=req('get'))
    assert set(form.fields.foo_fk.choices) == {b, c}


def test_auto_field_uses_integer_shortcut_when_explicitly_included():
    # AutoField (the pk) is registered with include=False, but when explicitly included it uses
    # the 'integer' shortcut.
    setup_db_compat_django()
    form = Form(auto__model=FormFromModelTest, auto__include=['id']).bind(request=req('get'))

    assert form.fields.id.iommi_shortcut_stack == ['integer', 'number']


def test_reverse_many_to_many_relation_shortcut():
    from tests.models import ReverseRelationTarget

    setup_db_compat_django()
    # A reverse ManyToMany relation is include=False by default ...
    assert 'm2m_sources' not in Form(auto__model=ReverseRelationTarget).bind(request=req('get')).fields
    # ... and uses the related_multiple shortcut when explicitly included.
    field = Form(auto__model=ReverseRelationTarget, auto__include=['m2m_sources']).bind(request=req('get')).fields.m2m_sources
    column = Table(auto__model=ReverseRelationTarget, auto__include=['m2m_sources']).bind(request=req('get')).columns.m2m_sources

    assert field.iommi_shortcut_stack[0] == 'related_multiple'
    assert column.iommi_shortcut_stack[0] == 'related_multiple'


def test_reverse_relations_and_auto_field_excluded_by_default():
    # AutoField (the pk) and reverse relations (Bar.foo / Qux.foo) are registered with
    # include=False, so a default auto Form only contains the model's own concrete field.
    setup_db_compat_django()
    form = Form(auto__model=Foo).bind(request=req('get'))

    assert list(form.fields.keys()) == ['foo']


def test_related_choices_from_model_field_rejects_unknown_field_type():
    from iommi.from_model import related_choices_from_model_field

    # A plain (non-relation) field is not a valid related field and must trip the assertion.
    not_a_relation = Foo._meta.get_field('foo')
    with pytest.raises(AssertionError):
        related_choices_from_model_field(not_a_relation)


def test_reverse_relation_shortcuts_from_model():
    from tests.models import ExpandModelTestA

    setup_db_compat_django()
    # reverse ForeignKey (ManyToOneRel) -> related_multiple
    reverse_fk = Form(auto__model=Foo, auto__include=['bars']).bind(request=req('get')).fields.bars
    reverse_fk_column = Table(auto__model=Foo, auto__include=['bars']).bind(request=req('get')).columns.bars
    # reverse OneToOne (OneToOneRel) -> related
    reverse_o2o = Form(auto__model=ExpandModelTestA, auto__include=['expandmodeltestb']).bind(request=req('get')).fields.expandmodeltestb

    assert reverse_fk.iommi_shortcut_stack[0] == 'related_multiple'
    assert reverse_fk_column.iommi_shortcut_stack[0] == 'related_multiple'
    assert reverse_o2o.iommi_shortcut_stack[0] == 'related'


def test_edit_column_sort_order_uses_reorder_handle_shortcut():
    from docs.models import FavoriteArtist
    from iommi import EditTable

    setup_db_compat_iommi()
    edit_table = EditTable(auto__model=FavoriteArtist, auto__include=['sort_order']).bind(request=req('get'))

    assert edit_table.columns.sort_order.iommi_shortcut_stack == ['reorder_handle']


def test_register_related_factory_registers_field_filter_and_column():
    from iommi.form import _related_field_factory_by_model
    from iommi.from_model import register_related_factory
    from iommi.query import _related_filter_factory_by_model
    from iommi.table import _related_column_factory_by_model

    class RegisterRelatedFactoryModel(Model):
        pass

    # shortcut_name and any extra kwargs are forwarded to all three component registries.
    register_related_factory(RegisterRelatedFactoryModel, shortcut_name='choice', extra__foo=7)

    for registry in (_related_field_factory_by_model, _related_filter_factory_by_model, _related_column_factory_by_model):
        assert registry[RegisterRelatedFactoryModel]['call_target']['attribute'] == 'choice'
        assert registry[RegisterRelatedFactoryModel]['extra']['foo'] == 7

    # An explicit factory is forwarded verbatim (instead of being built from shortcut_name).
    class RegisterRelatedFactoryModel2(Model):
        pass

    sentinel_factory = object()
    register_related_factory(RegisterRelatedFactoryModel2, factory=sentinel_factory)

    for registry in (_related_field_factory_by_model, _related_filter_factory_by_model, _related_column_factory_by_model):
        assert registry[RegisterRelatedFactoryModel2] is sentinel_factory


def test_register_related_multiple_factory_registers_field_filter_and_column():
    from iommi.form import _related_multiple_field_factory_by_model
    from iommi.from_model import register_related_multiple_factory
    from iommi.query import _related_multiple_filter_factory_by_model
    from iommi.table import _related_multiple_column_factory_by_model

    class RegisterRelatedMultipleFactoryModel(Model):
        pass

    register_related_multiple_factory(RegisterRelatedMultipleFactoryModel, shortcut_name='multi_choice', extra__foo=7)

    for registry in (_related_multiple_field_factory_by_model, _related_multiple_filter_factory_by_model, _related_multiple_column_factory_by_model):
        assert registry[RegisterRelatedMultipleFactoryModel]['call_target']['attribute'] == 'multi_choice'
        assert registry[RegisterRelatedMultipleFactoryModel]['extra']['foo'] == 7

    class RegisterRelatedMultipleFactoryModel2(Model):
        pass

    sentinel_factory = object()
    register_related_multiple_factory(RegisterRelatedMultipleFactoryModel2, factory=sentinel_factory)

    for registry in (_related_multiple_field_factory_by_model, _related_multiple_filter_factory_by_model, _related_multiple_column_factory_by_model):
        assert registry[RegisterRelatedMultipleFactoryModel2] is sentinel_factory
