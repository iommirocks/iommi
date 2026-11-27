from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateField,
    DecimalField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    Model,
    TextField,
)


class Genre(Model):
    name = CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Artist(Model):
    COUNTRIES = [('gb', 'United Kingdom'), ('us', 'United States'), ('se', 'Sweden'), ('de', 'Germany')]

    name = CharField(max_length=255, unique=True)
    country = CharField(max_length=2, choices=COUNTRIES)
    formed = IntegerField(null=True, blank=True)
    active = BooleanField(default=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/artists/{self.pk}/'

    class Meta:
        ordering = ('name',)


class Album(Model):
    name = CharField(max_length=255, unique=True)
    artist = ForeignKey(Artist, on_delete=CASCADE, related_name='albums')
    year = IntegerField()
    published_date = DateField(null=True, blank=True)
    genres = ManyToManyField(Genre, related_name='albums', blank=True)
    rating = DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    explicit = BooleanField(default=False)
    notes = TextField(blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/albums/{self.pk}/'

    class Meta:
        ordering = ('name',)


class Track(Model):
    name = CharField(max_length=255)
    index = IntegerField()
    album = ForeignKey(Album, on_delete=CASCADE, related_name='tracks')
    duration = IntegerField(help_text='In seconds')
    plays = IntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('album', 'index')
