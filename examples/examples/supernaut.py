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
from .models import (
    Album,
    Artist,
    Track,
)


# Menu -----------------------------


class SupernautMenu(Menu):
    home = MenuItem(url='/', display_name=_('Home'))
    artists = MenuItem(display_name=_('Artists'))
    albums = MenuItem(display_name=_('Albums'))
    tracks = MenuItem(display_name=_('Tracks'))

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


def artist_page(request, artist):
    artist = get_object_or_404(Artist, name=artist)

    class ArtistPage(Page):
        title = html.h1(artist.name)

        albums = AlbumTable(auto__rows=Album.objects.filter(artist=artist))
        tracks = TrackTable(auto__rows=Track.objects.filter(album__artist=artist))

    return ArtistPage()


def album_page(request, artist, album):
    album = get_object_or_404(Album, name=album, artist__name=artist)

    class AlbumPage(Page):
        title = html.h1(album)
        text = html.a(album.artist, attrs__href=album.artist.get_absolute_url())

        tracks = TrackTable(
            auto__rows=Track.objects.filter(album=album),
            columns__album__include=False,
        )

    return AlbumPage()


def edit_album(request, artist, album):
    album = get_object_or_404(Album, name=album, artist__name=artist)
    return Form.edit(auto__instance=album)


def delete_album(request, artist, album):
    album = get_object_or_404(Album, name=album, artist__name=artist)
    return Form.delete(auto__instance=album)


# URLs -----------------------------

urlpatterns = [
    path('', IndexPage().as_view()),
    path('albums/', AlbumTable(auto__model=Album, columns__year__bulk__include=True).as_view()),
    path('albums/create/', Form.create(auto__model=Album).as_view()),
    path('artists/', ArtistTable(auto__model=Artist).as_view()),
    path('tracks/', TrackTable(auto__model=Track).as_view()),
    path('artist/<artist>/', artist_page),
    path('artist/<artist>/<album>/', album_page),
    path('artist/<artist>/<album>/edit/', edit_album),
    path('artist/<artist>/<album>/delete/', delete_album),
]
