from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.urls import (
    path,
)

from docs.models import (
    Album,
    Artist,
    Track,
)
from iommi import (
    html,
    Page,
)
from iommi.path import (
    decode_path,
    decode_path_components,
    Decoder,
    register_advanced_path_decoding,
    register_path_decoding,
)
from tests.helpers import (
    req,
)

request = req('get')

import pytest

pytestmark = pytest.mark.django_db

# language=rst
"""
Path decoding
=============

Path decoding for Django function based views is simple and elegant. Declare your function:
"""


def test_path_fbv_example():
    def album_view(request, album_pk):
        album = get_object_or_404(Album, pk=album_pk)
        ...

    # language=rst
    """
    Then declare your path mapping:
    """

    urlpatterns = [
        path('<album_pk>/', album_view),
    ]

    # language=rst
    """
    For class based views it's a little more awkward with `self.kwargs`, but
    mostly the same. In iommi we have another approach that we think is more
    elegant and faster to develop with:
    """


# language=rst
"""
URLConf and iommi
~~~~~~~~~~~~~~~~~

The url parameters, or path components, are available in iommi under the `params` namespace. A simple example is:
"""


def test_path_url_mapping():
    class MyPage(Page):
        hello = html.div(
            lambda params, **_: f'Hello {params.name}',
        )

    urlpatterns = [
        path('<name>/', MyPage().as_view()),
    ]

    # language=rst
    """
    This simple view will take the `name` path parameter and print it on the page. This is sometimes useful, but it's more common to need some more complex lookup on our parameters, so that leads us to path decoders: 
    """

    # @test
    assert 'Hello Tony' in urlpatterns[0].callback(req('get'), name='Tony').content.decode()
    # @end


# language=rst
"""
iommi path decoders
~~~~~~~~~~~~~~~~~~~

In iommi we have a powerful and easy to use system for path decoding that also
works smoothly with iommi views. It builds on top of the params feature
described above. Let's look at an example: 

Register your models:
"""


def test_path_decoder(artist, album):
    # @test
    unregister_decoding = (
    # @end

    register_path_decoding(
        artist_name=Artist.name,
        artist_pk=Artist,
        album_pk=Album,
    )

    # @test
    )
    unregister_decoding.__enter__()

    class MyPage(Page):
        pass
    # @end

    # language=rst
    """
    Now in your path mapping you can write:
    """

    urlpatterns = [
        path('<artist_name>/<album_pk>/', MyPage().as_view()),
    ]

    # language=rst
    """
    ...and you will get an `Artist` instance in `params.artist` and an `Album`
    instance in `params.album`. The decoding will by default support
    `album_name` and `album_pk` if you register it like this. The name lookup
    assumes your name field is called `name` on the model. There's an advanced
    registration system for more complex lookups, but this should cover most
    usages.
    
    
    Use iommi decoders on a function based view
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   
    You can use the iommi path decoders on a normal FBV too:
    """

    @decode_path
    def my_view(request, artist, album):
        return artist, album

    # @test
    assert my_view(request, artist_pk=artist.pk, album_pk=album.pk) == (artist, album)
    # @end

    # language=rst
    """
    If you want to get any of the raw values before they are decoded you can access them
    via `request.iommi_view_params` which has both the undecoded and the decoded parameters.
    """

    # @test
    unregister_decoding.__exit__(None, None, None)
    # @end


# language=rst
"""
Advanced path decoders
~~~~~~~~~~~~~~~~~~~~~~

For cases where you want to decode something other than a pk or name you need the advanced path decoders. Here's a simple example:
"""


def test_path_advanced_decoder(track):
    # @test
    unregister_encoding = (
    # @end

    register_path_decoding(
        user_pk=User,
        user_username=User.username,
        user_email=User.email,
        track_foo=lambda string, request, decoded_kwargs, kwargs, **_: Track.objects.get(name__iexact=string.strip())
    )

    # @test
    )
    unregister_encoding.__enter__()
    # @end

    # language=rst
    """
    This will allow you to do `<user_pk>`, `<user_username>`, `<user_email>` in your url pattern for the `User` model, and `track_foo` for the `Track` model.  
    
    The first example just maps `pk`, `username` and `email` one to one to the model. So for an email lookup it will run `User.objects.get(email=params.email)` to get the `User` object. 
    
    The second example is for more complex use cases. As you have access to `request`, `decoded_kwargs` and `kwargs` in addition to the model you can perform path decoding that is not possible with Django path decoders. 
    """

    # @test
    user = User.objects.create(pk=11, username='tony', email='tony@example.com')
    result = decode_path_components(request=req('get'), user_email='tony@example.com', track_foo='  neoN kNights\n \t ')
    assert result['user'] == user
    assert result['track_foo'] == track

    unregister_encoding.__exit__(None, None, None)
    # @end
