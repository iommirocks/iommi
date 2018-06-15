from __future__ import unicode_literals

from django.db import models
from django.db.models import CASCADE
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Foo(models.Model):
    a = models.IntegerField()
    b = models.CharField(max_length=255)

    def __str__(self):
        return 'Foo(%s, %s)' % (self.a, self.b)


class Bar(models.Model):
    foo = models.ForeignKey(Foo, on_delete=CASCADE)
    c = models.BooleanField()


class Baz(models.Model):
    foo = models.ManyToManyField(Foo)
