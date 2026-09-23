"""
The benchmark workload: a handful of representative pages, and the requests we make to them.

Pages that are declared once and served with `.as_view()` only pay for bind and render per
request. The dashboard is instead instantiated inside a function based view, so it also pays for
construction and refine_done on every request, which is the other common way to use iommi.
"""

from collections.abc import Callable
from dataclasses import (
    dataclass,
    field,
)
from datetime import date
from decimal import Decimal

from bs4 import BeautifulSoup
from django.apps import apps
from django.contrib.auth.models import User
from django.db import connection
from django.db.models import Count
from django.test import RequestFactory

from benchmarks.models import (
    Album,
    Artist,
    Genre,
    Track,
)
from iommi import (
    Action,
    Column,
    EditColumn,
    EditTable,
    Field,
    Form,
    Header,
    Page,
    Table,
    html,
    iommi_render,
    register_search_fields,
)
from iommi.menu import (
    Menu,
    MenuItem,
)


@dataclass
class Scenario:
    name: str
    description: str
    view: Callable
    build_request: Callable
    expected_status: int = 200
    expected_text: list[str] = field(default_factory=list)


# --- Data -------------------------------------------------------------------------------------

GENRES = [
    'Blues',
    'Doom',
    'Folk',
    'Heavy metal',
    'Jazz',
    'Progressive',
    'Psychedelic',
    'Punk',
    'Rock',
    'Soul',
    'Stoner',
    'Thrash',
]
NUMBER_OF_ARTISTS = 30
ALBUMS_PER_ARTIST = 10
TRACKS_PER_ALBUM = 10

EDITED_ALBUM = 'Album 007'
EDIT_TABLE_ALBUMS = ['Album 010', 'Album 011', 'Album 012', 'Album 013']


