from django.db.models import Q

from docs.models import *
from iommi import *
from tests.helpers import (
    req,
    show_output,
    show_output_collapsed,
)

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

    By default the name of filters are derived from the name you specify or from the model field name
    For deeply nested names double underscores are replaced with single underscores, and those names
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
    show_output(track_table, '?-query%2Fquery=artist%3D"black+sabbath"')
    # @end
