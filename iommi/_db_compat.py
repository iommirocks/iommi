from tri_declarative import Shortcut

from iommi.base import MISSING


def setup_db_compat():
    setup_db_compat_django()


def register_factory(django_field_class, *, shortcut_name=MISSING, factory=MISSING):
    from iommi.form import register_field_factory
    from iommi.query import register_filter_factory
    from iommi.table import register_column_factory

    register_field_factory(django_field_class, shortcut_name=shortcut_name, factory=factory)
    register_filter_factory(django_field_class, shortcut_name=shortcut_name, factory=factory)
    register_column_factory(django_field_class, shortcut_name=shortcut_name, factory=factory)


def setup_db_compat_django():
    from iommi.form import register_field_factory
    from iommi.query import register_filter_factory
    from iommi.table import register_column_factory

    from django.db.models import (
        AutoField,
        BinaryField,
        BooleanField,
        CharField,
        DateField,
        DateTimeField,
        DecimalField,
        EmailField,
        FileField,
        FilePathField,
        FloatField,
        ForeignKey,
        GenericIPAddressField,
        ImageField,
        IntegerField,
        ManyToManyField,
        ManyToManyRel,
        ManyToOneRel,
        TextField,
        TimeField,
        URLField,
        UUIDField,
    )

    def char_field_factory(model_field, **_):
        if not model_field.choices:
            return Shortcut(call_target__attribute='text')

        return Shortcut(
            call_target__attribute='choice',
            choices=[x[0] for x in model_field.choices],
        )

    def field_char_field_factory(model_field, **_):
        if not model_field.choices:
            return Shortcut(call_target__attribute='text')

        display_name_by_choice = dict(model_field.choices)

        return Shortcut(
            call_target__attribute='choice',
            choices=[x[0] for x in model_field.choices],
            choice_display_name_formatter=lambda choice, **_: display_name_by_choice[choice],
        )

    # The order here is significant because of inheritance structure. More specific must be below less specific.
    register_factory(CharField, factory=char_field_factory)
    register_field_factory(CharField, factory=field_char_field_factory)  # the field is special, overwrite that here

    register_factory(UUIDField, shortcut_name='text')
    register_factory(TimeField, shortcut_name='time')
    register_factory(EmailField, shortcut_name='email')
    register_factory(DecimalField, shortcut_name='decimal')
    register_factory(DateField, shortcut_name='date')
    register_factory(DateTimeField, shortcut_name='datetime')
    register_factory(FloatField, shortcut_name='float')
    register_factory(IntegerField, shortcut_name='integer')
    register_factory(FileField, shortcut_name='file')
    register_factory(AutoField, factory=Shortcut(call_target__attribute='integer', include=False))
    register_factory(ManyToOneRel, factory=None)
    register_factory(ManyToManyRel, factory=None)
    register_factory(ManyToManyField, shortcut_name='many_to_many')
    register_factory(ForeignKey, shortcut_name='foreign_key')
    register_factory(GenericIPAddressField, shortcut_name='text')
    register_factory(FilePathField, shortcut_name='text')
    register_factory(BinaryField, factory=None)
    try:
        # This raises ImportError when the postgres driver isn't installed
        from django.contrib.postgres.fields import JSONField
        register_factory(JSONField, factory=None)
    except ImportError:
        pass

    # Column specific
    register_column_factory(BooleanField, shortcut_name='boolean')
    register_column_factory(TextField, shortcut_name='text')

    # Filter specific
    register_filter_factory(URLField, shortcut_name='url')
    register_filter_factory(BooleanField, shortcut_name='boolean')
    register_filter_factory(TextField, shortcut_name='text')

    # Field specific
    register_field_factory(ImageField, shortcut_name='image')
    register_field_factory(URLField, shortcut_name='url')
    register_field_factory(
        BooleanField,
        factory=lambda model_field, **kwargs: (
            Shortcut(call_target__attribute='boolean')
            if not model_field.null
            else Shortcut(call_target__attribute='boolean_tristate')
        ),
    )
    register_field_factory(TextField, shortcut_name='textarea')
    register_field_factory(FileField, shortcut_name='file')


def base_defaults_factory(model_field):
    from iommi.base import capitalize

    r = {}
    if hasattr(model_field, 'verbose_name'):
        r['display_name'] = capitalize(model_field.verbose_name)

    return r


# TODO: move to form.py! remember to take the tests with them
def field_defaults_factory(model_field):
    from django.db.models import BooleanField

    r = base_defaults_factory(model_field)

    if hasattr(model_field, 'null') and not isinstance(model_field, BooleanField):
        r['required'] = not model_field.null and not model_field.blank

    if hasattr(model_field, 'null'):
        r['parse_empty_string_as_none'] = model_field.null

    return r
