from docs.models import *
from iommi import *
from tests.helpers import (
    req,
    show_output,
    show_output_collapsed,
)

request = req('get')


def test_equivalence():
    # language=rst
    """
    Equivalence
    ===========

    In iommi there are multiple ways to accomplish the same thing. The two most obvious ways are declarative and programmatic. But there are different paths even within those two main paths. This page is an overview of a few of those ways. Hopefully you will see the philosophy through these examples. Let's get started!


    First a model:

    .. literalinclude:: models.py
         :start-after: # album_start
         :end-before: # album_end
         :language: python
    """

    # language=rst
    """
    We want to create a form to create an album. We already have the artist from the URL, so that field shouldn't be in the form.

    The following forms all accomplish this goal (you can use `form.as_view()` to create a view from a `Form` instance):
    """

    form = Form.create(
        auto__model=Album,
        auto__exclude=['artist'],
    )

    # @test
    show_output(form)
    # @end

    form = Form.create(
        auto=dict(
            model=Album,
            exclude=['artist'],
        ),
    )

    # @test
    show_output_collapsed(form)
    # @end

    form = Form.create(
        auto__model=Album,
        fields__artist__include=False,
    )

    # @test
    show_output_collapsed(form)
    # @end

    class AlbumForm(Form):
        class Meta:
            auto__model = Album
            auto__exclude = ['artist']

    form = AlbumForm.create()

    # @test
    show_output_collapsed(form)
    # @end

    class AlbumForm(Form):
        class Meta:
            auto__model = Album
            auto__include = ['name', 'year']

    form = AlbumForm.create()

    # @test
    show_output_collapsed(form)
    # @end

    class AlbumForm(Form):
        class Meta:
            auto__model = Album
            fields__artist__include = False

    form = AlbumForm.create()

    # @test
    show_output_collapsed(form)
    # @end

    # language=rst
    """
    Without using the `auto` features:
    """

    # @test
    def create_album(**_):
        pass
    # @end

    class AlbumForm(Form):
        name = Field()
        year = Field.integer()

        class Meta:
            title = 'Create album'
            actions__submit__post_handler = create_album

    form = AlbumForm()

    # @test
    show_output_collapsed(form)
    # @end

    form = Form(
        fields__name=Field(),
        fields__year=Field.integer(),
        title='Create album',
        actions__submit__post_handler=create_album,
    )

    # @test
    show_output_collapsed(form)
    # @end

    # language=rst
    """
    You can read more about this in the philosophy section under :ref:`philosophy_hybrid_api`.
    """
