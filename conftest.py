from datetime import date
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.db import connection

from docs.models import (
    Album,
    Artist,
    Track,
    FavoriteArtist,
)


# pragma: no cover
def pytest_runtest_setup(item):
    django_marker = item.get_closest_marker("django_db") or item.get_closest_marker("django")
    if django_marker is not None:
        try:
            import django  # noqa: F401
        except ImportError:
            pytest.skip("test requires django")


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    items[:] = sorted(items, key=lambda x: x.fspath)


def pytest_sessionstart(session):
    if not hasattr(session.config, 'workerinput'):
        # Only run on controller if under xdist

        from iommi.docs import generate_api_docs_tests, write_rst_from_pytest

        if not session.config.args:
            write_rst_from_pytest()
            generate_api_docs_tests((Path(__file__).parent / 'docs').absolute())
            write_rst_from_pytest()


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
def black_sabbath(transactional_db):
    return Artist.objects.create(name='Black Sabbath')


@pytest.fixture
def ozzy(transactional_db):
    return Artist.objects.create(name='Ozzy Osbourne')


@pytest.fixture
def album(black_sabbath):
    return Album.objects.create(name='Heaven & Hell', artist=black_sabbath, year=1980)


@pytest.fixture
def track(album):
    return Track.objects.create(album=album, name='Neon Knights', index=1)


@pytest.fixture
def small_discography(black_sabbath):
    return [
        Album.objects.get_or_create(name='Heaven & Hell', artist=black_sabbath, year=1980)[0],
        Album.objects.get_or_create(name='Mob Rules', artist=black_sabbath, year=1981)[0],
    ]


@pytest.fixture
def medium_discography(black_sabbath, ozzy):
    return [
        Album.objects.get_or_create(name='Heaven & Hell', artist=black_sabbath, year=1980)[0],
        Album.objects.get_or_create(name='Blizzard of Ozz', artist=ozzy, year=1980)[0],
        Album.objects.get_or_create(name='Mob Rules', artist=black_sabbath, year=1981)[0],
    ]


