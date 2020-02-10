from django.db.models import Model, IntegerField, BooleanField, FloatField, ForeignKey, OneToOneField, ManyToManyField, \
    FileField, CASCADE, CharField


class FormFromModelTest(Model):
    f_int = IntegerField()
    f_float = FloatField()
    f_bool = BooleanField()
    f_file = FileField()

    f_int_excluded = IntegerField()


class Foo(Model):
    foo = IntegerField(help_text='foo_help_text')

    def __repr__(self):
        return 'Foo pk: %s' % self.pk


class Bar(Model):
    foo = ForeignKey(Foo, related_name='bars', on_delete=CASCADE, help_text='bar_help_text')


class FieldFromModelForeignKeyTest(Model):
    foo_fk = ForeignKey(Foo, on_delete=CASCADE)


class FieldFromModelOneToOneTest(Model):
    foo_one_to_one = OneToOneField(Foo, on_delete=CASCADE)


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
        return 'Foo(%s, %s)' % (self.a, self.b)

    class Meta:
        ordering = ('pk',)


class TBar(Model):
    foo = ForeignKey(TFoo, on_delete=CASCADE)
    c = BooleanField()

    class Meta:
        ordering = ('pk',)


class TBaz(Model):
    foo = ManyToManyField(TFoo)

    class Meta:
        ordering = ('pk',)
        
        
class AdminUnique(Model):
    foo = IntegerField()
    unique = IntegerField(unique=True)


class BooleanFromModelTestModel(Model):
    b = BooleanField(help_text='$$$$')
