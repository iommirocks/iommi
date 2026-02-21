# language=rst
"""

Access control
~~~~~~~~~~~~~~

The iommi admin only allows access to users with the `is_staff` flag. Other than that iommi doesn't enforce any access control on its own. If you need any you have to implement it yourself for your specific use case. That being said, here are a few ideas:

- Middleware that checks URL of requests coming in, limiting certain paths (or all paths) to logged in users, users belonging to certain groups, etc. This is the easiest to get right as it's in one place and is easy to reason about. It can't handle many common cases, but it can be a good base to stand on.
- Path decoders in iommi can be used for access control if the object being decoded has access semantics. For example `/company/1/` could validate that the user is a member of the company with pk 1.
- You can generalize path decoder logic to call a `has_access` method on the model you decode.
- The `LoginRequiredMiddleware <https://docs.djangoproject.com/en/5.1/ref/middleware/#django.contrib.auth.middleware.LoginRequiredMiddleware>`_ can be used to default URLs to denied, where you have to mark allowed URLs with the `@login_not_required` decorator.

"""
import pytest
from django.urls import path

from docs.models import Track
from iommi import Page
from iommi.path import decode_path_components, register_path_decoding
from tests.helpers import req, user_req

pytestmark = pytest.mark.django_db


def test_path_decoder_for_access_control(track):
    # language=rst
    """
    Minimal example for path decoding access control
    ================================================
    """

    class AccessDeniedException(Exception):
        pass

    def has_access_decoder(model):
        def has_access_decoder_inner(string, request, **_):
            obj = model.objects.get(pk=string.strip())
            if not obj.has_access(request.user):
                raise AccessDeniedException()
            return obj
        return has_access_decoder_inner

    # @test
    with (
    # @end

    register_path_decoding(
        track_pk=has_access_decoder(Track),
    )

    # @test
    ):
        # @end
        urlpatterns = [
            path('<track_pk>/', Page().as_view()),
        ]

        # @test
        result = decode_path_components(request=user_req('get'), track_pk=str(track.pk))
        assert result['track_pk'] == track

        with pytest.raises(AccessDeniedException):
            decode_path_components(request=req('get'), track_pk=str(track.pk))
        # @end
