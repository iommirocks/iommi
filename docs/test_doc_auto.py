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
    `auto__include` can also be a dict. The keys are the fields to include (just like the list form), and the values are extra configuration passed to that field/column/etc. This is a more compact alternative to configuring each generated member separately via `fields__<name>__...`:
    """

    form = Form(
        auto__model=Album,
        auto__include={
            'name': dict(display_name='Album name'),
            'artist': {},
            'year': dict(help_text='The year the album was released'),
        },
    )

    # @test
    show_output(form)
    # @end
