from django.shortcuts import redirect
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
from iommi.experimental.edit_table import (
    EditColumn,
    EditTable,
)


def save_nested_forms(form, request, **_):
    did_fail = False
    for nested_form in form.nested_forms.values():
        for action in nested_form.actions.values():
            if action.post_handler is None:
                continue
            if action.post_handler and action.post_handler(**action.iommi_evaluate_parameters()) is None:
                did_fail = True

    if not did_fail:
        if 'post_save' in form.extra:
            form.extra.post_save(**form.iommi_evaluate_parameters())

        request.method = 'GET'

        return redirect(request.POST.get('next', '.'))


urlpatterns = [
    path(
        '',
        EditTable(
            auto__model=Album,
            page_size=5,
            columns__artist__edit__include=True,
            columns__year__edit__include=True,
            columns__delete=EditColumn.delete(),
        ).as_view(),
    ),
    path(
        'nested/',
        Form(
            fields=dict(
                edit_album=Form.edit(auto__model=Track, instance=lambda **_: Track.objects.get(album__artist__name='Black Sabbath', name='Supernaut'), fields__name__include=False),
                edit_table=EditTable(
                    auto__model=Album,
                    page_size=3,
                    columns__artist__edit__include=True,
                    columns__year__edit__include=True,
                    columns__delete=EditColumn.delete(),
                ),
                edit_table2=EditTable(
                    auto__model=Artist,
                    page_size=3,
                    columns__name__edit__include=True,
                    columns__delete=EditColumn.delete(),
                ),
            ),
            actions__save=Action.primary(post_handler=save_nested_forms),
        ).as_view(),
    ),
]
