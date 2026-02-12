from django.template import Template
from django.utils.translation import gettext_lazy

from docs.models import Album
from iommi.docs import (
    show_output,
    show_output_collapsed,
)
from iommi.main_menu import (
    EXTERNAL,
    M,
    MainMenu,
    path,
)
from iommi.path import register_path_decoding
from iommi.struct import Struct
from tests.helpers import req

request = req('get')

import pytest
pytestmark = pytest.mark.django_db


# language=rst
"""
.. _cookbook-main-menu:

Main menu
---------

"""

albums_view = edit_album_view = things_view = artists_view = album_view = lambda request, **_: None


def test_include(staff_user):
    # language=rst
    """
    How do I control which menu items are shown for a user?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses M.include

    Using `include` you can control which menu items are shown for a given user. This also controls access, so you can know that your menu and your access control are always in sync.
    """

    menu = MainMenu(
        items=dict(
            albums=M(
                view=albums_view,
            ),
            artists=M(
                view=artists_view,
                include=lambda user, **_: user.is_staff,
            ),
        ),
    )

    # @test
    show_output(menu)
    # @end

    # @test
    show_output(menu, user=staff_user)
    # @end


def test_display_name():
    # language=rst
    """
    How do I control the display name of a menu item?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses M.display_name

    By default the display name is derived from the `name` of the `M` object. So given:
    """

    menu = MainMenu(
        items=dict(
            albums=M(view=albums_view),
        ),
    )

    # @test
    show_output(menu)
    # @end

    # language=rst
    """
    The `name` would be "albums", and the display name is automatically derived as "Albums". The translation from `name` to `display_name` replaces `_` with space, runs `gettext_lazy()` on the result, and then capitalizes that.
    
    If you want to do something else, pass the `display_name` parameter:
    """

    menu = MainMenu(
        items=dict(
            albums=M(
                view=albums_view,
                display_name=gettext_lazy('Discography'),
            ),
        ),
    )

    # @test
    show_output(menu)
    # @end

    # language=rst
    """
    Note that `display_name` can be a function too.
    """


def test_paths():
    # language=rst
    """
    How do I add sub-paths for a menu item?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses M.paths

    Since the menu system can control access, it is useful to nest path mappings under a specific menu item without showing them in the menu. This is done with the `paths` argument:
    """

    menu = MainMenu(
        items=dict(
            albums=M(
                view=albums_view,
                paths=[
                    path('<album_pk>/edit/', edit_album_view),
                ],
            ),
        ),
    )

    # @test
    show_output_collapsed(menu)
    # @end


def test_external_links():
    # language=rst
    """
    How do I add external links in the menu?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses M.url
    .. uses EXTERNAL

    Use the special value `EXTERNAL` for the `view` argument, and use `url` argument:
    """

    menu = MainMenu(
        items=dict(
            albums=M(
                view=EXTERNAL,
                url='https://docs.iommi.rocks',
            ),
        ),
    )

    # @test
    show_output(menu)
    # @end

    # language=rst
    """
    Note the icon added by default for an external link. This is configurable via the `icon_formatter` on your `Style`.
    """


def test_nesting():
    # language=rst
    """
    How do I nest menu items?
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses M.items
    .. uses M.open

    You can create a menu hierarchy with the `items` argument, which produces expandable sections. iommi will open the menu items that match the current URL by default. You can also force a submenu to be open with the `open` argument:
    """

    menu = MainMenu(
        items=dict(
            things=M(
                view=things_view,
                open=True,  # force open
                items=dict(
                    albums=M(
                        view=albums_view,
                    ),
                    artists=M(
                        view=artists_view,
                    )
                ),
            ),
        ),
    )

    # @test
    show_output(menu)
    # @end

    # language=rst
    """
    The `open` argument can be a callable.
    """


def test_template():
    # language=rst
    """
    How do I put arbitrary html in the menu?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses M.template

    With the `template` argument you can put arbitrary html into menu items:
    """

    menu = MainMenu(
        items=dict(
            albums=M(
                view=EXTERNAL,
                template=Template('''
                <li style="margin-left: 1rem">
                    <span style="display: inline-block; width: 1.5rem; background: red; border-radius: 50%">&nbsp;</span>
                    <span style="display: inline-block; width: 1.5rem; background: orange; border-radius: 50%">&nbsp;</span>
                    <span style="display: inline-block; width: 1.5rem; background: yellow; border-radius: 50%">&nbsp;</span>
                    <span style="display: inline-block; width: 1.5rem; background: green; border-radius: 50%">&nbsp;</span>
                    <span style="display: inline-block; width: 1.5rem; background: blue; border-radius: 50%">&nbsp;</span>
                </li>
                ''')
            ),
        ),
    )

    # @test
    show_output(menu)
    # @end

    # language=rst
    """
    Note that you want to include the `<li>` tag.
        
    You can also override the base template via your `Style`. 
    """


def test_drill_down(album):
    # language=rst
    """
    How do I show which specific object I am on in the menu?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses M.path
    .. uses M.url
    .. uses M.params

    If you have a list of objects and you click into one of them, you might want to show that item in the menu, and potentially also sub-pages for that item. You do that by using iommi path decoders, and mapping everything together with `display_name`, `path`, `params` and `url`:

    """

    # @test
    with register_path_decoding(album_pk=Album):
        # @end

        menu = MainMenu(
            items=dict(
                albums=M(
                    view=albums_view,
                    items=dict(
                        album=M(
                            view=album_view,
                            display_name=lambda album, **_: str(album),
                            path='<album_pk>/',
                            params={'album'},
                            url=lambda album, **_: f'/albums/{album.pk}/',
                        ),
                    )
                ),
            ),
        )

        # @test
        request = req('get', url=f'/albums/{album.pk}/')
        request.iommi_view_params = Struct(album=album)

        show_output(menu, request=request)
        # @end


def test_dynamic_submenu(medium_discography):
    # language=rst
    """
    How do I make a data driven dynamic submenu?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses M.items

    There can be cases where you want a dynamic submenu where the items come from the database. To do this, specify `items` as a callable. Note that urls here can't be mapped to paths, as paths need to be known at startup.

    """

    menu = MainMenu(
        items=dict(
            albums=M(
                view=albums_view,
                items=lambda **_: {
                    f'album_{album.pk}': M(
                        view=EXTERNAL,
                        display_name=str(album),
                        url=album.get_absolute_url(),
                    )
                    for album in Album.objects.all()
                }
            )
        ),
    )

    # @test
    request = req('get', url=f'/albums/')

    show_output(menu, request=request)
    # @end


def test_non_rendered_menu_item(medium_discography):
    # language=rst
    """
    How do I use the menu for access control and path mapping without rendering into the menu?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    .. uses M.render

    The access control and path mapping of `M` items is very handy, but sometimes you don't want
    to show some URL in the sidebar menu. Use `render` to accomplish this:

    """

    menu = MainMenu(
        items=dict(
            albums=M(
                view=albums_view,
                render=False,
            )
        ),
    )

    # @test
    request = req('get', url=f'/albums/')

    response = show_output(menu, request=request)

    assert '<a href="/albums/"' not in response.decode()
    # @end
