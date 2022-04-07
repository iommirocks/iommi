from django.db import models


class Artist(models.Model):
    name = models.CharField(max_length=255, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        app_label = 'docs'


# album_start
class Album(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='albums')
    year = models.IntegerField()
    # album_end

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/albums/{self.pk}/'

    class Meta:
        ordering = ('name',)
        app_label = 'docs'


class Track(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    index = models.IntegerField()
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='tracks')
    duration = models.CharField(max_length=255, db_index=False, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('index',)
        app_label = 'docs'


class Musician(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    instrument = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        app_label = 'docs'


class Car(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    make = models.CharField(max_length=255)
    model = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        app_label = 'docs'
