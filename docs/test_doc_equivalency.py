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

    In iommi there are two equivalence principles that are important to grasp:

    - declarative/programmatic hybrid API
    - double underscore as a short hand syntax for nesting dicts

    The model used for these examples is `Album`:

    .. literalinclude:: models.py
         :start-at: class Album
         :end-before: def __str__
         :language: python


    Declarative/programmatic hybrid API
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The programmatic API is pretty straight forward: you have a class constructor that takes some arguments. The interesting part is how we can mirror that *exactly* into a declarative style.

    """

    table = Table(
        model=Album,
        columns=dict(
            name=Column(),
        ),
    )

    # language=rst
    """
    This simple table can be written as a class definition:
    """

    class MyTable(Table):
        class Meta:
            model = Album

        name = Column()

    # language=rst
    """
    There are two things to notice here: 
    
    1. Variables declared in `class Meta` in iommi means they get passed into the constructor. `model = Album` in `Meta` is exactly the same as `Table(model=Album)`.
    2. The `name` column is declared on the class itself, and the `columns` part of the argument (`Table(columns=dict(...)`) is implicit. For `Page` the same implicit name is called `parts`, and for `Form` it's called `fields`.
    
    Double underscore short form
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    In iommi you can have very deeply nested object structures, and because you want to customize something deep inside a graph it would be cumbersome to nest dicts a lot. So `__` is used a separator.
    
    Say we have a table, where we want to turn on filtering for a column, but we want to insert a special CSS class (called `special`) on the label of the search field:          
    """

    table = Table(
        auto__model=Model,
        # Enable filtering
        columns__name__filter__include=True,
        # Set the CSS class on the label
        columns__name__filter__field__label__attrs__class__special=True,
    )

    # language=rst
    """
    We could also write this without using `__` for nesting:
    """

    table = Table(
        auto=dict(model=Model),
        columns=dict(
            name=dict(
                filter=dict(
                    # Enable filtering
                    include=True,
                    # Set the CSS class on the label
                    field=dict(
                        label=dict(
                            attrs={
                                # have to use a dict literal here,
                                # because `class` is a reserved keyword in Python
                                'class': dict(
                                    special=True,
                                ),
                            },
                        ),
                    ),
                ),
            ),
        ),
    )

    # language=rst
    """
    These two things have exactly the same meaning, but the `__` syntax is a lot shorter and cleaner.
    """

    # language=rst
    """
    Further examples
    ~~~~~~~~~~~~~~~~
    """

    # language=rst
    """
    We want to create a form to create an album for a specific artist. We already have the artist from the URL, so that field shouldn't be in the form.

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
