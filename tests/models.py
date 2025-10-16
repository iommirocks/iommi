import django
from django.core import validators
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    FileField,
    FloatField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    Model,
    OneToOneField,
    UUIDField,
    UniqueConstraint,
    TextChoices,
    PositiveSmallIntegerField,
    Field,
)

from iommi import register_search_fields


class FormFromModelTest(Model):
    f_int = IntegerField()
    f_float = FloatField()
    f_bool = BooleanField()
    f_file = FileField()

    f_int_excluded = IntegerField()


class Foo(Model):
    foo = IntegerField(help_text='foo_help_text')

    def __repr__(self):
        return f'Foo pk: {self.pk}'  # pragma: no cover

    @property
    def qux(self):
        return self.quxes.first()


class Bar(Model):
    foo = ForeignKey(Foo, related_name='bars', on_delete=CASCADE, help_text='bar_help_text')


class FieldFromModelForeignKeyTest(Model):
    foo_fk = ForeignKey(Foo, on_delete=CASCADE)


class Qux(Model):
    foo = ForeignKey(Foo, related_name='quxes', related_query_name='qux', on_delete=CASCADE)
    lang = CharField(max_length=7)
    name = CharField(max_length=255, blank=True)


class FieldFromModelOneToOneTest(Model):
    foo_one_to_one = OneToOneField(Foo, on_delete=CASCADE)
    f_char = CharField(max_length=255, blank=True)


class ExpandModelTestA(Model):
    f_int = IntegerField()
    f_float = FloatField()
    f_bool = BooleanField()


class ExpandModelTestB(Model):
    link = OneToOneField(ExpandModelTestA, on_delete=CASCADE)


class FieldFromModelManyToManyTest(Model):
    foo_many_to_many = ManyToManyField(Foo)


class FooField(IntegerField):
    pass


class RegisterFieldFactoryTest(Model):
    foo = FooField()


class UniqueConstraintTest(Model):
    f_int = IntegerField()
    f_float = FloatField()
    f_bool = BooleanField()

    class Meta:
        unique_together = ('f_int', 'f_float', 'f_bool')


class UniqueConstraintAlternativeTest(Model):
    """Test unique constraints defined with UniqueConstraint
    instead of unique_together."""

    f_int = IntegerField()
    f_float = FloatField()
    f_bool = BooleanField()

    class Meta:
        verbose_name = "Unique constraint test"
        constraints = [UniqueConstraint(fields=('f_int', 'f_float', 'f_bool'), name="unique_test")]


class NamespaceFormsTest(Model):
    f_int = IntegerField()
    f_float = FloatField()
    f_bool = BooleanField()

    class Meta:
        unique_together = ('f_int', 'f_float', 'f_bool')
        verbose_name = 'foo_bar'


class CreateOrEditObjectTest(Model):
    f_int = IntegerField()
    f_float = FloatField()
    f_bool = BooleanField()
    f_foreign_key = ForeignKey(Foo, on_delete=CASCADE)
    f_many_to_many = ManyToManyField(Foo)

    class Meta:
        verbose_name = 'foo_bar'


class Baz(Model):
    a = IntegerField()
    b = IntegerField()

    class Meta:
        unique_together = ('a', 'b')


class FromModelWithInheritanceTest(Model):
    value = FloatField()

    class Meta:
        ordering = ('pk',)


class EndPointDispatchModel(Model):
    name = CharField(max_length=255, unique=True)


class NonStandardName(Model):
    non_standard_name = CharField(max_length=255)


class TFoo(Model):
    a = IntegerField()
    b = CharField(max_length=255)

    def __str__(self):
        return 'Foo({}, {})'.format(self.a, self.b)

    class Meta:
        ordering = ('pk',)


class TBar(Model):
    foo = ForeignKey(TFoo, on_delete=CASCADE)
    c = BooleanField()

    class Meta:
        ordering = ('pk',)


register_search_fields(model=TBar, search_fields=['pk'])


class TBar2(Model):
    bar = ForeignKey(TBar, on_delete=CASCADE)

    class Meta:
        ordering = ('pk',)


class TBaz(Model):
    foo = ManyToManyField(TFoo)

    class Meta:
        ordering = ('pk',)


class AdminUnique(Model):
    foo = IntegerField()
    unique = IntegerField(unique=True)

    class Meta:
        ordering = ('pk',)


class BooleanFromModelTestModel(Model):
    b = BooleanField(help_text='$$$$')

    class Meta:
        ordering = ('pk',)


class CSVExportTestModel(Model):
    a = IntegerField()
    b = CharField(max_length=1)
    c = FloatField()
    d = IntegerField(null=True)
    danger = CharField(max_length=255, default="=2+5+cmd|' /C calc'!A0")

    class Meta:
        ordering = ('pk',)


class QueryFromIndexesTestModel(Model):
    a = IntegerField()
    b = CharField(max_length=1, db_index=True)
    c = FloatField(db_index=True)
    d = ForeignKey(TFoo, on_delete=CASCADE, related_name='+')

    class Meta:
        ordering = ('pk',)


class AutomaticUrl(Model):
    a = IntegerField()

    def __str__(self):
        return 'the str of AutomaticUrl'

    def get_absolute_url(self):
        return 'url here!'


class AutomaticUrl2(Model):
    foo = ForeignKey(AutomaticUrl, on_delete=CASCADE)

    class Meta:
        ordering = ('pk',)


class T1(Model):
    foo = CharField(max_length=255)
    bar = CharField(max_length=255)

    class Meta:
        ordering = ('id',)


class T2(Model):
    foo = CharField(max_length=255)
    bar = CharField(max_length=255)

    class Meta:
        ordering = ('id',)


class EvilNames(Model):
    values = CharField(max_length=255)
    keys = CharField(max_length=255)
    items = CharField(max_length=255)

    class Meta:
        ordering = ('id',)


class DefaultsInForms(Model):
    name = CharField(max_length=255, default='<name>')
    number = IntegerField(default=7)


class SortKeyOnForeignKeyA(Model):
    name = CharField(max_length=255, db_index=True, unique=True)


class SortKeyOnForeignKeyB(Model):
    remote = ForeignKey(SortKeyOnForeignKeyA, on_delete=CASCADE)


class ChoicesModel(Model):
    CHOICES = [('purple', 'Purple'), ('orange', 'Orange')]
    color = CharField(choices=CHOICES, max_length=255)


if django.VERSION[:2] >= (3, 0):

    class ChoicesClassModel(Model):
        class ColorChoices(TextChoices):
            PURPLE = ('purple_thing-thing', 'Purple')
            ORANGE = ('orange', 'Orange')

        color = CharField(choices=ColorChoices.choices, max_length=255)


class IntChoicesModel(Model):
    CHOICES = [(301, '301 Moved Permanently'), (302, '302 Found'), (303, '303 See Other')]
    status = PositiveSmallIntegerField(choices=CHOICES)


class CamelCaseFieldModel(Model):
    camelCaseField = BooleanField()  # noqa: N815


class CustomField(Field):
    pass


class NotRegisteredCustomFieldModel(Model):
    custom_field = CustomField()


class OtherModel(Model):
    bar = CharField(max_length=255)


class SomeModel(Model):
    foo = ForeignKey(OtherModel, on_delete=CASCADE)


class TestModelValidators(Model):
    bar = CharField(max_length=5)
    slug = CharField(max_length=255, validators=[validators.validate_slug])

class UuidPKModel(Model):
    id = UUIDField(primary_key=True)
    foo = CharField(max_length=255)

