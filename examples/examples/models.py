from django.db import models


class Foo(models.Model):
    a = models.IntegerField()

    def __unicode__(self):
        return 'Foo: %s' % self.a

class Bar(models.Model):
    b = models.ForeignKey(Foo)
    c = models.CharField(max_length=255)
