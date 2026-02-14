from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('examples', '0003_load_initial_data'),
    ]

    operations = [
        migrations.DeleteModel(name='Bar'),
        migrations.DeleteModel(name='TBar'),
        migrations.DeleteModel(name='Foo'),
        migrations.DeleteModel(name='TFoo'),
        migrations.DeleteModel(name='UploadModel'),
    ]
