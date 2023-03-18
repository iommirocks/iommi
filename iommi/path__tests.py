import django
import pytest
from django.contrib.auth.models import User
from django.http import Http404

from docs.models import (
    Album,
    Artist,
    Track,
)

from iommi.path import (
    camel_to_snake,
    decode_path,
    decode_path_components,
    Decoder,
    PathDecoder,
    register_advanced_path_decoding,
    register_path_decoding,
)
from tests.helpers import req


@pytest.mark.django_db
def test_simple_path_decode():
    artist = Artist.objects.create(pk=3, name='Black Sabbath')
    album = Album.objects.create(pk=7, name='Heaven & Hell', artist=artist, year=1980)
    with register_path_decoding(artist_pk=Artist, album_name=Album.name):
        actual = decode_path_components(
            request=req('get'),
            pass_through='pass through',
            artist_pk=str(artist.pk),
            album_name='Heaven & Hell',
        )
        expected = dict(
            artist=artist,
            album=album,
            pass_through='pass through',
        )
        assert actual == expected


@pytest.mark.django_db
def test_explicit_parameter_name_path_decode():
    artist = Artist.objects.create(pk=3, name='Black Sabbath')
    second_artist = Artist.objects.create(pk=7, name='Dio')
    with register_path_decoding(artist_pk=Artist, second_artist_pk=PathDecoder(model=Artist, name='second_artist')):
        actual = decode_path_components(
            request=req('get'),
            pass_through='pass through',
            artist_pk=str(artist.pk),
            second_artist_pk=str(second_artist.pk),
        )
        expected = dict(
            artist=artist,
            second_artist=second_artist,
            pass_through='pass through',
        )
        assert actual == expected


@pytest.mark.django_db
def test_path_decode():
    artist = Artist.objects.create(pk=3, name='Black Sabbath')
    album = Album.objects.create(pk=7, name='Heaven & Hell', artist=artist, year=1980)
    with register_path_decoding(artist_for_album=lambda string, key, **_: Album.objects.get(pk=string).artist):
        actual = decode_path_components(
            request=req('get'),
            artist_for_album=str(album.pk),
        )
        expected = dict(
            artist_for_album=artist,
        )
        assert actual == expected


@pytest.mark.skipif(not django.VERSION[:2] >= (4, 0), reason='Requires django 4.0+')
@pytest.mark.django_db
def test_other_attribute_path_decode():
    user = User.objects.create(pk=11, username='tony', email='tony@example.com')
    with register_path_decoding(
        user_email=User.email,
    ):
        actual = decode_path_components(
            request=req('get'),
            user_email='tony@example.com',
        )
        expected = dict(
            user=user,
        )
        assert actual == expected


@pytest.mark.django_db
def test_lambda_path_decode():
    artist = Artist.objects.create(pk=3, name='Black Sabbath')
    album = Album.objects.create(pk=7, name='Heaven & Hell', artist=artist, year=1980)
    track = Track.objects.create(pk=13, album=album, name='Walk Away', index=7)
    with register_path_decoding(
        track=lambda string, **_: Track.objects.get(name__iexact=string.strip()),
    ):
        actual = decode_path_components(
            request=req('get'),
            track='  WALK aWay\n \t ',
        )
        expected = dict(
            track=track,
        )
        assert actual == expected


@pytest.mark.django_db
def test_view_decorator():
    artist = Artist.objects.create(pk=3, name='Black Sabbath')

    @decode_path
    def view(request, artist, pass_through):
        return request, artist, pass_through

    with register_path_decoding(artist_pk=Artist):
        request, *actual = view(req('get'), artist_pk=str(artist.pk), pass_through=7)

    expected = [artist, 7]
    assert actual == expected
    assert set(request.iommi_view_params.keys()) == {'artist', 'pass_through', 'artist_pk'}


@pytest.mark.django_db
def test_as_view_decodes():
    artist = Artist.objects.create(pk=3, name='Black Sabbath')

    from iommi import Page

    view = Page(parts__foo__children__text=lambda params, **_: str(params.artist)).as_view()

    with register_path_decoding(artist_pk=Artist):
        actual = view(req('get'), artist_pk=str(artist.pk), pass_through=7)

    assert 'Black Sabbath' in actual.content.decode()


@pytest.mark.django_db
@pytest.mark.skipif(pytest.__name__ == 'hammett', reason='hammett has problems with this warns() thing')
def test_legacy_path_decode():
    artist = Artist.objects.create(pk=3, name='Black Sabbath')
    album = Album.objects.create(pk=7, name='Heaven & Hell', artist=artist, year=1980)
    with pytest.warns(DeprecationWarning), register_path_decoding(Artist, Album):
        actual = decode_path_components(
            request=req('get'),
            pass_through='pass through',
            artist_pk=str(artist.pk),
            album_name='Heaven & Hell',
        )
        expected = dict(
            artist=artist,
            album=album,
            pass_through='pass through',
        )
        assert actual == expected

    user = User.objects.create(pk=11, username='tony', email='tony@example.com')
    track = Track.objects.create(pk=13, album=album, name='Walk Away', index=7)
    with pytest.warns(DeprecationWarning), register_advanced_path_decoding(
        {
            User: Decoder('pk', 'username', 'email'),
            Track: Decoder('foo', decode=lambda string, model, **_: model.objects.get(name__iexact=string.strip())),
        }
    ):
        actual = decode_path_components(
            request=req('get'), user_email='tony@example.com', track_foo='  WALK aWay\n \t '
        )
        expected = dict(
            user=user,
            track=track,
        )
        assert actual == expected


@pytest.mark.django_db
@pytest.mark.skipif(pytest.__name__ == 'hammett', reason='hammett has problems with this warns() thing')
def test_view_legacy_decorator():
    artist = Artist.objects.create(pk=3, name='Black Sabbath')

    @decode_path
    def view(request, artist, pass_through):
        return request, artist, pass_through

    with pytest.warns(DeprecationWarning):
        with register_path_decoding(Artist):
            request, *actual = view(req('get'), artist_pk=str(artist.pk), pass_through=7)

    expected = [artist, 7]
    assert actual == expected
    assert set(request.iommi_view_params.keys()) == {'artist', 'artist_pk', 'pass_through'}


@pytest.mark.django_db
def test_path_decode_404():
    with register_path_decoding(artist_name=Artist.name):
        with pytest.raises(Http404):
            decode_path_components(request=req('get'), artist_name='Does not exist')


def test_camel_to_snake():
    assert camel_to_snake('hello_friend') == 'hello_friend'
    assert camel_to_snake('helloFriend') == 'hello_friend'
    assert camel_to_snake('HelloFriend') == 'hello_friend'


def test_iommi_view_params_fills_already_existing():
    request = req('get')
    decode_path_components(request, foo=1)
    decode_path_components(request, bar=3)
    assert request.iommi_view_params == dict(foo=1, bar=3)


def test_model_pk_user_error():
    with pytest.raises(AssertionError):
        register_path_decoding(foo=Artist.pk)
