from tri.declarative import setdefaults_path

from tri.query import register_variable_factory


def setup_db_compat():
    setup_db_compat_django()


def setup_db_compat_django():
    from tri.query import Variable
    from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, CommaSeparatedIntegerField, DateField, DateTimeField, DecimalField, EmailField, URLField, TimeField, ForeignKey, ManyToOneRel, ManyToManyField, ManyToManyRel

    def foreign_key_factory(model_field, **kwargs):
        setdefaults_path(kwargs, dict(
            choices=model_field.foreign_related_fields[0].model.objects.all()
        ))
        return Variable.choice_queryset(**kwargs)

    # The order here is significant because of inheritance structure. More specific must be below less specific.
    register_variable_factory(CharField, Variable),
    register_variable_factory(URLField, Variable.url),
    register_variable_factory(TimeField, Variable.time),
    register_variable_factory(EmailField, Variable.email),
    register_variable_factory(DecimalField, Variable.decimal),
    register_variable_factory(DateField, Variable.date),
    register_variable_factory(DateTimeField, Variable.datetime),
    register_variable_factory(BooleanField, Variable.boolean),
    register_variable_factory(TextField, Variable.text),
    register_variable_factory(FloatField, Variable.float),
    register_variable_factory(IntegerField, Variable.integer),

    register_variable_factory(CommaSeparatedIntegerField, lambda **kwargs: Variable.comma_separated(parent_field=Variable.integer(**kwargs))),
    register_variable_factory(AutoField, lambda **kwargs: Variable.integer(**setdefaults_path(kwargs, dict(show=False)))),
    register_variable_factory(ManyToManyField, lambda model_field, **kwargs: Variable.multi_choice_queryset(model_field=model_field, **setdefaults_path(kwargs, dict(choices=model_field.rel.to._default_manager.all())))),

    register_variable_factory(ManyToOneRel, None),
    register_variable_factory(ManyToManyRel, None),
    # (ManyToManyRel_Related, None),
    register_variable_factory(ForeignKey, foreign_key_factory),
