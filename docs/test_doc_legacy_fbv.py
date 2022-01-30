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
from tests.helpers import (
    req,
    show_output,
)

pytestmark = pytest.mark.django_db


# language=rst
"""
Add iommi to a FBV
~~~~~~~~~~~~~~~~~~

"""


def test_legacy_fbv(small_discography, artist):
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
    response = view_artist(req('get'), artist_name=artist.name)
    assert artist.name in response.content.decode()
    show_output('legacy_fbv/test_legacy_fbv', response)
    # @end

    # language=rst
    """
    There's a table in the template for the tracks but it's all manual written `<table>`, `<tr>`, etc tags and so doesn't have sorting, and it's just a lot of code in that template. It would be nicer to use an iommi table! 
    """


def test_legacy_fbv_step2(small_discography, artist):
    # language=rst
    """
    Add an iommi table
    ==================
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
            }
        )

    # @test
    response = view_artist(req('get'), artist_name=artist.name)
    assert artist.name in response.content.decode()
    show_output('legacy_fbv/test_legacy_fbv_step2', response)
    # @end

    # language=rst
    """
    Now in the template we can add `{{ tracks }}` to render the table, and we can delete all the old manually written table html.
    """


def test_legacy_fbv_step3(artist, album, track):
    # language=rst
    """
    AJAX dispatch
    =============

    There's a problem with this code so far though, and that is that if we add filtering on album it breaks. One of the nice features
    of iommi is the automatic ajax endpoints (and by default a select2 widget), but this requires some extra routing.

    For views that are fully iommi this routing is done for you, but as this is a legacy function based view that we don't want to
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
            }
        )

    # @test
    response = view_artist(req('get'), artist_name=artist.name)
    assert artist.name in response.content.decode()
    # ajax dispatch
    response = view_artist(req('get', **{'/choices': album.name}), artist_name=artist.name)
    assert artist.name not in response.content.decode()
    assert album.name in response.content.decode()
    # @end


def test_legacy_fbv_step4(artist, album, track):
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
            }
        )

    # @test
    response = view_artist(req('get'), artist_name=artist.name)
    show_output('legacy_fbv/test_legacy_fbv_step4', response)
    assert artist.name in response.content.decode()
    # ajax dispatch
    response = view_artist(req('get', **{'/album/choices': album.name}), artist_name=artist.name)
    assert artist.name not in response.content.decode()
    assert album.name in response.content.decode()
    # @end
