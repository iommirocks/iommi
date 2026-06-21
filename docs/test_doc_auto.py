from docs.models import (
    Album,
)
from iommi import Form
from iommi.docs import show_output


def test_auto():
    # language=rst
    """
    .. _auto:

    `auto`
    ------

    The `auto` configuration namespace is used to generate forms/tables/etc from Django models. The simplest example is:

    """
    form = Form(auto__model=Album)

    # @test
    show_output(form)
    # @end

    # language=rst
    """
    By default you will get all fields from the model except the primary key. You can use `include` to include it again:
    """

    form = Form(
        auto__model=Album,
        fields__pk__include=True,
    )

    # @test
    show_output(form)
    # @end

    # language=rst
    """
    You can specify which model fields to include via `auto__include` to include just the fields you want, or `auto__exclude` to take all fields except some excluded fields. Fields/columns/etc can be excluded/included later using `include` on the field:  
    """

    form = Form(
        auto__model=Album,
        auto__include=['name', 'artist', 'year'],
        fields__name__include=False,
    )

    # @test
    show_output(form)
    # @end

    # language=rst
    """
    An item in the `auto__include` list can also be a dict. The `attr` key is the field to include (just like the plain string form), and the remaining keys are extra configuration passed to that field/column/etc. This is a more compact alternative to configuring each generated member separately via `fields__<name>__...`:
    """

    form = Form(
        auto__model=Album,
        auto__include=[
            dict(attr='name', display_name='Album name'),
            'artist',
            dict(attr='year', help_text='The year the album was released'),
        ],
    )

    # @test
    show_output(form)
    # @end