def setup_database():
    with connection.schema_editor() as editor:
        for model in apps.get_models():
            if model._meta.managed and not model._meta.proxy:
                editor.create_model(model)

    genres = Genre.objects.bulk_create([Genre(name=name) for name in GENRES])
    artists = Artist.objects.bulk_create(
        [
            Artist(
                name=f'Artist {i:02}',
                country=Artist.COUNTRIES[i % len(Artist.COUNTRIES)][0],
                formed=1960 + i,
                active=i % 3 != 0,
            )
            for i in range(NUMBER_OF_ARTISTS)
        ]
    )
    albums = Album.objects.bulk_create(
        [
            Album(
                name=f'Album {i:03}',
                artist=artists[i // ALBUMS_PER_ARTIST],
                year=1965 + i * 7 % 55,
                published_date=date(1965 + i * 7 % 55, 1 + i % 12, 1 + i % 28),
                rating=Decimal(i * 13 % 50) / 10,
                explicit=i % 5 == 0,
                notes='Remastered edition.' if i % 4 == 0 else '',
            )
            for i in range(NUMBER_OF_ARTISTS * ALBUMS_PER_ARTIST)
        ]
    )
    Album.genres.through.objects.bulk_create(
        [
            Album.genres.through(album=album, genre=genre)
            for i, album in enumerate(albums)
            for genre in {genres[i % len(genres)], genres[(i * 5 + 3) % len(genres)]}
        ]
    )
    Track.objects.bulk_create(
        [
            Track(
                name=f'Track {i:03}-{j:02}',
                index=j + 1,
                album=album,
                duration=120 + (i * TRACKS_PER_ALBUM + j) * 37 % 300,
                plays=(i * TRACKS_PER_ALBUM + j) * 7919 % 100_000,
            )
            for i, album in enumerate(albums)
            for j in range(TRACKS_PER_ALBUM)
        ]
    )


@dataclass
class ReportRow:
    pk: int
    name: str
    artist: str
    album: str
    year: int
    released: date
    duration: int
    plays: int
    explicit: bool


REPORT_ROWS = [
    ReportRow(
        pk=i,
        name=f'Track {i:03}',
        artist=f'Artist {i % NUMBER_OF_ARTISTS:02}',
        album=f'Album {i // TRACKS_PER_ALBUM:03}',
        year=1965 + i * 7 % 55,
        released=date(1965 + i * 7 % 55, 1 + i % 12, 1 + i % 28),
        duration=120 + i * 37 % 300,
        plays=i * 7919 % 100_000,
        explicit=i % 5 == 0,
    )
    for i in range(150)
]


# --- Pages ------------------------------------------------------------------------------------

register_search_fields(model=Track, search_fields=['name'], allow_non_unique=True)

# Album list: the typical "admin changelist" style page.
album_list = Table(
    auto__model=Album,
    auto__exclude=['notes'],
    rows=lambda **_: Album.objects.select_related('artist').prefetch_related('genres'),
    columns__name__cell__url=lambda row, **_: row.get_absolute_url(),
    columns__name__filter__include=True,
    columns__name__filter__freetext=True,
    columns__artist__filter__include=True,
    columns__year__filter__include=True,
    columns__explicit__filter__include=True,
    columns__year__bulk__include=True,
    columns__explicit__bulk__include=True,
    columns__edit=Column.edit(),
    columns__delete=Column.delete(),
    actions__create_album=Action(attrs__href='/albums/create/', display_name='Create album'),
)
album_list_view = album_list.as_view()

album_create_view = Form.create(auto__model=Album).as_view()

album_edit_view = Form.edit(
    auto__model=Album,
    instance=lambda **_: Album.objects.get(name=EDITED_ALBUM),
).as_view()

tracks_edit_table_view = EditTable(
    auto__model=Track,
    rows=lambda **_: Track.objects.filter(album__name__in=EDIT_TABLE_ALBUMS).select_related('album'),
    columns__name__field__include=True,
    columns__index__field__include=True,
    columns__duration__field__include=True,
    columns__plays__field__include=True,
    columns__delete=EditColumn.delete(),
    page_size=40,
).as_view()

# Report: a bigger table of plain python objects, no database involved.
report_view = Table(
    rows=REPORT_ROWS,
    columns=dict(
        name=Column(cell__url=lambda row, **_: f'/tracks/{row.pk}/'),
        artist=Column(),
        album=Column(),
        year=Column.number(),
        released=Column.date(),
        duration=Column(cell__format=lambda value, **_: f'{value // 60}:{value % 60:02}'),
        plays=Column.number(),
        explicit=Column.boolean(),
    ),
    page_size=len(REPORT_ROWS),
).as_view()


class DashboardPage(Page):
    menu = Menu(
        sub_menu=dict(
            albums=MenuItem(url='/albums/'),
            artists=MenuItem(url='/artists/'),
            genres=MenuItem(url='/genres/'),
            tracks=MenuItem(url='/tracks/'),
        ),
    )
    header = Header('Dashboard')
    intro = html.p('Latest releases, and the artists with the most albums.')
    search = Form(
        title='Search',
        fields=dict(
            q=Field(display_name='Search'),
            genre=Field.choice_queryset(choices=Genre.objects.all()),
            country=Field.choice(choices=[code for code, _ in Artist.COUNTRIES]),
            released_after=Field.date(),
            explicit=Field.boolean(),
        ),
        actions__submit__display_name='Search',
    )
    latest = Table(
        title='Latest releases',
        auto__model=Album,
        auto__include=['name', 'artist', 'year', 'published_date', 'rating'],
        rows=lambda **_: Album.objects.select_related('artist').order_by('-published_date'),
        page_size=10,
    )
    artists = Table(
        title='Artists',
        auto__model=Artist,
        rows=lambda **_: Artist.objects.annotate(album_count=Count('albums')).order_by('-album_count', 'name'),
        columns__name__cell__url=lambda row, **_: row.get_absolute_url(),
        columns__album_count=Column.number(),
        page_size=10,
    )


@iommi_render
def dashboard_view(request):
    return DashboardPage()


# --- Requests ---------------------------------------------------------------------------------

request_factory = RequestFactory()
user = User(username='benchmark', is_staff=True, is_superuser=True)


def get(path, data=None):
    def build_request():
        request = request_factory.get(path, data or {})
        request.user = user
        return request

    return build_request


def post(path, data):
    def build_request():
        request = request_factory.post(path, data)
        request.user = user
        return request

    return build_request


def form_data_from_html(content, submit_name):
    """What a browser would post when clicking the button named `submit_name`."""
    soup = BeautifulSoup(content, 'html.parser')
    form = soup.find(attrs={'name': submit_name}).find_parent('form')
    data = {}
    for element in form.find_all(['input', 'select', 'textarea']):
        name = element.get('name')
        if not name:
            continue
        if element.name == 'select':
            values = [
                option.get('value', option.text) for option in element.find_all('option') if option.has_attr('selected')
            ]
        elif element.name == 'textarea':
            values = [element.text]
        elif element.get('type') in ('submit', 'button', 'reset', 'file', 'image'):
            continue
        elif element.get('type') in ('checkbox', 'radio'):
            values = [element.get('value', 'on')] if element.has_attr('checked') else []
        else:
            values = [element.get('value', '')]
        data.setdefault(name, []).extend(values)
    data[submit_name] = ['']
    return data


def get_scenarios():
    # Endpoint paths and posted form data are taken from what iommi renders, like a browser would.
    request = get('/albums/create/')()
    album_form = Form.create(auto__model=Album).bind(request=request)
    choices_path = album_form.fields.artist.endpoints.choices.endpoint_path
    tbody_path = album_list.bind(request=get('/albums/')()).endpoints.tbody.endpoint_path

    edit_form_data = form_data_from_html(album_edit_view(get(f'/albums/{EDITED_ALBUM}/edit/')()).content, '-submit')
    invalid_edit_form_data = {**edit_form_data, 'name': [''], 'year': ['nineteen eighty']}
    edit_table_data = form_data_from_html(tracks_edit_table_view(get('/tracks/edit/')()).content, '-save')

    return [
        Scenario(
            name='albums.list',
            description='Model table with filters, bulk edit, row actions and pagination',
            view=album_list_view,
            build_request=get('/albums/'),
            expected_text=['Album 000', 'Artist 00', 'Create album'],
        ),
        Scenario(
            name='albums.list_filtered',
            description='Same table: free text search, sorted on a column, second page',
            view=album_list_view,
            build_request=get('/albums/', {'freetext_search': 'Album 1', 'order': '-year', 'page': '2'}),
            expected_text=['Album 140', 'Album 131'],
        ),
        Scenario(
            name='albums.tbody_ajax',
            description='Same table: the ajax endpoint used to refresh rows when filtering',
            view=album_list_view,
            build_request=get('/albums/', {tbody_path: '', 'freetext_search': 'Album 2'}),
            expected_text=['{"html": ', 'Album 215'],
        ),
        Scenario(
            name='album_form.create',
            description='Model create form with FK select, M2M multi select, date, decimal and textarea',
            view=album_create_view,
            build_request=get('/albums/create/'),
            expected_text=['published_date', 'genres'],
        ),
        Scenario(
            name='album_form.edit_post',
            description='Model edit form: valid post, validation, save and redirect',
            view=album_edit_view,
            build_request=post(f'/albums/{EDITED_ALBUM}/edit/', edit_form_data),
            expected_status=302,
        ),
        Scenario(
            name='album_form.edit_post_invalid',
            description='Model edit form: post with validation errors, rendered again',
            view=album_edit_view,
            build_request=post(f'/albums/{EDITED_ALBUM}/edit/', invalid_edit_form_data),
            expected_text=['nineteen eighty', 'is-invalid'],
        ),
        Scenario(
            name='album_form.choices_ajax',
            description='Model create form: the select2 ajax endpoint for the artist FK',
            view=album_create_view,
            build_request=get('/albums/create/', {choices_path: 'Artist 1'}),
            expected_text=['Artist 10', 'Artist 19'],
        ),
        Scenario(
            name='tracks.edit_table',
            description='Edit table, 40 rows with 4 editable columns and delete checkboxes',
            view=tracks_edit_table_view,
            build_request=get('/tracks/edit/'),
            expected_text=['Track 010-00', 'Track 013-09'],
        ),
        Scenario(
            name='tracks.edit_table_post',
            description='Edit table: post all 40 rows back, validate and save',
            view=tracks_edit_table_view,
            build_request=post('/tracks/edit/', edit_table_data),
            expected_status=302,
        ),
        Scenario(
            name='dashboard',
            description='Page instantiated per request: menu, fragments, a form and two model tables',
            view=dashboard_view,
            build_request=get('/'),
            expected_text=['Dashboard', 'Latest releases', 'Artist 00'],
        ),
        Scenario(
            name='report',
            description='Table of 150 plain python objects and 8 columns, no database',
            view=report_view,
            build_request=get('/report/'),
            expected_text=['Track 000', 'Track 149'],
        ),
    ]
