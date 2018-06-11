# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bar',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('c', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Foo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=255)),
                ('a', models.IntegerField()),
                ('b', models.BooleanField()),
            ],
        ),
        migrations.AddField(
            model_name='bar',
            name='b',
            field=models.ForeignKey(to='examples.Foo'),
        ),
    ]
