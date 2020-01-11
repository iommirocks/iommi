from tri_declarative import Shortcut


def setup_db_compat():
    setup_db_compat_django()


def setup_db_compat_django():
    from iommi.form import register_field_factory
    from iommi.query import register_variable_factory
    from iommi.table import register_column_factory

    from django.db.models import (
        AutoField,
        BooleanField,
        CharField,
        DateField,
        DateTimeField,
        DecimalField,
        EmailField,
        FileField,
        FloatField,
        ForeignKey,
        IntegerField,
        ManyToManyField,
        ManyToManyRel,
        ManyToOneRel,
        TextField,
        TimeField,
        URLField,
        UUIDField,
    )

    # The order here is significant because of inheritance structure. More specific must be below less specific.
    register_column_factory(CharField, Shortcut(call_target__attribute='text'))
    register_column_factory(UUIDField, Shortcut(call_target__attribute='text'))
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

    # The order here is significant because of inheritance structure. More specific must be below less specific.
    register_field_factory(CharField, Shortcut())
    register_field_factory(UUIDField, Shortcut())
    register_field_factory(URLField, Shortcut(call_target__attribute='url'))
    register_field_factory(TimeField, Shortcut(call_target__attribute='time'))
    register_field_factory(EmailField, Shortcut(call_target__attribute='email'))
    register_field_factory(DecimalField, Shortcut(call_target__attribute='decimal'))
    register_field_factory(DateField, Shortcut(call_target__attribute='date'))
    register_field_factory(DateTimeField, Shortcut(call_target__attribute='datetime'))
    register_field_factory(
        BooleanField,
        lambda model_field, **kwargs: (
            Shortcut(call_target__attribute='boolean')
            if not model_field.null
            else Shortcut(call_target__attribute='boolean_tristate')
        )
    )
    register_field_factory(TextField, Shortcut(call_target__attribute='textarea'))
    register_field_factory(FloatField, Shortcut(call_target__attribute='float'))
    register_field_factory(IntegerField, Shortcut(call_target__attribute='integer'))
    register_field_factory(AutoField, Shortcut(call_target__attribute='integer', show=False))
    register_field_factory(ManyToOneRel, None)
    register_field_factory(ManyToManyRel, None)
    register_field_factory(FileField, Shortcut(call_target__attribute='file'))
    register_field_factory(ForeignKey, Shortcut(call_target__attribute='foreign_key'))
    register_field_factory(ManyToManyField, Shortcut(call_target__attribute='many_to_many'))


def field_defaults_factory(model_field):
    from iommi.form import capitalize
    from django.db.models import BooleanField
    r = {}
    if hasattr(model_field, 'verbose_name'):
        r['display_name'] = capitalize(model_field.verbose_name)

    if hasattr(model_field, 'null') and not isinstance(model_field, BooleanField):
        r['required'] = not model_field.null and not model_field.blank

    if hasattr(model_field, 'null'):
        r['parse_empty_string_as_none'] = model_field.null

    return r
