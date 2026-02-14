import json
from pathlib import Path

from django.db import migrations


def load_initial_data(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Artist = apps.get_model('examples', 'Artist')
    Album = apps.get_model('examples', 'Album')
    Track = apps.get_model('examples', 'Track')

    if not User.objects.filter(username='admin').exists():
        User.objects.create(username='admin', is_staff=True, first_name='Tony', last_name='Iommi')

    if not Album.objects.exists():
        json_path = Path(__file__).parent.parent.parent / 'scraped_data.json'
        with open(json_path) as f:
            artists = json.loads(f.read())

        for artist_name, albums in artists.items():
            artist, _ = Artist.objects.get_or_create(name=artist_name)
            for album_name, album_data in albums.items():
                album, _ = Album.objects.get_or_create(artist=artist, name=album_name, year=int(album_data['year']))
                for i, (track_name, duration) in enumerate(album_data['tracks']):
                    Track.objects.get_or_create(album=album, index=i + 1, name=track_name, duration=duration)


def reverse_initial_data(apps, schema_editor):
    Track = apps.get_model('examples', 'Track')
    Album = apps.get_model('examples', 'Album')
    Artist = apps.get_model('examples', 'Artist')
    User = apps.get_model('auth', 'User')

    Track.objects.all().delete()
    Album.objects.all().delete()
    Artist.objects.all().delete()
    User.objects.filter(username='admin').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('examples', '0002_auto_20210204_0831'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(load_initial_data, reverse_initial_data),
    ]
