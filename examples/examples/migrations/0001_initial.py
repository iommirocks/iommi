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
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('c', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Foo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('a', models.IntegerField()),
            ],
        ),
        migrations.AddField(
            model_name='bar',
            name='b',
            field=models.ForeignKey(to='examples.Foo'),
        ),
    ]
