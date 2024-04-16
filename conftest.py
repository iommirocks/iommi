from pathlib import Path

import pytest
from django.db import connection

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


@pytest.fixture(autouse=True)
def reset_sequences(request, django_db_blocker):
    if request.node.get_closest_marker('django_db'):
        with django_db_blocker.unblock():
            cursor = connection.cursor()

            # noinspection SqlResolve
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for i, (table,) in enumerate(cursor.fetchall()):
                cursor.execute(f"""
                    INSERT INTO SQLITE_SEQUENCE (name,seq) SELECT '{table}', {(i + 1) * 1000} WHERE NOT EXISTS
                        (SELECT changes() AS change FROM sqlite_sequence WHERE change <> 0);
                """)


@pytest.fixture
def artist(transactional_db):
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
        Album.objects.get_or_create(name='Heaven & Hell', artist=artist, year=1980)[0],
        Album.objects.get_or_create(name='Mob Rules', artist=artist, year=1981)[0],
    ]


@pytest.fixture
def medium_discography(artist):
    ozzy, _ = Artist.objects.get_or_create(name='Ozzy Osbourne')
    return [
        Album.objects.get_or_create(name='Heaven & Hell', artist=artist, year=1980)[0],
        Album.objects.get_or_create(name='Blizzard of Ozz', artist=ozzy, year=1980)[0],
        Album.objects.get_or_create(name='Mob Rules', artist=artist, year=1981)[0],
    ]


def create_tracks(album_name, tracks):
    album = Album.objects.get(name=album_name)
    Track.objects.bulk_create(
        [
            Track(
                album=album,
                name=name,
                index=i + 1,
            )
            for i, name in enumerate(tracks)
        ]
    )


@pytest.fixture
def big_discography(medium_discography):
    create_tracks(
        'Heaven & Hell',
        [
            'Neon Knights',
            'Children of the Sea',
            'Lady Evil',
            'Heaven and Hell',
            'Wishing Well',
            'Die Young',
            'Walk Away',
            'Lonely Is the Word',
        ],
    )

    create_tracks(
        'Blizzard of Ozz',
        [
            'I Don\'t Know',
            'Crazy Train',
            'Goodbye to Romance',
            'Dee',
            'Suicide Solution',
            'Mr. Crowley',
            'No Bone Movies',
            'Revelation (Mother Earth)',
            'Steal Away (The Night)',
        ],
    )

    create_tracks(
        'Mob Rules',
        [
            'Turn Up the Night',
            'Voodoo',
            'The Sign of the Southern Cross',
            'E5150" (instrumental',
            'The Mob Rules',
            'Country Girl',
            'Slipping Away',
            'Falling Off the Edge of the World',
            'Over and Over',
        ],
    )
