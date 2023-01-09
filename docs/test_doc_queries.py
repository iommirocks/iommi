from docs.models import *
from iommi import *
from tests.helpers import (
    req,
    show_output,
)

request = req('get')

from django.shortcuts import render
import pytest
pytestmark = pytest.mark.django_db


def test_queries():
    # language=rst
    """
    Queries
    =======

    iommi queries makes it easy to implement searching and filtering in your Django app.

    Major features:

    - Generate simple filtering GUIs
    - Supply your views with an advanced query language
    - Query language can be used stand alone without the GUI parts
    - Highly customizable GUI based on iommi :doc:`forms`

    Queries are normally used from inside iommi tables where they are an
    integrated part, but can also be used stand alone. See below for an
    example.

    .. image:: queries_example.png

    The code for the example above:
    """

    Table(
        auto__model=Album,
        page_size=10,
        columns__name__filter__include=True,
        columns__artist__filter__include=True,
    )

    # language=rst
    """
    Read the full documentation and the :doc:`cookbook` for more.
    """
    

def test_query_language():
    # language=rst
    """
    Query language
    --------------

    iommi comes with an advanced query language so users can filter tables
    after what they want. Searching songs can look like this:

    .. code-block::

        album=Paranoid AND lyrics:"have the power"

    This will find the song War Pigs, as it's from the album Paranoid and
    the lyrics contains the text "have the power". The query language supports
    `AND` and `OR`, parenthesis and the operations `<`, `<=`, `>`, `>=` for
    numerical values, and `=` for all values which is an exact case insensitive
    match. You can exclude with `!=`. As the example above shows `:` is used for
    case insensitive "contains" queries, and the inverse of that is `!:`.

    iommi tries to support what the user might intuitively write for searching
    boolean columns. It will interpret "n", "no", "0" (zero), "false", "f" and "off"
    as `false`  and the corresponding values for `true`.

    You can configure a `Filter` to be case sensitive by setting `query_operator_to_q_operator`
    to `case_sensitive_query_operator_to_q_operator`.

    iommi queries have a special form for filtering directly on pk, which can be
    very handy: `album.pk=3`.

    `query_operator_for_field` specifies what operation the simple form uses to
    interpret its inputs. The default is `=`, meaning exact case insensitive match.

    If you have table of `Song` and a foreign key to `Album`, if you search for
    `album=Paranoid` iommi will by default create the Django query
    `Q(album__name='Paranoid')`. If your model has different fields used as names,
    you must register those with `register_search_fields`, or if you want
    something other special for just this view you can use the `search_fields`
    parameter to specify the fields to use. Note that you can use `pk` or
    other non-string columns as search fields if you want.
    """
    

def test_stand_alone_example(small_discography):
    # language=rst
    """
    Stand alone example
    -------------------

    Simple view that allows the user to search for an album by choosing the artist from a drop down, and search
    for specific year in the advanced mode:
    """

    class AlbumQuery(Query):
        artist = Filter.choice_queryset(choices=Artist.objects.all())
        year = Filter.integer()

    def albums(request):
        query = AlbumQuery().bind(request=request)
        return render(
            request=request,
            template_name='albums.html',
            context={
                'query': query,
                'albums': query.get_q(),
            },
        )

    # @test
    albums(req('get'))
    # @end

    # language=rst
    """
    .. code-block:: html

        <!-- albums.html -->
        {{ query }}

        <ul>
            {% for album in albums %}
                <li>{{ album }}</li>
            {% endfor %}
        </ul>
        
    You will also need to render the assets in your `<head>` tag:
    
    .. code-block:: html
        
        {% for asset in query.iommi_collected_assets.values %}
            {{ asset }}
        {% endfor %}
    """

    # @test
    show_output(albums(req('get')))
    # @end

    # language=rst
    """
    Programmatically call the search API:
    """

    query = Query(auto__model=Album).bind(request=request)
    albums_queryset = query.parse_query_string(
        'artist="Black Sabbath" and (year=1991 or year=1992)'
    )
