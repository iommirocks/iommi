import pytest
from django.contrib.auth.models import User

from examples.models import (
    Album,
    Artist,
    Track,
)


@pytest.fixture
def artist(db):
    return Artist.objects.create(name='Black Sabbath')


@pytest.fixture
def album(artist):
    return Album.objects.create(name='Heaven & Hell', artist=artist, year=1980)


@pytest.fixture
def track(album):
    return Track.objects.create(album=album, name='Neon Knights', index=1, duration='3:50')


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(username='admin', password='admin', is_staff=True)


@pytest.fixture
def discography(artist):
    albums_data = [
        ('Heaven & Hell', 1980, [('Neon Knights', '3:50'), ('Children of the Sea', '5:30')]),
        ('Mob Rules', 1981, [('Turn Up the Night', '3:42'), ('Voodoo', '4:34')]),
    ]
    albums = []
    for album_name, year, tracks in albums_data:
        album = Album.objects.create(name=album_name, artist=artist, year=year)
        albums.append(album)
        for i, (track_name, duration) in enumerate(tracks):
            Track.objects.create(album=album, name=track_name, index=i + 1, duration=duration)
    return albums
