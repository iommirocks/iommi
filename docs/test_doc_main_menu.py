from docs.models import Artist
from iommi import Table
from iommi.experimental.main_menu import (
    M,
    MainMenu,
    main_menu_middleware,
)
from tests.helpers import (
    req,
    show_output,
)


def fake_view():
    pass  # pragma: no cover


menu_declaration = None
urlpatterns = None


def test_base(settings, medium_discography):
    # language=rst
    """
    Main menu
    ~~~~~~~~~

    .. warning::

        The `MainMenu` component is considered experimental. That means the API can change in breaking ways in minor releases of iommi. It also means you import from `iommi.experimental` to make that clear.

    The main menu component in iommi is used to create the main navigation for your app. This is primarily useful for SaaS or internal apps. It creates a sidebar menu with support for nested menu items, and centralized access control that automatically shows only menu items the user has access to.

    To set up your main menu:

    - add the `iommi.experimental.main_menu.main_menu_middleware` middleware to the `MIDDLEWARE` list
    - declare your `MainMenu`
    - define the `IOMMI_MAIN_MENU` setting to point to where you have defined your menu (like `IOMMI_MAIN_MENU = 'your_app.main_menu.main_menu'`).
    - add the url patterns from the menu to your app

    Access control is recursive, meaning that if a user does not have access to a menu item, it is automatically denied access to all subitems.

    .. note::

        There are many more examples in :doc:`the cookbook <cookbook_main_menu>`.
    """

    # @test
    global menu_declaration
    global urlpatterns

    artists_view = fake_view
    albums_view = fake_view
    # @end

    menu_declaration = MainMenu(
        items=dict(
            artists=M(
                icon='people',
                view=artists_view,
            ),
            albums=M(
                icon='disc',
                view=albums_view,
            ),
        ),
    )

    # language=rst
    """
    Add the url patterns from the menu to your app:
    """

    urlpatterns = menu_declaration.urlpatterns()

    # language=rst
    """
    Your views will now get the menu rendered on standard iommi views. For non-iommi views you can render the menu with `{{ request.iommi_main_menu }}`.
    """

    # @test
    settings.IOMMI_MAIN_MENU = 'docs.test_doc_main_menu.menu_declaration'
    settings.ROOT_URLCONF = 'docs.test_doc_main_menu'
    assert 'iommi.experimental.main_menu.main_menu_middleware' in settings.MIDDLEWARE

    response = main_menu_middleware(get_response=lambda request: Table(auto__model=Artist).bind(request=request).render_to_response())(req('get', url='/artists/'))
    show_output(response)
    # @end
