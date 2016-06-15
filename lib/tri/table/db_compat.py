from tri.declarative import setdefaults


def setup_db_compat():
    setup_db_compat_django()


def setup_db_compat_django():
    from tri.table import Column, register_column_factory
    try:
        # noinspection PyUnresolvedReferences
        from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, CommaSeparatedIntegerField, DateField, DateTimeField, DecimalField, EmailField, URLField, TimeField, ForeignKey, ManyToOneRel, ManyToManyField, ManyToManyRel
        # from django.db.models.fields.reverse_related import ManyToManyRel as ManyToManyRel_Related
    except ImportError:
        pass
    else:
        # The order here is significant because of inheritance structure. More specific must be below less specific.
        register_column_factory(CharField, lambda model_field, **kwargs: Column(**kwargs))
        register_column_factory(URLField, lambda model_field, **kwargs: Column.url(**kwargs))
        register_column_factory(TimeField, lambda model_field, **kwargs: Column.time(**kwargs))
        register_column_factory(EmailField, lambda model_field, **kwargs: Column.email(**kwargs))
        register_column_factory(DecimalField, lambda model_field, **kwargs: Column.decimal(**kwargs))
        register_column_factory(DateField, lambda model_field, **kwargs: Column.date(**kwargs))
        register_column_factory(DateTimeField, lambda model_field, **kwargs: Column.datetime(**kwargs))
        register_column_factory(CommaSeparatedIntegerField, lambda model_field, **kwargs: Column.comma_separated(parent_field=Column.integer(**kwargs)))
        register_column_factory(BooleanField, lambda model_field, **kwargs: Column.boolean(**kwargs))
        register_column_factory(TextField, lambda model_field, **kwargs: Column.text(**kwargs))
        register_column_factory(FloatField, lambda model_field, **kwargs: Column.float(**kwargs))
        register_column_factory(IntegerField, lambda model_field, **kwargs: Column.integer(**kwargs))
        register_column_factory(AutoField, lambda model_field, **kwargs: Column.integer(**setdefaults(kwargs, dict(show=False))))
        register_column_factory(ManyToOneRel, None)
        register_column_factory(ManyToManyField, lambda model_field, **kwargs: Column.multi_choice_queryset(**setdefaults(kwargs, dict(choices=model_field.rel.to._default_manager.all()))))
        register_column_factory(ManyToManyRel, None)
        # register_field_factory(ManyToManyRel_Related, None)

        def foreign_key_factory(model_field, **kwargs):
            setdefaults(kwargs, dict(
                choices=model_field.foreign_related_fields[0].model.objects.all()
            ))
            kwargs['model'] = model_field.foreign_related_fields[0].model
            return Column.choice_queryset(**kwargs)

        register_column_factory(ForeignKey, foreign_key_factory)
