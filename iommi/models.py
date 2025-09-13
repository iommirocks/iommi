from django.db.models import Model

from iommi.model_fields import SortOrderField


class Orderable(Model):
    sort_order = SortOrderField()

    class Meta:
        abstract = True
        ordering = ["sort_order"]
