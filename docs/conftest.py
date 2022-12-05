import pytest
from docs.models import (
    Album,
    Artist,
    Track,
)


@pytest.fixture(autouse=True)
def docs_style(settings):
    settings.IOMMI_DEFAULT_STYLE = 'bootstrap_docs'


@pytest.fixture
def artist():
    return Artist.objects.create(name='Black Sabbath')


@pytest.fixture
def album(artist):
    return Album.objects.create(name='Heaven & Hell', artist=artist, year=1980)


@pytest.fixture
def track(album):
    return Track.objects.create(album=album, name='Neon Knights', index=1)


@pytest.fixture
def small_discography(artist):
    return [
        Album.objects.create(name='Heaven & Hell', artist=artist, year=1980),
        Album.objects.create(name='Mob Rules', artist=artist, year=1981),
    ]


@pytest.fixture
def medium_discography(artist):
    ozzy = Artist.objects.create(name='Ozzy Osbourne')
    return [
        Album.objects.create(name='Heaven & Hell', artist=artist, year=1980),
        Album.objects.create(name='Blizzard of Ozz', artist=ozzy, year=1980),
        Album.objects.create(name='Mob Rules', artist=artist, year=1981),
    ]
