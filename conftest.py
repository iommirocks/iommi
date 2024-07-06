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


@pytest.fixture
def really_big_discography():
    albums = [
        {'artist': 'Black Sabbath', 'name': '13', 'year': 2013},
        {'artist': 'Dio', 'name': 'Angry Machines', 'year': 1996},
        {'artist': 'Dio', 'name': 'At Donington UK: Live 1983 & 1987', 'year': 2010},
        {'artist': 'Ozzy Osbourne', 'name': 'Bark At The Moon', 'year': 1983},
        {'artist': 'Black Sabbath', 'name': 'Black Sabbath', 'year': 1970},
        {'artist': 'Black Sabbath', 'name': 'Black Sabbath Vol 4', 'year': 1972},
        {'artist': 'Ozzy Osbourne', 'name': 'Blizzard Of Ozz', 'year': 1980},
        {'artist': 'Black Sabbath', 'name': 'Born Again', 'year': 1983},
        {'artist': 'Black Sabbath', 'name': 'Captured Live!', 'year': 1983},
        {'artist': 'Black Sabbath', 'name': 'Cross Purposes', 'year': 1994},
        {'artist': 'Black Sabbath', 'name': 'Cross Purposes - Live', 'year': 1995},
        {'artist': 'Black Sabbath', 'name': 'Dehumanizer', 'year': 1992},
        {'artist': 'Ozzy Osbourne', 'name': 'Diary Of A Madman', 'year': 1981},
        {'artist': 'Dio', 'name': "Dio's Inferno - The Last In Live", 'year': 1997},
        {'artist': 'Django Reinhardt', 'name': 'Django', 'year': 1957},
        {'artist': 'Django Reinhardt', 'name': 'Django (Volume 1)', 'year': 1957},
        {'artist': 'Django Reinhardt', 'name': 'Django Reinhardt', 'year': 1961},
        {'artist': 'Django Reinhardt', 'name': 'Django Volume V', 'year': 1959},
        {'artist': 'Ozzy Osbourne', 'name': 'Down To Earth', 'year': 2001},
        {'artist': 'Dio', 'name': 'Dream Evil', 'year': 1987},
        {'artist': 'Dio', 'name': 'Evil Or Divine: Live In New York City', 'year': 2003},
        {'artist': 'Dio', 'name': 'Finding The Sacred Heart – Live In Philly 1986 –', 'year': 2013},
        {'artist': 'Black Sabbath', 'name': 'Forbidden', 'year': 1995},
        {'artist': 'Tony Iommi', 'name': 'Fused', 'year': 2005},
        {'artist': 'Black Sabbath', 'name': 'Headless Cross', 'year': 1989},
        {'artist': 'Black Sabbath', 'name': 'Heaven And Hell', 'year': 1980},
        {'artist': 'Dio', 'name': 'Holy Diver', 'year': 1983},
        {'artist': 'Dio', 'name': 'Holy Diver Live', 'year': 2006},
        {'artist': 'Dio', 'name': 'Intermission', 'year': 1986},
        {'artist': 'Tony Iommi', 'name': 'Iommi', 'year': 2000},
        {'artist': 'Dio', 'name': 'Killing The Dragon', 'year': 2002},
        {'artist': 'Ozzy Osbourne', 'name': 'Live & Loud', 'year': 1993},
        {'artist': 'Dio', 'name': 'Live - We Rock', 'year': 2010},
        {'artist': 'Ozzy Osbourne', 'name': 'Live At Budokan', 'year': 2002},
        {'artist': 'Black Sabbath', 'name': 'Live At Hammersmith Odeon', 'year': 2007},
        {'artist': 'Black Sabbath', 'name': 'Live At Last', 'year': 1980},
        {'artist': 'Black Sabbath', 'name': 'Live Evil', 'year': 1982},
        {'artist': 'Dio', 'name': 'Live In London Hammersmith Apollo 1993', 'year': 2014},
        {'artist': 'Black Sabbath', 'name': 'Live...Gathered In Their Masses', 'year': 2013},
        {'artist': 'Dio', 'name': 'Lock Up The Wolves', 'year': 1990},
        {'artist': 'Dio', 'name': 'Magica', 'year': 2000},
        {'artist': 'Black Sabbath', 'name': 'Master Of Reality', 'year': 1971},
        {'artist': 'Dio', 'name': 'Master Of The Moon', 'year': 2004},
        {'artist': 'Black Sabbath', 'name': 'Mob Rules', 'year': 1981},
        {'artist': 'Black Sabbath', 'name': 'Never Say Die!', 'year': 1978},
        {'artist': 'Django Reinhardt', 'name': 'Newly Discovered Masters By Django Reinhardt And The Quintet Of The Hot Club Of France', 'year': 1961},
        {'artist': 'Ozzy Osbourne', 'name': 'No More Tears', 'year': 1991},
        {'artist': 'Ozzy Osbourne', 'name': 'Off The Record Specials With Mary Turner', 'year': 1987},
        {'artist': 'Ozzy Osbourne', 'name': 'Ordinary Man', 'year': 2020},
        {'artist': 'Ozzy Osbourne', 'name': 'Ozzmosis', 'year': 1995},
        {'artist': 'Ozzy Osbourne', 'name': 'Ozzy Live', 'year': 2012},
        {'artist': 'Black Sabbath', 'name': 'Paranoid', 'year': 1970},
        {'artist': 'Black Sabbath', 'name': 'Past Lives', 'year': 2002},
        {'artist': 'Black Sabbath', 'name': 'Reunion', 'year': 1998},
        {'artist': 'Black Sabbath', 'name': 'Sabbath Bloody Sabbath', 'year': 1973},
        {'artist': 'Black Sabbath', 'name': 'Sabotage', 'year': 1975},
        {'artist': 'Dio', 'name': 'Sacred Heart', 'year': 1985},
        {'artist': 'Ozzy Osbourne', 'name': 'Scream', 'year': 2010},
        {'artist': 'Django Reinhardt', 'name': 'Souvenirs De Django Reinhardt Volume 2', 'year': 1954},
        {'artist': 'Ozzy Osbourne', 'name': 'Speak Of The Devil', 'year': 1982},
        {'artist': 'Dio', 'name': 'Strange Highways', 'year': 1993},
        {'artist': 'Quintette Du Hot Club De France', 'name': "Swing '35-'39", 'year': 1970},
        {'artist': 'Black Sabbath', 'name': 'Technical Ecstasy', 'year': 1976},
        {'artist': 'Black Sabbath', 'name': 'The End', 'year': 2016},
        {'artist': 'Black Sabbath', 'name': 'The End (4 February 2017 - Birmingham)', 'year': 2017},
        {'artist': 'Black Sabbath', 'name': 'The Eternal Idol', 'year': 1987},
        {'artist': 'Django Reinhardt', 'name': 'The Great Artistry Of Django Reinhardt', 'year': 1953},
        {'artist': 'Ozzy Osbourne', 'name': 'The King Biscuit Flower Hour (#642)', 'year': 1986},
        {'artist': 'Dio', 'name': 'The Last In Line', 'year': 1984},
        {'artist': 'Quintette Du Hot Club De France', 'name': 'The Quintet Of The Hot Club Of France - Volume 2', 'year': 1943},
        {'artist': 'Ozzy Osbourne', 'name': 'The Ultimate Sin', 'year': 1986},
        {'artist': 'Black Sabbath', 'name': 'Tyr', 'year': 1990},
        {'artist': 'Ozzy Osbourne', 'name': 'Under Cover', 'year': 2005},
        {'artist': 'Django Reinhardt', 'name': 'Volume 2', 'year': 1957},
        {'artist': 'Damnation', 'name': 'album 10', 'year': 1980},
        {'artist': 'Damnation', 'name': 'album 9', 'year': 1980},
    ]

    artist_by_name = {}
    for artist in {x['artist'] for x in albums}:
        artist_by_name[artist] = Artist.objects.create(name=artist)

    for album in albums:
        Album.objects.create(
            name=album['name'],
            artist=artist_by_name[album['artist']],
            year=album['year'],
        )
