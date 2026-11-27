from django.urls import (
    include,
    path,
)

from docs.models import *
from iommi import *
from iommi.path import (
    PathDecoder,
    decode_path,
    register_explicit_path_decoding,
    register_path_decoding,
)
from iommi.views import (
    auth_views,
    crud_views,
)


def test_functions():
    # language=rst
    """
    Functions
    =========

    The classes iommi exposes are documented one page each under
    :doc:`api`. This page covers the module level functions.

    Most of these are *registrations*: you call them once at startup (typically in
    the `ready` method of an `AppConfig`) to teach iommi about your code base. For
    why you would want to, see :doc:`registrations` and :doc:`semantic_models`.


    Model introspection
    -------------------

    These tell iommi which shortcut to use when it generates a `Column`, `Field` or
    `Filter` from a Django model field. See :doc:`registrations` for how to choose
    between them, and :doc:`auto` for the generation they affect.

    `register_factory(django_field_class, *, shortcut_name=MISSING, factory=MISSING, **kwargs)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Register the handling of a Django field class for `Column`, `Field` and `Filter`
    at once. Pass either `shortcut_name` (the name of a shortcut to call) or
    `factory` (a `Shortcut` instance or a callable returning one). Register `None`
    to make iommi ignore the field type.

    `register_column_factory` / `register_field_factory` / `register_filter_factory` / `register_edit_column_factory`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Same signature as `register_factory`, but each affects only one of `Column`,
    `Field`, `Filter` and `EditColumn`. Use these when the three need to differ.

    `register_related_factory(model, *, shortcut_name=MISSING, factory=MISSING, **kwargs)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Register handling of `ForeignKey` and `OneToOneField` by their *related* model
    rather than by field class. There are also
    `register_related_column_factory`, `register_related_field_factory` and
    `register_related_filter_factory` for the single-class versions.

    `register_related_multiple_factory(model, *, shortcut_name=MISSING, factory=MISSING, **kwargs)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    As above, for `ManyToManyField` and one-to-many (reverse foreign key). There are
    also `register_related_multiple_column_factory`,
    `register_related_multiple_field_factory` and
    `register_related_multiple_filter_factory`.

    `register_search_fields(*, model, search_fields, allow_non_unique=False, overwrite=False)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Declare which model fields `Query` uses to find an object by name, so the
    advanced query language can say `album=Heaven` instead of `album.pk=42`.
    `search_fields` accepts `__` separated paths. Pass `allow_non_unique=True` when
    the fields don't uniquely identify a row.


    Rendering
    ---------

    `register_cell_formatter(type_or_class, formatter)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Register how a value of a given type renders in a table cell. `formatter` is
    called with the keyword arguments `table`, `column`, `row` and `value`.

    `register_style(name, style, allow_overwrite=False)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Register a :doc:`Style` under `name` so it can be referenced as a string by
    `IOMMI_DEFAULT_STYLE` and `iommi_style`. Returns a context manager, which makes
    it convenient in tests. See :doc:`styles`.

    `html`
    ~~~~~~

    Not a function but a fragment builder object. `html.div('foo')` is a shorter way
    to write `Fragment(tag='div', children__text='foo')`, and any tag name works.
    See :doc:`fragments`.

    `M`
    ~~~

    Shorthand for declaring a :doc:`MainMenu` item. See :doc:`main_menu` and the
    :ref:`main menu cookbook <cookbook-main-menu>`.


    Path decoding
    -------------

    See :doc:`path` for the full picture.

    `register_path_decoding(**kwargs)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Register decoders for URL path components. Each keyword is the name you will
    use in your url pattern, and the value is a model (decoded by pk), a model
    field (decoded by that field), a callable, or a `PathDecoder`:
    """

    register_path_decoding(
        artist_pk=Artist,
        artist_name=Artist.name,
        album_pk=PathDecoder(
            decode=lambda string, **_: Album.objects.get(pk=string),
            name='album',
        ),
    )

    # language=rst
    """
    `PathDecoder(*, decode=None, model=None, name)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    An explicit decoder. `decode` is a callable receiving `string`, `request`,
    `decoded_kwargs` and `kwargs`; `name` is the keyword argument the decoded object
    is delivered under. Useful for lookups Django's path converters can't express,
    and for access control.

    `register_explicit_path_decoding(**kwargs)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lower level version of `register_path_decoding` that takes only `PathDecoder`
    instances, with no shorthand.

    `decode_path(f)`
    ~~~~~~~~~~~~~~~~

    Decorator that applies iommi's path decoders to a plain Django function based
    view, so it receives decoded objects as arguments:
    """

    @decode_path
    def my_view(request, artist, album):
        return artist, album

    # language=rst
    """
    The raw and decoded values are both available on `request.iommi_view_params`.


    Bundled views
    -------------

    See :doc:`views` for what these render.

    `crud_views(*, model, table=EMPTY, create=EMPTY, edit=EMPTY, delete=EMPTY, detail=EMPTY)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Returns an `include()` of list, create, detail, edit and delete views for
    `model`. The `table`, `create`, `edit`, `delete` and `detail` namespaces are
    passed through to the underlying `Table`/`Form`, so you can configure any of
    them, e.g. `crud_views(model=Album, table__page_size=10)`:
    """

    urlpatterns = [
        path('albums/', crud_views(model=Album)),
    ]

    # language=rst
    """
    `auth_views()`
    ~~~~~~~~~~~~~~

    Returns an `include()` of `login/`, `logout/` and `change_password/` views:
    """

    urlpatterns = [
        path('', auth_views()),
    ]

    # language=rst
    """
    `middleware(get_response)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    iommi's middleware, which lets a view return an iommi object directly. See
    :doc:`middleware`. Must be last in `MIDDLEWARE`.

    `iommi_render(view)`
    ~~~~~~~~~~~~~~~~~~~~

    Decorator that renders the iommi object returned by a single view, for when you
    don't want to install the middleware globally.


    .. _test-helpers:

    Test helpers
    ------------

    From `iommi.test_helpers`. See :doc:`testing` for how to use these.

    `do_post(form, do_post_key_validation=True, request_builder=req, **user_data)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Simulate a user filling out `form` and submitting it. Renders the form, extracts
    the default post data, merges `user_data` on top, and returns the form bound to
    the resulting POST request. Requires a form with a post target, so use
    `.create()`, `.edit()` or `.delete()`.

    Every key in `user_data` must exist in the rendered form; pass
    `do_post_key_validation=False` to allow keys that aren't plain fields.

    `req(method, url='/', **data)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Build a request with an anonymous user.

    `user_req(method, **data)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Build a request from a normal authenticated user.

    `staff_req(method, **data)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Build a request from an authenticated staff/superuser.

    `extract_form_data(content)`
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Extract the default form data from rendered HTML. Used by `do_post`.
    """

    # @test
    assert urlpatterns
    assert my_view
    # @end
