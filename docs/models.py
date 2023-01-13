from django.db.models import (
    CASCADE,
    CharField,
    ForeignKey,
    IntegerField,
    Model,
)


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
    year = IntegerField()

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
