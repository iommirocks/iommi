from tri_declarative import Shortcut


def setup_db_compat():
    from iommi.form import register_field_factory
    from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, \
        DateField, DateTimeField, DecimalField, EmailField, URLField, TimeField, \
        ForeignKey, ManyToManyField, FileField, ManyToOneRel, ManyToManyRel, UUIDField

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
