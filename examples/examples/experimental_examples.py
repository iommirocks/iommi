from django.urls import path

from examples.iommi import (
    EditTable as ExampleEditTable,
)
from examples.iommi import (
    Form as ExampleForm,
)
from examples.models import (
    Album,
    Artist,
    Track,
)
from examples.views import (
    AlbumTable,
    TrackTable,
    album_card_table,
)
from iommi import (
    Action,
    Form,
    PaginatorTrigger,
    Panel,
    html,
)
from iommi.edit_table import (
    EditColumn,
    EditTable,
)
from iommi.form import save_nested_forms


urlpatterns = [
    path(
        'pagination/load-more/',
        TrackTable(
            title='Tracks: Load more',
            page_size=25,
            parts__page__trigger=PaginatorTrigger.LOAD_MORE,
        ).as_view(),
    ),
    path(
        'pagination/infinite-scroll/',
        AlbumTable(
            title='Albums: Infinite scroll',
            page_size=10,
            parts__page__trigger=PaginatorTrigger.INFINITE_SCROLL,
        ).as_view(),
    ),
    path(
        'pagination/hybrid/',
        album_card_table(
            table_class=AlbumTable,
            title='Albums: Load more, then infinite scroll',
            page_size=10,
            parts__page__trigger=PaginatorTrigger.LOAD_MORE_THEN_INFINITE_SCROLL,
        ).as_view(),
    ),
    path(
        'pagination/edit-artist/<int:artist_pk>/',
        ExampleForm(
            title='Edit artist and albums',
            fields=dict(
                artist=ExampleForm.edit(
                    auto__model=Artist,
                    auto__instance=lambda artist_pk, **_: Artist.objects.get(pk=artist_pk),
                    title='Artist',
                ),
                albums=ExampleEditTable.div(
                    title='Albums',
                    auto__model=Album,
                    rows=lambda artist_pk, **_: Album.objects.filter(artist_id=artist_pk),
                    page_size=5,
                    parts__page__trigger=PaginatorTrigger.LOAD_MORE,
                    parts__page__show_page_links=False,
                    edit_actions__add_row__include=False,
                    columns__artist__include=False,
                    columns__name__field__include=True,
                    columns__year__field__include=True,
                    columns__published_date__field__include=True,
                    row__layout=Panel.div(dict(
                        name_row=Panel.row(dict(name=Panel.cell())),
                        details_row=Panel.row(dict(
                            year=Panel.cell(),
                            published_date=Panel.cell(),
                        )),
                        separator=html.hr(),
                    )),
                ),
            ),
            actions__save=Action.primary(post_handler=save_nested_forms),
        ).as_view(),
    ),
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
