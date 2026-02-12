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
from docs.models import Track
from iommi.path import register_path_decoding


def test_path_decoder_for_access_control():
    # language=rst
    """
    Minimal example for path decoding access control
    ================================================
    """

    def has_access_decoder(model):
        def has_access_decoder_inner(string, user, **_):
            model = model.objects.get(pk=string.strip())
            if not model.has_access(user):
                raise AccessDeniedException()
            return model
        return has_access_decoder_inner

    # @test
    class AccessDeniedException(Exception):
        pass

    unregister_encoding = (
    # @end

    register_path_decoding(
        track_pk=has_access_decoder(Track),
    )

    # @test
    )
    unregister_encoding.__enter__()
    # @end
