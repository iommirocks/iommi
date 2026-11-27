from django.conf import settings
from django.http import HttpResponseRedirect
from django.template import Template
from django.utils.translation import gettext_lazy as _

import iommi.style
from examples.iommi import (
    Action,
    Column,
    Table,
)
from examples.models import (
    Album,
    Artist,
    Track,
)
from iommi import (
    Header,
    Page,
    html,
)
from iommi.base import items
from iommi.experimental.calendar import Calendar
from iommi.form import (
    Field,
    Form,
)
from iommi.style import validate_styles

# Use this function in your code to check that the style is configured correctly. Pass in all stylable classes in your system. For example if you have subclasses for Field, pass these here.
validate_styles()


class StyleSelector(Form):
    class Meta:
        @staticmethod
        def actions__submit__post_handler(request, form, **_):
            style = form.fields.style.value
            settings.IOMMI_DEFAULT_STYLE = style
            return HttpResponseRedirect(request.get_full_path())

        include = getattr(settings, 'IOMMI_REFINE_DONE_OPTIMIZATION', True) is False

    style = Field.choice(
        choices=[k for k, v in items(iommi.style._styles) if not v.internal],
        initial=lambda form, field, **_: getattr(settings, 'IOMMI_DEFAULT_STYLE', iommi.style.DEFAULT_STYLE),
    )


class ExamplesPage(Page):
    pass


# Tables ---------------------------


class TrackTable(Table):
    class Meta:
        auto__rows = Track.objects.all().select_related('album__artist')
        columns__name__filter__include = True


class AlbumTable(Table):
    class Meta:
        auto__model = Album
        page_size = 20

        @staticmethod
        def columns__name__cell__url(row, **_):
            return row.get_absolute_url()

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
        actions__create_album = Action(attrs__href='/albums/create/', display_name=_('Create album'))


def album_card_table(*, table_class=Table, **kwargs):
    return table_class.div(
        auto__model=Album,
        row__template=Template(
            """
            <div class="card" style="width: 15rem; display: inline-block;" {{ cells.attrs }}>
                <img class="card-img-top" src="/static/album_art/{{ row.artist }}/{{ row.name|urlencode }}.jpg">
                <div class="card-body text-center">
                    <h5>{{ cells.name }}</h5>
                    <p class="card-text">
                        {{ cells.artist }}
                    </p>
                    <p class="card-text">{{ cells.year }}</p>
                    {% if cells.edit or cells.delete %}
                        <div>{{ cells.edit }} {{ cells.delete }}</div>
                    {% endif %}
                </div>
            </div>
        """
        ),
        **kwargs,
    )


class ArtistTable(Table):
    class Meta:
        auto__model = Artist

        @staticmethod
        def columns__name__cell__url(row, **_):
            return row.get_absolute_url()

        columns__name__filter__include = True


def black_sabbath_edit_url(**_):
    artist_pk = Artist.objects.filter(name='Black Sabbath').values_list('pk', flat=True).first()
    return f'/experimental/pagination/edit-artist/{artist_pk}/' if artist_pk is not None else '/artists/'


# Pages ----------------------------


class ArtistPage(Page):
    title = html.h1(lambda params, **_: params.artist.name)
    edit_artist_and_albums = html.a(
        'Edit artist and albums with Load more',
        attrs__href=lambda params, **_: f'/experimental/pagination/edit-artist/{params.artist.pk}/',
    )

    albums = AlbumTable(auto__model=Album, rows=lambda params, **_: Album.objects.filter(artist=params.artist))


class AlbumPage(Page):
    title = html.h1(lambda params, **_: params.album)
    text = html.a(
        lambda params, **_: params.album.artist,
        attrs__href=lambda params, **_: params.album.artist.get_absolute_url(),
    )

    tracks = TrackTable(
        auto__model=Track,
        rows=lambda params, **_: Track.objects.filter(album=params.album),
        columns__album__include=False,
    )


def _latest_album_year(**_):
    latest = Album.objects.latest('published_date')
    return latest.published_date.year


def _latest_album_month(**_):
    latest = Album.objects.latest('published_date')
    return latest.published_date.month


class AlbumCalendar(Page):
    title = Header('Album releases')
    calendar = Calendar(
        rows=Album.objects.all(),
        event__attr='published_date',
        event__display_name=lambda event, **_: event.name,
        year=_latest_album_year,
        month=_latest_album_month,
    )


class IndexPage(ExamplesPage):
    logo = html.img(
        attrs__src='https://docs.iommi.rocks/_static/logo_with_outline.svg',
        attrs__style__width='10%',
    )
    header = Header('Welcome to the iommi examples application')
    docs_link = html.a('iommi docs', attrs__href='https://docs.iommi.rocks/')
    style_selector = StyleSelector()
    pagination_header = Header('Incremental pagination examples')
    load_more_link = html.a('Load more: tracks', attrs__href='/experimental/pagination/load-more/')
    infinite_scroll_link = html.a('Infinite scroll: albums', attrs__href='/experimental/pagination/infinite-scroll/')
    hybrid_link = html.a('Load more, then infinite scroll: albums', attrs__href='/experimental/pagination/hybrid/')

    albums = album_card_table()
