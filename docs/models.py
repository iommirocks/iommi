from django.db.models import (
    CASCADE,
    CharField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    Model,
    OneToOneField,
    TextField,
)


class Genre(Model):
    name = CharField(max_length=255, db_index=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/genres/{self.pk}/'

    class Meta:
        ordering = ('name',)
        app_label = 'docs'


class Artist(Model):
    name = CharField(max_length=255, db_index=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/artists/{self.pk}/'

    class Meta:
        ordering = ('name',)
        app_label = 'docs'


class Album(Model):
    name = CharField(max_length=255, db_index=True)
    artist = ForeignKey(Artist, on_delete=CASCADE, related_name='albums')
    year = IntegerField(default=1980)

    genres = ManyToManyField(Genre, related_name='albums')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/albums/{self.pk}/'

    class Meta:
        ordering = ('name',)
        app_label = 'docs'


class Track(Model):
    name = CharField(max_length=255, db_index=True)
    index = IntegerField()
    album = ForeignKey(Album, on_delete=CASCADE, related_name='tracks')
    duration = CharField(max_length=255, db_index=False, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('index',)
        app_label = 'docs'


class Musician(Model):
    name = CharField(max_length=255, db_index=True)
    instrument = CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        app_label = 'docs'


class Profile(Model):
    artist = OneToOneField(Artist, on_delete=CASCADE, related_name='profiles')
    description = TextField()

    def __str__(self):
        return self.artist.name

    class Meta:
        ordering = ('artist__name',)
        app_label = 'docs'
