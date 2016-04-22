from collections import OrderedDict

from tri.declarative import setdefaults

_variable_factory_by_django_field_type = None


def setup():
    from tri.query import Variable
    from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, CommaSeparatedIntegerField, DateField, DateTimeField, DecimalField, EmailField, URLField, TimeField, ForeignKey, ManyToOneRel, ManyToManyField, ManyToManyRel

    def foreign_key_factory(model_field, **kwargs):
        setdefaults(kwargs, dict(
            choices=model_field.foreign_related_fields[0].model.objects.all()
        ))
        kwargs['model'] = model_field.foreign_related_fields[0].model
        return Variable.choice_queryset(**kwargs)

    # The order here is significant because of inheritance structure. More specific must be below less specific.
    global _variable_factory_by_django_field_type
    _variable_factory_by_django_field_type = OrderedDict([
        (CharField, lambda model_field, **kwargs: Variable(**kwargs)),
        (URLField, lambda model_field, **kwargs: Variable.url(**kwargs)),
        (TimeField, lambda model_field, **kwargs: Variable.time(**kwargs)),
        (EmailField, lambda model_field, **kwargs: Variable.email(**kwargs)),
        (DecimalField, lambda model_field, **kwargs: Variable.decimal(**kwargs)),
        (DateField, lambda model_field, **kwargs: Variable.date(**kwargs)),
        (DateTimeField, lambda model_field, **kwargs: Variable.datetime(**kwargs)),
        (CommaSeparatedIntegerField, lambda model_field, **kwargs: Variable.comma_separated(parent_field=Variable.integer(**kwargs))),
        (BooleanField, lambda model_field, **kwargs: Variable.boolean(**kwargs)),
        (TextField, lambda model_field, **kwargs: Variable.text(**kwargs)),
        (FloatField, lambda model_field, **kwargs: Variable.float(**kwargs)),
        (IntegerField, lambda model_field, **kwargs: Variable.integer(**kwargs)),
        (AutoField, lambda model_field, **kwargs: Variable.integer(**setdefaults(kwargs, dict(show=False)))),
        (ManyToOneRel, None),
        (ManyToManyField, lambda model_field, **kwargs: Variable.multi_choice_queryset(**setdefaults(kwargs, dict(choices=model_field.rel.to._default_manager.all())))),
        (ManyToManyRel, None),
        # (ManyToManyRel_Related, None),
        (ForeignKey, foreign_key_factory),
    ])


def register_field_factory(field_class, factory):
    _variable_factory_by_django_field_type[field_class] = factory

setup()
