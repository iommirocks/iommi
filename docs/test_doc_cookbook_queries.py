from django.db.models import Q

from docs.models import *
from iommi import *
from iommi.docs import (
    show_output,
    show_output_collapsed,
)
from tests.helpers import req

request = req('get')

import pytest
pytestmark = pytest.mark.django_db


def test_queries():
    # language=rst
    """
    Queries
    -------

    """


def test_how_do_i_override_what_operator_is_used_for_a_query():
    # language=rst
    """
    .. _override-operator:

    How do I override what operator is used for a query?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Filter.query_operator_to_q_operator

    The member `query_operator_to_q_operator` for `Filter` is used to convert from e.g. `:`
    to `icontains`. You can specify another callable here:
    """

    Table(
        auto__model=Track,
        columns__album__filter__query_operator_to_q_operator=lambda op: 'exact',
    )

    # language=rst
    """
    The above will force the album name to always be looked up with case
    sensitive match even if the user types `album<Paranoid` in the
    advanced query language. Use this feature with caution!

    See also `How do I control what Q is produced?`_

    """


def test_how_do_i_control_what_q_is_produced(really_big_discography):
    # language=rst
    """
    .. _control-q:

    How do I control what Q is produced?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses Filter.value_to_q

    For more advanced customization you can use `value_to_q`. It is a
    callable that takes `filter, op, value_string_or_f` and returns a
    `Q` object. The default handles `__`, different operators, negation
    and special handling of when the user searches for `null`.
    """

    class AlbumTable(Table):
        class Meta:
            auto__model = Album

            query__form__fields__eighties = Field.boolean(
                display_name="the '80s",
            )

            @staticmethod
            def query__filters__eighties__value_to_q(value_string_or_f, **_):
                if value_string_or_f == "1":
                    return Q(year__gte=1980) & Q(year__lte=1989)
                return Q()

    # @test
    show_output(AlbumTable(), url='/?eighties=1')
    # @end

    # language=rst
    """
    Without the filter selected:
    """

    # @test
    show_output_collapsed(AlbumTable(), url='/?eighties=0')
    # @end


def test_how_do_I_set_the_name_for_a_filter(big_discography):
    # language=rst
    """
    How do I control the name used in the advanced query?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Filter.query_name

    By default the names of filters are derived from the name you specify or from the model field name.
    For deeply nested names, double underscores are replaced with single underscores, and those names
    can become a bit unwieldy. You can then override this with `query_name`:
    """

    track_table = Table(
        auto__model=Track,
        auto__include=['name', 'album', 'album__artist__name'],
        columns__album_artist_name__filter=dict(
            include=True,
            query_name='artist',
        ),
    )

    # @test
    t = track_table.bind(request=req('get', **{'-query/query': 'artist="black sabbath"'}))
    assert t.query.get_advanced_query_param() == '-query/query'
    assert t.query.filters.album_artist_name.attr == 'album__artist__name'
    assert t.query.filters.album_artist_name.query_name == 'artist'
    assert not t.query.form.get_errors(), t.query.form.get_errors()
    assert repr(t.query.get_q()) == repr(Q(album__artist__name__iexact='black sabbath'))
    assert {row.album.artist.name for row in t.rows} == {'Black Sabbath'}, [row.album.artist.name for row in t.rows]

    show_output(track_table, '?-query%2Fquery=artist%3D"black+sabbath"')
    # @end


def test_how_do_I_filter_on_the_thing_itself(big_discography):
    # language=rst
    """
    How do I filter on the thing itself?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Filter.attr
    .. uses Filter.

    Filtering a table on the thing itself is sometimes useful, but can be a bit unintuitive:
    """

    albums = Table(
        auto__model=Album,
        auto__include=['name', 'artist', 'year'],

        query__filters__album=Filter.choice_queryset(
            attr=None,
            choices=Album.objects.all(),
            value_to_q=lambda value_string_or_f, **_: Q(pk=value_string_or_f) if value_string_or_f else Q(),
        ),
    )

    # @test
    show_output(albums, '')
    # @end


def test_how_do_i_style_the_query_container(big_discography):
    # language=rst
    """
    How do I style the query container?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Query.attrs
    .. uses Query.tag
    .. uses Query.form_container

    The `Query` component renders a container element that wraps the filter form.
    You can configure its tag and attributes directly. The simple (GUI) form itself
    is wrapped in `form_container`, which you can configure the same way:
    """

    albums = Table(
        auto__model=Album,
        auto__include=['name', 'artist', 'year'],
        columns__name__filter__include=True,
        query__attrs__style__border='2px solid red',
    )

    # @test
    show_output(albums, '')
    # @end


