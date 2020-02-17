from django.db import models


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
