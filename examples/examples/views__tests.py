import pytest
from bs4 import BeautifulSoup
from django.test import RequestFactory
from django.urls import (
    include,
    path,
)

from examples.main_menu import main_menu
from iommi.struct import Struct

urlpatterns = [path('experimental/', include('examples.experimental_examples'))] + main_menu.urlpatterns()


def req(method, url='/', **data):
    request = getattr(RequestFactory(HTTP_REFERER='/'), method.lower())(url, data=data)
    request.user = Struct(is_staff=False, is_authenticated=False, is_superuser=False)
    return request


def staff_req(method, url='/', **data):
    request = req(method, url=url, **data)
    request.user = Struct(is_staff=True, is_authenticated=True, is_superuser=True)
    return request


@pytest.mark.django_db
def test_album_table_renders(album):
    from examples.models import Album
    from examples.views import AlbumTable

    table = AlbumTable(auto__model=Album).bind(request=req('get'))
    response = table.render_to_response()
    assert response.status_code == 200


@pytest.mark.django_db
def test_table_with_preprocess_rows(discography):
    from examples.iommi import Table
    from examples.models import Album

    table = Table(
        auto__model=Album,
        preprocess_rows=lambda rows, **_: rows.filter(year=1980),
    ).bind(request=req('get'))

    content = table.__html__()
    assert 'Heaven' in content
    assert 'Mob Rules' not in content


@pytest.mark.django_db
def test_form_create(artist):
    from examples.iommi import Form
    from examples.models import Album

    form = Form.create(auto__model=Album).bind(
        request=req(
            'post',
            name='Test Album',
            artist=str(artist.pk),
            year='2000',
            **{'-submit': ''},
        ),
    )
    form.render_to_response()
    assert Album.objects.filter(name='Test Album').exists()


@pytest.mark.django_db
def test_table_filter(discography):
    from examples.iommi import Table
    from examples.models import Album

    table = Table(
        auto__model=Album,
        columns__name__filter__include=True,
    ).bind(request=req('get', **{'query': 'name="Heaven & Hell"'}))

    content = table.__html__()
    assert 'Heaven' in content


@pytest.mark.django_db
def test_index_page_renders(album):
    from examples.views import IndexPage

    page = IndexPage().bind(request=req('get'))
    response = page.render_to_response()
    assert response.status_code == 200


@pytest.mark.django_db
def test_albums_route_uses_album_cards(client, settings, album):
    from examples.views import AlbumTable, album_card_table

    settings.ROOT_URLCONF = __name__

    response = client.get('/albums/')
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.select_one('.card')
    assert not soup.select('table, tbody')
    assert soup.select_one('a[href="/albums/create/"]')

    staff_table = album_card_table(table_class=AlbumTable).bind(request=staff_req('get'))
    staff_soup = BeautifulSoup(str(staff_table), 'html.parser')
    assert staff_soup.select_one(f'a[href="/albums/{album.pk}/edit/"]')
    assert staff_soup.select_one(f'a[href="/albums/{album.pk}/delete/"]')


@pytest.mark.django_db
def test_hybrid_album_cards_append_into_div(client, settings, artist):
    from examples.models import Album

    settings.ROOT_URLCONF = __name__
    settings.MIDDLEWARE = [middleware for middleware in settings.MIDDLEWARE if middleware != 'iommi.main_menu.main_menu_middleware']
    for i in range(12):
        Album.objects.create(name=f'Album {i:02}', artist=artist, year=1980 + i)

    url = '/experimental/pagination/hybrid/'
    first = client.get(url)
    assert first.status_code == 200
    soup = BeautifulSoup(first.content, 'html.parser')
    items = soup.select_one('[data-iommi-incremental-items]')
    assert items.name == 'div'
    assert len(items.select('.card')) == 10
    assert not soup.select('table, tbody')

    endpoint = soup.select_one('[data-iommi-incremental]')['data-iommi-incremental-endpoint']
    second = client.get(url, {endpoint: '2'})
    assert second.status_code == 200
    appended = BeautifulSoup(second.json()['html'], 'html.parser')
    assert len(appended.select('.card')) == 2
    assert not appended.select('table, tbody')
    assert second.json()['has_more'] is False


