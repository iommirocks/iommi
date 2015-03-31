from django.db import models


class Foo(models.Model):
    a = models.IntegerField()
    b = models.CharField(max_length=255)
