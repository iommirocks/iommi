from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext

from examples import (
    example_adding_decorator,
    example_links,
)
from examples.models import (
    Album,
    Artist,
    Foo,
    TBar,
    TFoo,
)
from examples.views import (
    all_column_sorts,
    ExamplesPage,
)
from iommi import (
    Action,
    Column,
    EditTable,
    Field,
    html,
    Page,
    Table,
)

examples = []

example = example_adding_decorator(examples)


@example(gettext('Auto from model example 1'))
def table_auto_example_1(request):
    return Table(
        auto__model=Album,
    )


@example(gettext('Tables know how to render as CSV files'))
def csv(request):
    class ArtistTable(Table):
        class Meta:
            auto__model = Artist
            page_size = 5

            actions__download = Action(
                attrs__href=lambda table, **_: '?' + table.endpoints.csv.endpoint_path,
            )
            columns__name__extra_evaluated__report_name = 'name'
            extra_evaluated__report_name = 'artists'

    class AlbumTable(Table):
        class Meta:
            auto__model = Album
            page_size = 5

            actions__download = Action(
                attrs__href=lambda table, **_: '?' + table.endpoints.csv.endpoint_path,
            )
            columns__name__extra_evaluated__report_name = 'name'
            columns__artist__extra_evaluated__report_name = 'artist'
            columns__year__extra_evaluated__report_name = 'year'
            extra_evaluated__report_name = 'alums'

    return Page(
        parts=dict(
            artists=ArtistTable(),
            albums=AlbumTable(),
        ),
    )


@example(gettext('EditTable example'))
def edit_table(request):
    return EditTable(
        auto__model=Album,
        columns=dict(
            name=dict(
                filter__include=True,
                edit__include=True,
            ),
            year__edit__include=True,
        ),
    )


class IndexPage(ExamplesPage):
    header = html.h1('Table examples')

    description = html.p('Some examples of iommi tables')

    examples = example_links(examples)

    all_fields = html.p(
        Action(
            display_name='Example with all available types of columns',
            attrs__href='all_columns',
        ),
    )


urlpatterns = [
    path('', IndexPage().as_view()),
    path('all_columns/', all_column_sorts),
    path('example_1/', table_readme_example_1, name='readme_example_1'),
    path('example_2/', table_readme_example_2, name='readme_example_2'),
    path('example_3/', table_auto_example_1, name='readme_example_1'),
    path('example_4/', table_auto_example_2, name='readme_example_2'),
    path('example_5/', table_kitchen_sink, name='kitchen_sink'),
    path('example_6/', example_6_view),
    path('example_7/', table_two),
    path('example_8/', table_post_handler_on_lists),
    path('example_9/', extra_fields),
    path('example_10/', csv),
    path('example_11/', edit_table),
]
