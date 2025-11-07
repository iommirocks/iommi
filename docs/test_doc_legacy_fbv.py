import pytest
from django.shortcuts import (
    get_object_or_404,
    render,
)

from docs.models import (
    Artist,
    Track,
)
from iommi import (
    Page,
    Table,
)
from iommi.docs import show_output
from tests.helpers import (
    call_view_through_middleware,
    req,
)

pytestmark = pytest.mark.django_db


# language=rst
"""
Add iommi to a FBV
~~~~~~~~~~~~~~~~~~

"""


def test_legacy_fbv(small_discography, black_sabbath):
    # language=rst
    """
    Let's say we have a simple view to display an album:
    """

    def view_artist(request, artist_name):
        artist = get_object_or_404(Artist, name=artist_name)
        return render(
            request,
            'view_artist.html',
            context={
                'artist': artist,
            },
        )

    # @test
    response = view_artist(req('get'), artist_name=black_sabbath.name)
    assert black_sabbath.name in response.content.decode()
    show_output(response)
    # @end

    # language=rst
    """
    There's a table in the template for the tracks but it's all manual written `<table>`, `<tr>`, etc tags and so doesn't have sorting, and it's just a lot of code in that template. It would be nicer to use an iommi table! 
    """


def test_legacy_fbv_step2(small_discography, black_sabbath):
    # language=rst
    """
    Add an iommi table
    ==================

    First the template is modified to extend `"iommi/base.html"` and wrap the content in `{% block content %}`.

    Then we need to create the iommi object, and pass the collected assets to the context:
    """

    def view_artist(request, artist_name):
        artist = get_object_or_404(Artist, name=artist_name)

        albums = Table(
            auto__rows=artist.albums.all(),
        ).bind(request=request)

        return render(
            request,
            'view_artist2.html',
            context={
                'artist': artist,
                'albums': albums,
                'assets': albums.iommi_collected_assets(),
            }
        )

    # @test
    response = call_view_through_middleware(view_artist, req('get'), artist_name=black_sabbath.name)
    assert black_sabbath.name in response.content.decode()
    show_output(response)
    # @end

    # language=rst
    """
    Now in the template we can add `{{ albums }}` to render the table, and we can delete all the old manually written table html.
    """


def test_legacy_fbv_step3(black_sabbath, album, track):
    # language=rst
    """
    AJAX dispatch
    =============

    There are two problems with this code so far though, and that is that if we add filtering on album it breaks. One of the nice features
    of iommi is the automatic ajax endpoints (and by default a select2 widget), but this requires some extra routing, and that we include the
    relevant JS assets.

    For views that are fully iommi the routing is done for you, but as this is a legacy function based view that we don't want to
    rewrite fully right now, we'll have to add the routing boilerplate ourselves:
    """

    def view_artist(request, artist_name):
        artist = get_object_or_404(Artist, name=artist_name)

        tracks = Table(
            auto__rows=Track.objects.filter(album__artist=artist),
            columns__album__filter__include=True,
        ).bind(request=request)

        dispatch = tracks.perform_dispatch()
        if dispatch is not None:
            return dispatch

        return render(
            request,
            'view_artist.html',
            context={
                'artist': artist,
                'tracks': tracks,
                'assets': tracks.iommi_collected_assets(),
            }
        )

    # language=rst
    """
    You will also have to render the assets into the `<head>` block of your html:
    
    .. code-block:: html
    
        {% for asset in assets.values %}
            {{ asset }}
        {% endfor %}
    """

    # @test
    response = view_artist(req('get'), artist_name=black_sabbath.name)
    assert black_sabbath.name in response.content.decode()
    # ajax dispatch
    response = view_artist(req('get', **{'/choices': album.name}), artist_name=black_sabbath.name)
    assert black_sabbath.name not in response.content.decode()
    assert album.name in response.content.decode()
    # @end


def test_legacy_fbv_step4(black_sabbath, album, track):
    # language=rst
    """
    Multiple iommi components
    =========================

    You should only create one iommi component in order to get the automatic namespacing for free. So if you wanted to add two tables, you should wrap them in a `Page`:
    """

    def view_artist(request, artist_name):
        artist = get_object_or_404(Artist, name=artist_name)

        class MyPage(Page):
            albums = Table(auto__rows=artist.albums.all())
            tracks = Table(
                auto__rows=Track.objects.filter(album__artist=artist),
                columns__album__filter__include=True,
            )
        page = MyPage().bind(request=request)

        dispatch = page.perform_dispatch()
        if dispatch is not None:
            return dispatch

        return render(
            request,
            'view_artist3.html',
            context={
                'artist': artist,
                'tracks': page.parts.tracks,
                'albums': page.parts.albums,
                'assets': page.iommi_collected_assets(),
            }
        )

    # @test
    response = view_artist(req('get'), artist_name=black_sabbath.name)
    show_output(response)
    assert black_sabbath.name in response.content.decode()
    # ajax dispatch
    response = view_artist(req('get', **{'/album/choices': album.name}), artist_name=black_sabbath.name)
    assert black_sabbath.name not in response.content.decode()
    assert album.name in response.content.decode()
    # @end
