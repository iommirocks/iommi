from django.db import models
from django.utils.translation import gettext as _


class Foo(models.Model):
    name = models.CharField(max_length=255)
    a = models.IntegerField()
    b = models.BooleanField()


class Bar(models.Model):
    b = models.ForeignKey(Foo, on_delete=models.CASCADE)
    c = models.CharField(max_length=255)


class TFoo(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    a = models.IntegerField()

    def __str__(self):
        return self.name


class TBar(models.Model):
    b = models.ForeignKey(TFoo, on_delete=models.CASCADE)
    c = models.CharField(max_length=255)


class UploadModel(models.Model):
    f = models.FileField()


class Artist(models.Model):
    name = models.CharField(max_length=255, db_index=True, verbose_name=_('artist'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Album(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='albums')
    year = models.IntegerField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Track(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    index = models.IntegerField()
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='tracks')
    duration = models.CharField(max_length=255, db_index=False, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('index',)