@pytest.mark.django_db
def test_artist_and_incremental_edit_table_example_saves_loaded_rows(client, settings, artist):
    from examples.models import Album

    settings.ROOT_URLCONF = __name__
    settings.MIDDLEWARE = [middleware for middleware in settings.MIDDLEWARE if middleware != 'iommi.main_menu.main_menu_middleware']
    albums = [Album.objects.create(name=f'Album {i}', artist=artist, year=1980 + i) for i in range(6)]
    url = f'/experimental/pagination/edit-artist/{artist.pk}/'

    first = client.get(url)
    assert first.status_code == 200
    first_html = BeautifulSoup(first.content, 'html.parser')
    assert first_html.select_one('input[name="name"]')
    assert first_html.select_one('[data-iommi-incremental-load-more]')
    assert not first_html.select('[data-iommi-incremental-page-link]')

    def assert_album_row_layout(row, pk):
        assert row.name == 'div'
        name = row.select_one(f'input[name="albums/name/{pk}"]')
        year = row.select_one(f'input[name="albums/year/{pk}"]')
        published_date = row.select_one(f'input[name="albums/published_date/{pk}"]')
        assert name and year and published_date
        assert name.find_parent(class_='row') != year.find_parent(class_='row')
        assert year.find_parent(class_='row') == published_date.find_parent(class_='row')

    assert_album_row_layout(first_html.select_one('[data-iommi-edit-table-row]'), albums[0].pk)

    endpoint = first_html.select_one('[data-iommi-incremental]')['data-iommi-incremental-endpoint']
    second = client.get(url, {endpoint: '2'})
    assert second.status_code == 200
    second_data = second.json()
    assert f'name="albums/name/{albums[-1].pk}"' in second_data['html']
    appended_row = BeautifulSoup(second_data['html'], 'html.parser').select_one('[data-iommi-edit-table-row]')
    assert_album_row_layout(appended_row, albums[-1].pk)
    token = BeautifulSoup(second_data['paginator_html'], 'html.parser').select_one('input[name$="incremental_pages"]')

    post_data = {'name': 'Black Sabbath updated', '-save': '', token['name']: token['value']}
    for album in albums:
        post_data[f'albums/name/{album.pk}'] = 'Updated album' if album == albums[-1] else album.name
        post_data[f'albums/year/{album.pk}'] = str(album.year)
        post_data[f'albums/published_date/{album.pk}'] = '2020-01-02' if album == albums[-1] else ''

    response = client.post(url, post_data)
    assert response.status_code == 302
    artist.refresh_from_db()
    albums[-1].refresh_from_db()
    assert artist.name == 'Black Sabbath updated'
    assert albums[-1].name == 'Updated album'
    assert str(albums[-1].published_date) == '2020-01-02'
    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_admin_renders(staff_user):
    from iommi.admin import Admin

    response = Admin.all_models().bind(request=staff_req('get')).render_to_response()
    assert response.status_code == 200


# The examples app registers `register_related_factory(Artist, shortcut_name='artist')` (see
# examples/apps.py), which resolves foreign keys to `Artist` via the custom `artist` shortcut. That
# shortcut only exists on the examples' own `Column`/`Field`/`Filter` subclasses, so the admin must
# use the examples' `Admin` (with the matching `table_class`/`form_class`) or building any view for a
# model with a FK to `Artist` -- like `Album` -- crashes with `AttributeError: ... has no attribute
# 'artist'`. These tests guard that interaction.


@pytest.mark.django_db
def test_admin_list_renders_model_with_registered_related_factory(album, staff_user):
    from examples.iommi import Admin

    response = (
        Admin.list()
        .refine_with_params(app_name='examples', model_name='album')
        .bind(request=staff_req('get'))
        .render_to_response()
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_create_renders_model_with_registered_related_factory(staff_user):
    from examples.iommi import Admin

    response = (
        Admin.create()
        .refine_with_params(app_name='examples', model_name='album')
        .bind(request=staff_req('get'))
        .render_to_response()
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_edit_renders_model_with_registered_related_factory(album, staff_user):
    from examples.iommi import Admin

    response = (
        Admin.edit()
        .refine_with_params(app_name='examples', model_name='album', pk=album.pk)
        .bind(request=staff_req('get'))
        .render_to_response()
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_delete_renders_model_with_registered_related_factory(album, staff_user):
    from examples.iommi import Admin

    response = (
        Admin.delete()
        .refine_with_params(app_name='examples', model_name='album', pk=album.pk)
        .bind(request=staff_req('get'))
        .render_to_response()
    )
    assert response.status_code == 200
