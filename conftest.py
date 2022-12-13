from pathlib import Path

import pytest

from docs.models import (
    Album,
    Artist,
    Track,
)


# pragma: no cover
def pytest_runtest_setup(item):
    django_marker = item.get_closest_marker("django_db") or item.get_closest_marker("django")
    if django_marker is not None:
        try:
            import django  # noqa: F401
        except ImportError:
            pytest.skip("test requires django")

    flask_marker = item.get_closest_marker("flask")
    if flask_marker is not None:
        try:
            import flask  # noqa: F401
        except ImportError:
            pytest.skip('test requires flask')


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    items[:] = sorted(items, key=lambda x: x.fspath)


def pytest_sessionstart(session):
    from iommi.docs import generate_api_docs_tests

    generate_api_docs_tests((Path(__file__).parent / 'docs').absolute())


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
