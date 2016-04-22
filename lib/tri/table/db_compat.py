from collections import OrderedDict

from tri.declarative import setdefaults

_column_factory_by_django_field_type = None


def setup():
    from tri.table import Column
    from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, CommaSeparatedIntegerField, DateField, DateTimeField, DecimalField, EmailField, URLField, TimeField, ForeignKey, ManyToOneRel, ManyToManyField, ManyToManyRel
    # from django.db.models.fields.reverse_related import ManyToManyRel as ManyToManyRel_Related

    def foreign_key_factory(model_field, **kwargs):
        setdefaults(kwargs, dict(
            choices=model_field.foreign_related_fields[0].model.objects.all()
        ))
        kwargs['model'] = model_field.foreign_related_fields[0].model
        return Column.choice_queryset(**kwargs)

    # The order here is significant because of inheritance structure. More specific must be below less specific.
    global _column_factory_by_django_field_type
    _column_factory_by_django_field_type = OrderedDict([
        (CharField, lambda model_field, **kwargs: Column(**kwargs)),
        (URLField, lambda model_field, **kwargs: Column.url(**kwargs)),
        (TimeField, lambda model_field, **kwargs: Column.time(**kwargs)),
        (EmailField, lambda model_field, **kwargs: Column.email(**kwargs)),
        (DecimalField, lambda model_field, **kwargs: Column.decimal(**kwargs)),
        (DateField, lambda model_field, **kwargs: Column.date(**kwargs)),
        (DateTimeField, lambda model_field, **kwargs: Column.datetime(**kwargs)),
        (CommaSeparatedIntegerField, lambda model_field, **kwargs: Column.comma_separated(parent_field=Column.integer(**kwargs))),
        (BooleanField, lambda model_field, **kwargs: Column.boolean(**kwargs)),
        (TextField, lambda model_field, **kwargs: Column.text(**kwargs)),
        (FloatField, lambda model_field, **kwargs: Column.float(**kwargs)),
        (IntegerField, lambda model_field, **kwargs: Column.integer(**kwargs)),
        (AutoField, lambda model_field, **kwargs: Column.integer(**setdefaults(kwargs, dict(show=False)))),
        (ManyToOneRel, None),
        (ManyToManyField, lambda model_field, **kwargs: Column.multi_choice_queryset(**setdefaults(kwargs, dict(choices=model_field.rel.to._default_manager.all())))),
        (ManyToManyRel, None),
        # (ManyToManyRel_Related, None),
        (ForeignKey, foreign_key_factory),
    ])


def register_field_factory(field_class, factory):
    _column_factory_by_django_field_type[field_class] = factory


setup()
