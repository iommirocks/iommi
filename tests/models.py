from django.db.models import Model, IntegerField, ForeignKey, CharField


class Foo(Model):
    value = IntegerField(help_text='foo_help_text')

    def __repr__(self):
        return 'Foo pk: %s' % self.pk


class Bar(Model):
    foo = ForeignKey(Foo)


class Baz(Model):
    name = CharField(max_length=255)
