from django.db import models


class Foo(models.Model):
    a = models.IntegerField()
    b = models.CharField(max_length=255)

    def __unicode__(self):
        return 'Foo(%s, %s)' % (self.a, self.b)


class Bar(models.Model):
    foo = models.ForeignKey(Foo)
    foo2 = models.ForeignKey(Foo)
    foo3 = models.ForeignKey(Foo)
    c = models.BooleanField()
