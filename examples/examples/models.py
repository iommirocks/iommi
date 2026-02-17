from django.db import models
from django.utils.translation import gettext_lazy as _


class Artist(models.Model):
    name = models.CharField(max_length=255, db_index=True, verbose_name=_('name'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name = _('artist')
        verbose_name_plural = _('artists')

    def get_absolute_url(self):
        return f'/artists/{self.pk}/'


class Album(models.Model):
    name = models.CharField(max_length=255, db_index=True, verbose_name=_('name'))
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='albums', verbose_name=_('artist'))
    year = models.IntegerField(verbose_name=_('year'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name = _('album')
        verbose_name_plural = _('albums')

    def get_absolute_url(self):
        return f'/albums/{self.pk}/'


class Track(models.Model):
    name = models.CharField(max_length=255, db_index=True, verbose_name=_('name'))
    index = models.IntegerField(verbose_name=_('index'))
    album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='tracks', verbose_name=_('album'))
    duration = models.CharField(max_length=255, db_index=False, null=True, blank=True, verbose_name=_('duration'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('index',)
        verbose_name = _('track')
        verbose_name_plural = _('tracks')
