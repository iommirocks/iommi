import pytest
from django.test import RequestFactory

from iommi.struct import Struct


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