def test_how_does_a_query_filter_the_rows(big_discography):
    # language=rst
    """
    .. _query-filter-rows:

    How does a query filter the rows, and how do I post-process them?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Query.filter
    .. uses Query.filters
    .. uses Query.rows
    .. uses Query.model
    .. uses Query.postprocess

    A `Query` holds a set of `filters` and the `rows` (and `model`) it filters. When
    bound it builds a `Q` from the request, and its `filter` method applies that to
    the `rows`. Use `postprocess` to operate on the resulting rows afterwards. A
    `Query` is usually created for you by a `Table`, but you can declare and use one
    on its own:
    """

    class AlbumQuery(Query):
        name = Filter()
        year = Filter.integer()

    query = AlbumQuery(rows=Album.objects.all())

    # @test
    show_output(query)

    bound = query.bind(request=req('get'))
    assert set(bound.filters.keys()) == {'name', 'year'}
    assert bound.get_q() == Q()
    assert repr(Album.objects.filter(bound.parse_query_string('name="Mob Rules"'))) == repr(
        Album.objects.filter(name__iexact='Mob Rules')
    )
    # @end


def test_how_do_i_choose_which_filters_are_generated(big_discography):
    # language=rst
    """
    .. _query-auto-config:

    How do I choose which filters are generated from a model?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses QueryAutoConfig.model
    .. uses QueryAutoConfig.exclude
    .. uses QueryAutoConfig.default_included
    .. uses QueryAutoConfig.rows

    Like tables and forms, a `Query` can introspect a model. Pass `auto__model` (or
    `auto__rows`) and pick the filters with `auto__include`/`auto__exclude`, or flip
    the default with `auto__default_included`:
    """

    query = Query(
        auto__model=Album,
        auto__exclude=['year'],
    )

    # @test
    show_output(query)
    bound = query.bind(request=req('get'))
    assert 'year' not in bound.filters
    # @end


def test_how_do_i_configure_a_filters_gui_field(big_discography):
    # language=rst
    """
    .. _filter-gui-field:

    How do I configure a filter's GUI field?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Filter.field
    .. uses Filter.choices
    .. uses Filter.search_fields

    Each filter has a GUI form field, configured through the filter's `field`
    namespace. For choice filters `choices` is the list of options, and
    `search_fields` controls which model fields the autocomplete of a
    `choice_queryset` filter searches:
    """

    albums = Table(
        auto__model=Album,
        columns__year__filter=dict(
            include=True,
            field__include=True,
        ),
        columns__artist__filter=dict(
            include=True,
            search_fields=['name'],
        ),
    )

    # @test
    show_output(albums, '')
    # @end


def test_how_do_i_customize_how_a_filter_matches(big_discography):
    # language=rst
    """
    .. _filter-matching:

    How do I customize how a single filter matches?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Filter.query_operator_for_field
    .. uses Filter.unary
    .. uses Filter.parse
    .. uses Filter.is_valid_filter
    .. uses Filter.pk_lookup_to_q
    .. uses Filter.model
    .. uses Filter.model_field
    .. uses Filter.model_field_name

    Lower-level hooks change how an individual filter behaves:

    - `query_operator_for_field` is the operator used for the simple (GUI) form, e.g. `=` for exact-ish matching or `:` for "contains".
    - `parse` parses the user's input string into a value.
    - `unary` marks a filter as usable without a value in the advanced query language.
    - `is_valid_filter` decides whether a filter is allowed to be part of a query at all.
    - `pk_lookup_to_q` controls how a lookup by primary key is turned into a `Q`.

    Filters generated from a model also carry `model`, `model_field` and
    `model_field_name` (the same introspection you get on columns and fields), so a
    custom hook can read the Django field's metadata when it needs to.
    """

    albums = Table(
        auto__model=Album,
        columns__name__filter=dict(
            include=True,
            query_operator_for_field=':',
        ),
    )

    # @test
    show_output(albums, '')
    # @end


def test_how_do_i_customize_the_advanced_query_toggle(big_discography):
    # language=rst
    """
    .. _advanced-query:

    How do I customize the advanced query language area?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    .. uses Query.advanced

    A `Query` with filters offers an "advanced" free-text query language alongside
    the GUI form, with a link to toggle between them. Configure that toggle (and the
    advanced area) through the `advanced` namespace:
    """

    albums = Table(
        auto__model=Album,
        columns__name__filter__include=True,
        query__advanced__toggle__attrs__class__advanced_toggle=True,
    )

    # @test
    show_output(albums, '')
    # @end
