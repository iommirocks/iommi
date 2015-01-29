from django.db import models


class Foo(models.Model):
    a = models.IntegerField()

class Bar(models.Model):
    b = models.ForeignKey(Foo)
    c = models.CharField(max_length=255)
