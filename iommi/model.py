from django.core.exceptions import FieldDoesNotExist
from django.db.models import Model


class IommiModel(Model):
    class Meta:
        abstract = True

    def __setattr__(self, name, value):
        if not name.startswith('_') and name != 'pk':
            try:
                field = self._meta.get_field(name)

                if getattr(field, 'primary_key', False):
                    return object.__setattr__(self, name, value)

            except FieldDoesNotExist as e:
                if name not in self.get_annotated_attributes():
                    raise TypeError(f'There is no field {name} on the model {self.__class__.__name__}. You can assign arbitrary attributes if they start with `_`. If this is an annotation, please add a method `get_annotated_attributes` that returns a list of valid annotated attributes that should not trigger this message.') from e

            self.get_updated_fields().add(name)

        return object.__setattr__(self, name, value)

    def get_updated_fields(self):
        return self.__dict__.setdefault('_updated_fields', set())

    def get_annotated_attributes(self):
        return ()

    @classmethod
    def from_db(cls, db, field_names, values):
        result = super().from_db(db, field_names, values)
        result.get_updated_fields().clear()
        return result

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.pk is not None and not force_insert:
            update_fields = self.get_updated_fields()

        super(IommiModel, self).save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields
        )

        self.get_updated_fields().clear()

    def __repr__(self):
        return f'<{self.__class__.__name__} pk={self.pk}>'
