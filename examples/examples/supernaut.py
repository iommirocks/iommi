from django.shortcuts import get_object_or_404
from django.template import Template
from django.urls import (
    path,
)
from django.utils.translation import gettext as _

from iommi import (
    Action,
    Column,
    Form,
    html,
    Menu,
    MenuItem,
    Page,
    Table,
)
from iommi.path import (
    Decoder,
    register_advanced_path_decoding,
    register_path_decoding,
)

from .models import (
    Album,
    Artist,
    Track,
)

# Registrations --------------------

register_path_decoding(Artist)
register_advanced_path_decoding({
    Album: Decoder('name', decode=lambda model, string, decoded_kwargs, **_: model.objects.get(name=string, artist=decoded_kwargs['artist'])),
})


# Menu -----------------------------


class SupernautMenu(Menu):
    home = MenuItem(url='/supernaut/', display_name=_('Home'))
    artists = MenuItem(url='/supernaut/artists/', display_name=_('Artists'))
    albums = MenuItem(url='/supernaut/albums/', display_name=_('Albums'))
    tracks = MenuItem(url='/supernaut/tracks/', display_name=_('Tracks'))

    class Meta:
        attrs__class = {'fixed-top': True}


# Tables ---------------------------


class TrackTable(Table):
    class Meta:
        auto__rows = Track.objects.all().select_related('album__artist')
        columns__name__filter__include = True


class AlbumTable(Table):
    class Meta:
        auto__model = Album
        page_size = 20
        columns__name__cell__url = lambda row, **_: row.get_absolute_url()
        columns__name__filter__include = True
        columns__year__filter__include = True
        columns__year__filter__field__include = False
        columns__artist__filter__include = True
        columns__edit = Column.edit(
            include=lambda request, **_: request.user.is_staff,
        )
        columns__delete = Column.delete(
            include=lambda request, **_: request.user.is_staff,
        )
        actions__create_album = Action(attrs__href='/supernaut/albums/create/', display_name=_('Create album'))


class ArtistTable(Table):
    class Meta:
        auto__model = Artist
        columns__name__cell__url = lambda row, **_: row.get_absolute_url()
        columns__name__filter__include = True


# Pages ----------------------------


class IndexPage(Page):
    menu = SupernautMenu()

    title = html.h1(_('Supernaut'))
    welcome_text = html.div(_('This is a discography of the best acts in music!'))

    albums = AlbumTable(
        auto__model=Album,
        tag='div',
        header__template=None,
        cell__tag=None,
        row__template=Template(
            """
            <div class="card" style="width: 15rem; display: inline-block;" {{ cells.attrs }}>
                <img class="card-img-top" src="/static/album_art/{{ row.artist }}/{{ row.name|urlencode }}.jpg">
                <div class="card-body text-center">
                    <h5>{{ cells.name }}</h5>
                    <p class="card-text">
                        {{ cells.artist }}
                    </p>
                </div>
            </div>
        """
        ),
    )


class ArtistPage(Page):
    title = html.h1(lambda params, **_: params.artist.name)

    albums = AlbumTable(auto__model=Album, rows=lambda params, **_: Album.objects.filter(artist=params.artist))
    tracks = TrackTable(auto__model=Track, rows=lambda params, **_: Track.objects.filter(album__artist=params.artist))


class AlbumPage(Page):
    title = html.h1(lambda params, **_: params.album)
    text = html.a(lambda params, **_: params.album.artist, attrs__href=lambda params, **_: params.album.artist.get_absolute_url())

    tracks = TrackTable(
        auto__model=Track,
        rows=lambda params, **_: Track.objects.filter(album=params.album),
        columns__album__include=False,
    )


# URLs -----------------------------

urlpatterns = [
    path('', IndexPage().as_view()),
    path('albums/', AlbumTable(auto__model=Album, columns__year__bulk__include=True).as_view()),
    path('albums/create/', Form.create(auto__model=Album).as_view()),
    path('artists/', ArtistTable(auto__model=Artist).as_view()),
    path('tracks/', TrackTable(auto__model=Track).as_view()),
    path('artist/<artist_name>/', ArtistPage().as_view()),
    path('artist/<artist_name>/<album_name>/', AlbumPage().as_view()),
    path('artist/<artist_name>/<album_name>/edit/', Form.edit(auto__model=Album, instance=lambda params, **_: params.album).as_view()),
    path('artist/<artist_name>/<album_name>/delete/', Form.delete(auto__model=Album, instance=lambda params, **_: params.album).as_view()),
]
