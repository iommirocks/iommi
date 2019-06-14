from tri_declarative import Shortcut


def setup_db_compat():
    setup_db_compat_django()


def setup_db_compat_django():
    from tri_table import register_column_factory
    try:
        # noinspection PyUnresolvedReferences
        from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, DateField, DateTimeField, DecimalField, EmailField, TimeField, ForeignKey, ManyToOneRel, ManyToManyField, ManyToManyRel
    except ImportError:
        pass
    else:
        # The order here is significant because of inheritance structure. More specific must be below less specific.

        register_column_factory(CharField, Shortcut(call_target__attribute='text'))
        register_column_factory(TimeField, Shortcut(call_target__attribute='time'))
        register_column_factory(EmailField, Shortcut(call_target__attribute='email'))
        register_column_factory(DecimalField, Shortcut(call_target__attribute='decimal'))
        register_column_factory(DateField, Shortcut(call_target__attribute='date'))
        register_column_factory(DateTimeField, Shortcut(call_target__attribute='datetime'))
        register_column_factory(BooleanField, Shortcut(call_target__attribute='boolean'))
        register_column_factory(TextField, Shortcut(call_target__attribute='text'))
        register_column_factory(FloatField, Shortcut(call_target__attribute='float'))
        register_column_factory(IntegerField, Shortcut(call_target__attribute='integer'))
        register_column_factory(AutoField, Shortcut(call_target__attribute='integer', show=False))
        register_column_factory(ManyToOneRel, None)
        register_column_factory(ManyToManyField, Shortcut(call_target__attribute='many_to_many'))
        register_column_factory(ManyToManyRel, None)

        register_column_factory(ForeignKey, Shortcut(call_target__attribute='foreign_key'))
