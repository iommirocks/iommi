from tri.declarative import Shortcut

from tri.query import register_variable_factory


def setup_db_compat():
    setup_db_compat_django()


def setup_db_compat_django():
    from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, DateField, DateTimeField, DecimalField, EmailField, URLField, TimeField, ForeignKey, ManyToOneRel, ManyToManyField, ManyToManyRel

    # The order here is significant because of inheritance structure. More specific must be below less specific.
    register_variable_factory(CharField, Shortcut()),
    register_variable_factory(URLField, Shortcut(call_target__attribute='url')),
    register_variable_factory(TimeField, Shortcut(call_target__attribute='time')),
    register_variable_factory(EmailField, Shortcut(call_target__attribute='email')),
    register_variable_factory(DecimalField, Shortcut(call_target__attribute='decimal')),
    register_variable_factory(DateField, Shortcut(call_target__attribute='date')),
    register_variable_factory(DateTimeField, Shortcut(call_target__attribute='datetime')),
    register_variable_factory(BooleanField, Shortcut(call_target__attribute='boolean')),
    register_variable_factory(TextField, Shortcut(call_target__attribute='text')),
    register_variable_factory(FloatField, Shortcut(call_target__attribute='float')),
    register_variable_factory(IntegerField, Shortcut(call_target__attribute='integer')),

    register_variable_factory(AutoField, Shortcut(call_target__attribute='integer', show=False))
    register_variable_factory(ManyToManyField, Shortcut(call_target__attribute='many_to_many'))

    register_variable_factory(ManyToOneRel, None),
    register_variable_factory(ManyToManyRel, None),
    register_variable_factory(ForeignKey, Shortcut(call_target__attribute='foreign_key'))
