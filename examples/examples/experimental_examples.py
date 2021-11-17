from django.urls import path

from examples.models import Album
from iommi.experimental.formset_table import FormsetTable

urlpatterns = [
    path(
        '',
        FormsetTable(
            auto__model=Album,
            columns__artist__edit__include=True,
            columns__year__edit__include=True,
        ).as_view(),
    ),
]
