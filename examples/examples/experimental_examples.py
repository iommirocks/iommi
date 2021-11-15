from django.urls import path
from tri_declarative import Refinable

from examples.models import (
    Album,
)
from iommi import (
    Column,
    Field,
    Form,
    Table,
)
from iommi.base import items


class TableField(Field):
    column = Refinable()

    class Meta:
        editable = False


class TableForm(Form):
    table = Refinable()

    class Meta:
        member_class = TableField
        table__call_target = Table

    def on_refine_done(self):
        super(TableForm, self).on_refine_done()

        columns = {}

        for k, v in items(self.fields):
            columns[k] = dict(
                attr=v.attr,
            )

        self.table = self.table(
            auto=self.auto,
            columns=columns,
        ).refine_done()


urlpatterns = [
    path(
        '',
        TableForm(
            auto__model=Album,
            fields__artist__editable=True,
        ).as_view(),
    ),
]
