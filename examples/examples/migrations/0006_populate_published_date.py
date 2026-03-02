from datetime import date

from django.db import migrations

# Real (or best-guess) release dates sourced from public knowledge.
# Key: (artist_name, album_name) -> date
RELEASE_DATES = {
    # Black Sabbath
    ("Black Sabbath", "Black Sabbath"): date(1970, 2, 13),
    ("Black Sabbath", "Paranoid"): date(1970, 9, 18),
    ("Black Sabbath", "Master of Reality"): date(1971, 7, 21),
    ("Black Sabbath", "Black Sabbath Vol. 4"): date(1972, 9, 25),
    ("Black Sabbath", "Sabbath Bloody Sabbath"): date(1973, 12, 1),
    ("Black Sabbath", "Sabotage"): date(1975, 7, 28),
    ("Black Sabbath", "Technical Ecstasy"): date(1976, 9, 25),
    ("Black Sabbath", "Never Say Die!"): date(1978, 9, 28),
    ("Black Sabbath", "Live at Last"): date(1980, 6, 27),
    ("Black Sabbath", "Heaven and Hell"): date(1980, 4, 25),
    ("Black Sabbath", "Mob Rules"): date(1981, 11, 4),
    ("Black Sabbath", "Live Evil"): date(1982, 12, 15),
    ("Black Sabbath", "Born Again"): date(1983, 8, 7),
    ("Black Sabbath", "Captured Live!"): date(1983, 8, 7),
    ("Black Sabbath", "The Eternal Idol"): date(1987, 11, 24),
    ("Black Sabbath", "Headless Cross"): date(1989, 4, 18),
    ("Black Sabbath", "Tyr"): date(1990, 8, 20),
    ("Black Sabbath", "Dehumanizer"): date(1992, 6, 22),
    ("Black Sabbath", "Cross Purposes"): date(1994, 1, 31),
    ("Black Sabbath", "Cross Purposes - Live"): date(1995, 4, 14),
    ("Black Sabbath", "Forbidden"): date(1995, 6, 8),
    ("Black Sabbath", "Reunion"): date(1998, 10, 20),
    ("Black Sabbath", "Past Lives"): date(2002, 8, 27),
    ("Black Sabbath", "Live at Hammersmith Odeon"): date(2007, 11, 27),
    ("Black Sabbath", "13"): date(2013, 6, 10),
    ("Black Sabbath", "Live... Gathered in Their Masses"): date(2013, 11, 22),
    ("Black Sabbath", "The End"): date(2017, 11, 17),
    # Dio
    ("Dio", "Holy Diver"): date(1983, 5, 25),
    ("Dio", "The Last In Line"): date(1984, 7, 2),
    ("Dio", "Sacred Heart"): date(1985, 8, 15),
    ("Dio", "Intermission"): date(1986, 7, 28),
    ("Dio", "Dream Evil"): date(1987, 7, 6),
    ("Dio", "Lock Up The Wolves"): date(1990, 5, 14),
    ("Dio", "Strange Highways"): date(1993, 11, 1),
    ("Dio", "Angry Machines"): date(1996, 10, 15),
    ("Dio", "Dio's Inferno - The Last In Live"): date(1997, 11, 18),
    ("Dio", "Magica"): date(2000, 3, 21),
    ("Dio", "Killing The Dragon"): date(2002, 5, 28),
    ("Dio", "Master Of The Moon"): date(2004, 8, 30),
    ("Dio", "Holy Diver Live"): date(2006, 4, 18),
    ("Dio", "Live - We Rock"): date(2010, 4, 14),
    ("Dio", "At Donington UK: Live 1983 & 1987"): date(2010, 9, 21),
    ("Dio", "Finding The Sacred Heart \u2013 Live In Philly 1986 \u2013"): date(2013, 6, 18),
    ("Dio", "Live In London Hammersmith Apollo 1993"): date(2014, 2, 11),
    ("Dio", "Donington '87"): date(2022, 5, 20),
    ("Dio", "Donington '83"): date(2022, 5, 20),
    # Ozzy Osbourne
    ("Ozzy Osbourne", "Blizzard Of Ozz"): date(1980, 9, 20),
    ("Ozzy Osbourne", "Diary Of A Madman"): date(1981, 11, 7),
    ("Ozzy Osbourne", "Speak Of The Devil"): date(1982, 11, 27),
    ("Ozzy Osbourne", "Bark At The Moon"): date(1983, 11, 15),
    ("Ozzy Osbourne", "The Ultimate Sin"): date(1986, 2, 22),
    ("Ozzy Osbourne", "King Biscuit Flower Hour [Airdate: August 24, 1986]"): date(1986, 8, 24),
    ("Ozzy Osbourne", "Tribute"): date(1987, 3, 19),
    ("Ozzy Osbourne", "No Rest For The Wicked"): date(1988, 9, 28),
    ("Ozzy Osbourne", "No More Tears"): date(1991, 9, 17),
    ("Ozzy Osbourne", "Live & Loud"): date(1993, 6, 22),
    ("Ozzy Osbourne", "Ozzmosis"): date(1995, 10, 23),
    ("Ozzy Osbourne", "Down To Earth"): date(2001, 10, 16),
    ("Ozzy Osbourne", "Live at Budokan"): date(2002, 6, 25),
    ("Ozzy Osbourne", "Under Cover"): date(2005, 11, 1),
    ("Ozzy Osbourne", "Black Rain"): date(2007, 5, 22),
    ("Ozzy Osbourne", "Scream"): date(2010, 6, 15),
    ("Ozzy Osbourne", "Ozzy Live"): date(2012, 9, 3),
    ("Ozzy Osbourne", "Ordinary Man"): date(2020, 2, 21),
    ("Ozzy Osbourne", "Patient Number 9"): date(2022, 9, 9),
    # Radiohead
    ("Radiohead", "Pablo Honey"): date(1993, 2, 22),
    ("Radiohead", "The Bends"): date(1995, 3, 13),
    ("Radiohead", "OK Computer"): date(1997, 6, 16),
    ("Radiohead", "In Concert - 725"): date(1997, 7, 25),
    ("Radiohead", "Kid A"): date(2000, 10, 2),
    ("Radiohead", "Amnesiac"): date(2001, 6, 5),
    ("Radiohead", "Hail To The Thief"): date(2003, 6, 9),
    ("Radiohead", "In Rainbows"): date(2007, 10, 10),
    ("Radiohead", "In Rainbows Disk 2"): date(2009, 8, 11),
    ("Radiohead", "The King Of Limbs"): date(2011, 2, 18),
    ("Radiohead", "A Moon Shaped Pool"): date(2016, 5, 8),
    ("Radiohead", "Minidiscs (Hacked)"): date(2019, 6, 18),
    # Tony Iommi
    ("Tony Iommi", "Iommi"): date(2000, 10, 16),
    ("Tony Iommi", "Fused"): date(2005, 7, 12),
    # Django Reinhardt – exact dates are mostly unknown for these
    # compilations/reissues, using Jan 1 of the release year.
    ("Django Reinhardt", "Django Reinhardt Und Der Hot Club De France"): date(1929, 1, 1),
    ("Django Reinhardt", "Django And His American Friends Vol. 1"): date(1930, 1, 1),
    ("Django Reinhardt", "Django Reinhardt y el Quinteto del Hot Club de Francia"): date(1932, 1, 1),
    ("Django Reinhardt", "Django And His American Friends, Vol. 2"): date(1935, 1, 1),
    ("Django Reinhardt", "Djangology"): date(1936, 1, 1),
    ("Django Reinhardt", "The Great Artistry Of Django Reinhardt"): date(1953, 1, 1),
    ("Django Reinhardt", "Souvenirs De Django Reinhardt Volume 2"): date(1954, 1, 1),
    ("Django Reinhardt", "Django (Volume 1)"): date(1957, 1, 1),
    ("Django Reinhardt", "Volume 2"): date(1957, 1, 1),
    ("Django Reinhardt", "Django Volume V"): date(1959, 1, 1),
    ("Django Reinhardt", "Django - Volume 8"): date(1959, 1, 1),
    ("Django Reinhardt", "Django Reinhardt Europe's Greatest Contribution To Jazz"): date(1964, 1, 1),
    ("Django Reinhardt", "And His Jazz Guitar"): date(1966, 1, 1),
    ("Django Reinhardt", "Django"): date(1969, 1, 1),
    ("Django Reinhardt", "Django Reinhardt (Volume II)"): date(1969, 1, 1),
    ("Django Reinhardt", "Django, Mon Fr\u00e8re"): date(1969, 1, 1),
    ("Django Reinhardt", "Djangologie 15 (1946-1947)"): date(1970, 1, 1),
    ("Django Reinhardt", "Djangologie 19"): date(1971, 1, 1),
    ("Django Reinhardt", "Django 1934 - Les Premiers Enregistrements Du Quintette Du H.C.F."): date(1972, 1, 1),
    ("Django Reinhardt", "Django \u00b435-\u00b439 - The Quintet Of The Hot Club Of France"): date(1973, 1, 1),
    ("Django Reinhardt", "Django Reinhardt"): date(1976, 1, 1),
    ("Django Reinhardt", "Nuages (Radio Sessions 1947, Vol. 1)"): date(1980, 1, 1),
    ("Django Reinhardt", "Django Reinhardt Au Club St-Germain-Des-Pr\u00e9s"): date(1983, 1, 1),
    ("Django Reinhardt", "Le Quintette Du Hot Club De France Feat. Stephane Grappelly"): date(1984, 1, 1),
    ("Django Reinhardt", "Djangology 49"): date(1990, 1, 1),
    ("Django Reinhardt", "Swing 39"): date(2000, 1, 1),
    ("Django Reinhardt", "Django Et Compagnie (Jazz In Paris)"): date(2000, 1, 1),
    ("Django Reinhardt", "Django's Blues"): date(2001, 1, 1),
    ("Django Reinhardt", "Et Le Hot Club De France"): date(2004, 1, 1),
    # Quintette Du Hot Club De France
    ("Quintette Du Hot Club De France", "The Quintet Of The Hot Club Of France - Volume 2"): date(1943, 1, 1),
    ("Quintette Du Hot Club De France", "Swing '35-'39"): date(1970, 1, 1),
}


def populate_published_date(apps, schema_editor):
    Album = apps.get_model('examples', 'Album')
    for album in Album.objects.select_related('artist').all():
        key = (album.artist.name, album.name)
        d = RELEASE_DATES.get(key)
        if d is None:
            # Fallback: use Jan 1 of the album year
            d = date(album.year, 1, 1)
        album.published_date = d
        album.save(update_fields=['published_date'])


def reverse_populate(apps, schema_editor):
    Album = apps.get_model('examples', 'Album')
    Album.objects.all().update(published_date=None)


class Migration(migrations.Migration):
    dependencies = [
        ('examples', '0005_add_album_published_date'),
    ]

    operations = [
        migrations.RunPython(populate_published_date, reverse_populate),
    ]
