from django.db.models import PositiveIntegerField
from django import VERSION as DJANGO_VERSION


class SortOrderField(PositiveIntegerField):
    def __init__(self, **kwargs):
        kwargs.setdefault("null", False)
        kwargs.setdefault("blank", False)
        if DJANGO_VERSION[0] >= 5:
            kwargs.setdefault("db_default", 0)
        kwargs.setdefault("db_index", True)
        kwargs.setdefault("default", 0)
        kwargs.setdefault("editable", False)
        super().__init__(**kwargs)
