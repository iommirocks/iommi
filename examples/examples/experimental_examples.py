from django.urls import path

from examples.models import (
    Album,
    Artist,
    Track,
)
from iommi import (
    Action,
    Form,
)
from iommi.edit_table import (
    EditColumn,
    EditTable,
)
from iommi.form import save_nested_forms

urlpatterns = [
    path(
        '',
        EditTable(
            auto__model=Album,
            page_size=5,
            columns__artist__field__include=True,
            columns__year__field__include=False,
            columns__delete=EditColumn.delete(),
        ).as_view(),
    ),
    path(
        'nested/',
        Form(
            fields=dict(
                edit_album=Form.edit(
                    auto__model=Track,
                    instance=lambda **_: Track.objects.first(),
                    fields__name__include=False,
                ),
                edit_table=EditTable(
                    auto__model=Album,
                    page_size=3,
                    columns__artist__field__include=True,
                    columns__year__field__include=True,
                    columns__delete=EditColumn.delete(),
                ),
                edit_table2=EditTable(
                    auto__model=Artist,
                    page_size=3,
                    columns__name__field__include=True,
                    columns__delete=EditColumn.delete(),
                ),
            ),
            actions__save=Action.primary(
                post_handler=save_nested_forms,
            ),
        ).as_view(),
    ),
]
