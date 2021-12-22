from iommi import *
from iommi.admin import Admin
from django.urls import (
    include,
    path,
)
from django.db import models
from tests.helpers import req, user_req, staff_req
from docs.models import *
request = req('get')

from django.db.models import Model, CharField, IntegerField, ForeignKey



def test_equivalence():
    # language=rst
    """
    Equivalence
    ===========

    In iommi there are multiple ways to accomplish the same thing. The two most obvious ways are declarative and programmatic. But there are different paths even within those two main paths. This page is an overview of a few of those ways. Hopefully you will see the philosophy through these examples. Let's get started!


    First a model:


    """
    class Album(Model):
        name = CharField(max_length=255, db_index=True)
        artist = ForeignKey(Artist, on_delete=models.CASCADE, related_name='albums')
        year = IntegerField()


    # @test
        class Meta:
            app_label = 'docs_avoid_conflict'

    # language=rst
    """
    We want to create a form to create an album. We already have the artist from the URL, so that field shouldn't be in the form.

    The following forms all accomplish this goal (although they would need more work to create a full functioning view!):



    """
    form = Form(
        auto__model=Album,
        auto__exclude=['artist'],
    )



    form = Form(
        auto=dict(
            model=Album,
            exclude=['artist'],
        ),
    )



    form = Form(
        auto__model=Album,
        fields__artist__include=False,
    )



    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            auto__exclude = ['artist']

    form = ArtistForm()



    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            auto__include = ['name', 'year']

    form = ArtistForm()


    class ArtistForm(Form):
        class Meta:
            auto__model = Album
            fields__artist__include = False

    form = ArtistForm()


    # language=rst
    """
    Without using the `auto` features:


    """
    class ArtistForm(Form):
        name = Field()
        year = Field.integer()

        class Meta:
            title = 'Create album'

    form = ArtistForm()



    form = Form(
        fields__name=Field(),
        fields__year=Field.integer(),
        title='Create album'
    )


    # language=rst
    """
    You can read more about this in the philosophy section under :ref:`philosophy_hybrid_api`.
    """
