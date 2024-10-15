import pytest
from django.urls import (
    include,
    path,
)

from docs.models import Album
from iommi import Form
from iommi.views import (
    auth_views,
    crud_views,
)
from tests.helpers import show_output

# language=rst
"""
Views
=====

iommi ships with some views for some common use cases: 

"""


def test_auth():
    # language=rst
    """
    Authorization
    ~~~~~~~~~~~~~
    We have `login`, `logout`, and `change_password` views, and there's a function to get all patterns:

    """

    urlpatterns = [
        path('', auth_views()),
    ]

    # @test
    url_patterns = urlpatterns[0].url_patterns
    assert len(url_patterns) == 3

    show_output(url_patterns[0])
    show_output(url_patterns[1])
    show_output(url_patterns[2])
    # @end


@pytest.mark.django_db
def test_crud_view(big_discography):
    # language=rst
    """
    CRUD views
    ~~~~~~~~~~

    Create a full CRUD set of views:

    """

    urlpatterns = [
        path('', crud_views(model=Album)),
    ]

    # @test
    url_patterns = urlpatterns[0].url_patterns
    assert len(url_patterns) == 5

    album = Album.objects.get(name='Heaven & Hell')

    show_output(url_patterns[0], url=f"/{str(url_patterns[0].pattern).replace('<pk>', str(album.pk))}")
    show_output(url_patterns[1], url=f"/{str(url_patterns[1].pattern).replace('<pk>', str(album.pk))}")
    show_output(url_patterns[2], url=f"/{str(url_patterns[2].pattern).replace('<pk>', str(album.pk))}")
    show_output(url_patterns[3], url=f"/{str(url_patterns[3].pattern).replace('<pk>', str(album.pk))}")
    show_output(url_patterns[4], url=f"/{str(url_patterns[4].pattern).replace('<pk>', str(album.pk))}")
    # @end
