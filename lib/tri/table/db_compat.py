from tri.declarative import setdefaults_path


def setup_db_compat():
    setup_db_compat_django()


def setup_db_compat_django():
    def many_to_many_factory(model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.related_model.objects.all(),
            model=model_field.related_model,
        )
        return Column.multi_choice_queryset(model_field=model_field, **kwargs)

    def auto_field_factory(**kwargs):
        setdefaults_path(
            kwargs,
            show=False,
        )
        return Column.integer(**kwargs)

    def comma_separated_integer_factory(**kwargs):
        setdefaults_path(
            kwargs,
            show=False,
        )
        return Column.comma_separated(parent_field=Column.integer(**kwargs))

    from tri.table import Column, register_column_factory
    try:
        # noinspection PyUnresolvedReferences
        from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, CommaSeparatedIntegerField, DateField, DateTimeField, DecimalField, EmailField, TimeField, ForeignKey, ManyToOneRel, ManyToManyField, ManyToManyRel
        # from django.db.models.fields.reverse_related import ManyToManyRel as ManyToManyRel_Related
    except ImportError:
        pass
    else:
        # The order here is significant because of inheritance structure. More specific must be below less specific.
        register_column_factory(CharField, Column)
        register_column_factory(TimeField, Column.time)
        register_column_factory(EmailField, Column.email)
        register_column_factory(DecimalField, Column.decimal)
        register_column_factory(DateField, Column.date)
        register_column_factory(DateTimeField, Column.datetime)
        register_column_factory(BooleanField, Column.boolean)
        register_column_factory(TextField, Column.text)
        register_column_factory(FloatField, Column.float)
        register_column_factory(IntegerField, Column.integer)

        register_column_factory(CommaSeparatedIntegerField, comma_separated_integer_factory)
        register_column_factory(AutoField, auto_field_factory)
        register_column_factory(ManyToOneRel, None)
        register_column_factory(ManyToManyField, many_to_many_factory)
        register_column_factory(ManyToManyRel, None)
        # register_field_factory(ManyToManyRel_Related, None)

        def foreign_key_factory(model_field, **kwargs):
            setdefaults_path(
                kwargs,
                choices=model_field.foreign_related_fields[0].model.objects.all(),
                model=model_field.foreign_related_fields[0].model,
            )
            return Column.choice_queryset(model_field=model_field, **kwargs)

        register_column_factory(ForeignKey, foreign_key_factory)