def create_tracks(artist, album_name, tracks):
    album = Album.objects.get(artist=artist, name=album_name)
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
def big_discography(black_sabbath, ozzy, medium_discography):
    create_tracks(
        black_sabbath,
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
        ozzy,
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
        black_sabbath,
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
        {'artist': 'Black Sabbath', 'name': '13', 'year': 2013, 'date': '2013-06-11'},
        {'artist': 'Dio', 'name': 'Angry Machines', 'year': 1996, 'date': '1996-10-15'},
        {'artist': 'Dio', 'name': 'At Donington UK: Live 1983 & 1987', 'year': 2010, 'date': '2010-05-25'},
        {'artist': 'Ozzy Osbourne', 'name': 'Bark At The Moon', 'year': 1983, 'date': '1983-11-15'},
        {'artist': 'Black Sabbath', 'name': 'Black Sabbath', 'year': 1970, 'date': '1970-02-13'},
        {'artist': 'Black Sabbath', 'name': 'Black Sabbath Vol 4', 'year': 1972, 'date': '1972-09-25'},
        {'artist': 'Ozzy Osbourne', 'name': 'Blizzard Of Ozz', 'year': 1980, 'date': '1980-09-20'},
        {'artist': 'Black Sabbath', 'name': 'Born Again', 'year': 1983, 'date': '1983-08-07'},
        {'artist': 'Black Sabbath', 'name': 'Captured Live!', 'year': 1983, 'date': '1983-01-01'},
        {'artist': 'Black Sabbath', 'name': 'Cross Purposes', 'year': 1994, 'date': '1994-01-31'},
        {'artist': 'Black Sabbath', 'name': 'Cross Purposes - Live', 'year': 1995, 'date': '1995-04-01'},
        {'artist': 'Black Sabbath', 'name': 'Dehumanizer', 'year': 1992, 'date': '1992-06-22'},
        {'artist': 'Ozzy Osbourne', 'name': 'Diary Of A Madman', 'year': 1981, 'date': '1981-11-07'},
        {'artist': 'Dio', 'name': "Dio's Inferno - The Last In Live", 'year': 1997, 'date': '1997-11-04'},
        {'artist': 'Django Reinhardt', 'name': 'Django', 'year': 1957, 'date': '1957-01-01'},
        {'artist': 'Django Reinhardt', 'name': 'Django (Volume 1)', 'year': 1957, 'date': '1957-01-01'},
        {'artist': 'Django Reinhardt', 'name': 'Django Reinhardt', 'year': 1961, 'date': '1961-01-01'},
        {'artist': 'Django Reinhardt', 'name': 'Django Volume V', 'year': 1959, 'date': '1959-01-01'},
        {'artist': 'Ozzy Osbourne', 'name': 'Down To Earth', 'year': 2001, 'date': '2001-10-16'},
        {'artist': 'Dio', 'name': 'Dream Evil', 'year': 1987, 'date': '1987-07-21'},
        {'artist': 'Dio', 'name': 'Evil Or Divine: Live In New York City', 'year': 2003, 'date': '2003-03-25'},
        {'artist': 'Dio', 'name': 'Finding The Sacred Heart – Live In Philly 1986 –', 'year': 2013, 'date': '2013-07-02'},
        {'artist': 'Black Sabbath', 'name': 'Forbidden', 'year': 1995, 'date': '1995-06-08'},
        {'artist': 'Tony Iommi', 'name': 'Fused', 'year': 2005, 'date': '2005-07-12'},
        {'artist': 'Black Sabbath', 'name': 'Headless Cross', 'year': 1989, 'date': '1989-04-17'},
        {'artist': 'Black Sabbath', 'name': 'Heaven And Hell', 'year': 1980, 'date': '1980-04-25'},
        {'artist': 'Dio', 'name': 'Holy Diver', 'year': 1983, 'date': '1983-05-25'},
        {'artist': 'Dio', 'name': 'Holy Diver Live', 'year': 2006, 'date': '2006-04-11'},
        {'artist': 'Dio', 'name': 'Intermission', 'year': 1986, 'date': '1986-07-07'},
        {'artist': 'Tony Iommi', 'name': 'Iommi', 'year': 2000, 'date': '2000-10-16'},
        {'artist': 'Dio', 'name': 'Killing The Dragon', 'year': 2002, 'date': '2002-05-28'},
        {'artist': 'Ozzy Osbourne', 'name': 'Live & Loud', 'year': 1993, 'date': '1993-06-28'},
        {'artist': 'Dio', 'name': 'Live - We Rock', 'year': 2010, 'date': '2010-04-06'},
        {'artist': 'Ozzy Osbourne', 'name': 'Live At Budokan', 'year': 2002, 'date': '2002-06-25'},
        {'artist': 'Black Sabbath', 'name': 'Live At Hammersmith Odeon', 'year': 2007, 'date': '2007-03-27'},
        {'artist': 'Black Sabbath', 'name': 'Live At Last', 'year': 1980, 'date': '1980-01-01'},
        {'artist': 'Black Sabbath', 'name': 'Live Evil', 'year': 1982, 'date': '1982-12-15'},
        {'artist': 'Dio', 'name': 'Live In London Hammersmith Apollo 1993', 'year': 2014, 'date': '2014-02-04'},
        {'artist': 'Black Sabbath', 'name': 'Live...Gathered In Their Masses', 'year': 2013, 'date': '2013-11-26'},
        {'artist': 'Dio', 'name': 'Lock Up The Wolves', 'year': 1990, 'date': '1990-05-14'},
        {'artist': 'Dio', 'name': 'Magica', 'year': 2000, 'date': '2000-03-21'},
        {'artist': 'Black Sabbath', 'name': 'Master Of Reality', 'year': 1971, 'date': '1971-07-21'},
        {'artist': 'Dio', 'name': 'Master Of The Moon', 'year': 2004, 'date': '2004-09-01'},
        {'artist': 'Black Sabbath', 'name': 'Mob Rules', 'year': 1981, 'date': '1981-11-04'},
        {'artist': 'Black Sabbath', 'name': 'Never Say Die!', 'year': 1978, 'date': '1978-09-28'},
        {'artist': 'Django Reinhardt', 'name': 'Newly Discovered Masters By Django Reinhardt And The Quintet Of The Hot Club Of France', 'year': 1961, 'date': '1961-01-01'},
        {'artist': 'Ozzy Osbourne', 'name': 'No More Tears', 'year': 1991, 'date': '1991-09-17'},
        {'artist': 'Ozzy Osbourne', 'name': 'Off The Record Specials With Mary Turner', 'year': 1987, 'date': '1987-01-01'},
        {'artist': 'Ozzy Osbourne', 'name': 'Ordinary Man', 'year': 2020, 'date': '2020-02-21'},
        {'artist': 'Ozzy Osbourne', 'name': 'Ozzmosis', 'year': 1995, 'date': '1995-10-23'},
        {'artist': 'Ozzy Osbourne', 'name': 'Ozzy Live', 'year': 2012, 'date': '2012-01-01'},
        {'artist': 'Black Sabbath', 'name': 'Paranoid', 'year': 1970, 'date': '1970-09-18'},
        {'artist': 'Black Sabbath', 'name': 'Past Lives', 'year': 2002, 'date': '2002-08-27'},
        {'artist': 'Black Sabbath', 'name': 'Reunion', 'year': 1998, 'date': '1998-10-20'},
        {'artist': 'Black Sabbath', 'name': 'Sabbath Bloody Sabbath', 'year': 1973, 'date': '1973-12-01'},
        {'artist': 'Black Sabbath', 'name': 'Sabotage', 'year': 1975, 'date': '1975-07-28'},
        {'artist': 'Dio', 'name': 'Sacred Heart', 'year': 1985, 'date': '1985-08-15'},
        {'artist': 'Ozzy Osbourne', 'name': 'Scream', 'year': 2010, 'date': '2010-06-15'},
        {'artist': 'Django Reinhardt', 'name': 'Souvenirs De Django Reinhardt Volume 2', 'year': 1954, 'date': '1954-01-01'},
        {'artist': 'Ozzy Osbourne', 'name': 'Speak Of The Devil', 'year': 1982, 'date': '1982-11-27'},
        {'artist': 'Dio', 'name': 'Strange Highways', 'year': 1993, 'date': '1993-11-02'},
        {'artist': 'Quintette Du Hot Club De France', 'name': "Swing '35-'39", 'year': 1970, 'date': '1970-01-01'},
        {'artist': 'Black Sabbath', 'name': 'Technical Ecstasy', 'year': 1976, 'date': '1976-09-25'},
        {'artist': 'Black Sabbath', 'name': 'The End', 'year': 2016, 'date': '2016-11-18'},
        {'artist': 'Black Sabbath', 'name': 'The End (4 February 2017 - Birmingham)', 'year': 2017, 'date': '2017-11-17'},
        {'artist': 'Black Sabbath', 'name': 'The Eternal Idol', 'year': 1987, 'date': '1987-11-24'},
        {'artist': 'Django Reinhardt', 'name': 'The Great Artistry Of Django Reinhardt', 'year': 1953, 'date': '1953-01-01'},
        {'artist': 'Ozzy Osbourne', 'name': 'The King Biscuit Flower Hour (#642)', 'year': 1986, 'date': '1986-01-01'},
        {'artist': 'Dio', 'name': 'The Last In Line', 'year': 1984, 'date': '1984-07-02'},
        {'artist': 'Quintette Du Hot Club De France', 'name': 'The Quintet Of The Hot Club Of France - Volume 2', 'year': 1943, 'date': '1943-01-01'},
        {'artist': 'Ozzy Osbourne', 'name': 'The Ultimate Sin', 'year': 1986, 'date': '1986-02-22'},
        {'artist': 'Black Sabbath', 'name': 'Tyr', 'year': 1990, 'date': '1990-08-20'},
        {'artist': 'Ozzy Osbourne', 'name': 'Under Cover', 'year': 2005, 'date': '2005-11-01'},
        {'artist': 'Django Reinhardt', 'name': 'Volume 2', 'year': 1957, 'date': '1957-01-01'},
        {'artist': 'Damnation', 'name': 'album 10', 'year': 1980, 'date': '1980-01-01'},
        {'artist': 'Damnation', 'name': 'album 9', 'year': 1980, 'date': '1980-01-01'},
    ]

    artist_by_name = {}
    for artist in {x['artist'] for x in albums}:
        artist_by_name[artist] = Artist.objects.create(name=artist)

    for album in albums:
        Album.objects.create(
            name=album['name'],
            artist=artist_by_name[album['artist']],
            year=album['year'],
            published_date=date.fromisoformat(album['date']),
        )


@pytest.fixture
def staff_user():
    return User.objects.create(username='staff_user', is_staff=True)


@pytest.fixture
def john_doe_user(transactional_db):
    return User.objects.create(username='john.doe', email='john.doe@example.com')


@pytest.fixture
def damnation(transactional_db):
    return Artist.objects.create(name='Damnation')


@pytest.fixture
def fav_artists(john_doe_user, black_sabbath, damnation, ozzy):
    return [
        FavoriteArtist.objects.create(user=john_doe_user, artist=black_sabbath, comment='Love it!', sort_order=0),
        FavoriteArtist.objects.create(user=john_doe_user, artist=ozzy, comment='I love this too!', sort_order=1),
        FavoriteArtist.objects.create(user=john_doe_user, artist=damnation, comment='And this as well', sort_order=2),
    ]
