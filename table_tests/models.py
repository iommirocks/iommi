from django.db import models
from django.db.models import CASCADE


class Foo(models.Model):
    a = models.IntegerField()
    b = models.CharField(max_length=255)

    def __str__(self):
        return 'Foo(%s, %s)' % (self.a, self.b)

    class Meta:
        ordering = ('pk',)


class Bar(models.Model):
    foo = models.ForeignKey(Foo, on_delete=CASCADE)
    c = models.BooleanField()

    class Meta:
        ordering = ('pk',)


class Baz(models.Model):
    foo = models.ManyToManyField(Foo)

    class Meta:
        ordering = ('pk',)


class FromModelWithInheritanceTest(models.Model):
    value = models.FloatField()
