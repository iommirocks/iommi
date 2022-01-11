
Add iommi to a FBV
~~~~~~~~~~~~~~~~~~




Let's say we have a simple view to display an album:

.. code-block:: python

    def view_artist(request, artist_name):
        artist = get_object_or_404(Artist, name=artist_name)
        return render(
            request,
            'view_artist.html',
            context={
                'artist': artist,
            },
        )



There's a table in the template for the tracks but it's all manual written `<table>`, `<tr>`, etc tags and so doesn't have sorting, and it's just a lot of code in that template. It would be nicer to use an iommi table! 



Add an iommi table
==================

.. code-block:: python

    def view_artist(request, artist_name):
        artist = get_object_or_404(Artist, name=artist_name)

        tracks = Table(
            auto__rows=Track.objects.filter(album__artist=artist),
        ).bind(request=request)

        return render(
            request,
            'view_artist.html',
            context={
                'artist': artist,
                'tracks': tracks,
            }
        )



Now in the template we can add `{{ tracks }}` to render the table, and we can delete all the old manually written table html.




AJAX dispatch
=============

There's a problem with this code so far though, and that is that if we add filtering on album it breaks. One of the nice features
of iommi is the automatic ajax endpoints (and by default a select2 widget), but this requires some extra routing.

For views that are fully iommi this routing is done for you, but as this is a legacy function based view that we don't want to
rewrite fully right now, we'll have to add the routing boilerplate ourselves:

.. code-block:: python

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




Multiple iommi components
=========================

You should only create one iommi component in order to get the automatic namespacing for free. So if you wanted to add two tables, you should wrap them in a `Page`:

.. code-block:: python

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
            'view_artist.html',
            context={
                'artist': artist,
                'tracks': page.parts.tracks,
                'albums': page.parts.albums,
            }
        )

