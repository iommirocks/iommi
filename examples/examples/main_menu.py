from examples import (
    playground,
    storybook,
    supernaut,
)
from examples.iommi import Form
from examples.models import (
    Album,
    Artist,
    Track,
)
from iommi.admin import Admin
from iommi.experimental.main_menu import (
    EXTERNAL,
    M,
    MainMenu,
)

main_menu = MainMenu(
    items=dict(
        albums=M(
            view=supernaut.AlbumTable(auto__model=Album, columns__year__bulk__include=True),
            items=dict(
                create=M(view=Form.create(auto__model=Album)),
                album=M(
                    path='<album_pk>/',
                    params={'album'},
                    view=supernaut.AlbumPage,
                    display_name=lambda album, **_: album.name,
                    url=lambda album, **_: album.get_absolute_url(),
                ),
            ),
        ),
        artists=M(
            view=supernaut.ArtistTable(auto__model=Artist),
            items=dict(
                artist=M(
                    path='<artist_pk>/',
                    params={'artist'},
                    view=supernaut.ArtistPage,
                    display_name=lambda artist, **_: artist.name,
                    url=lambda artist, **_: artist.get_absolute_url(),
                ),
            ),
        ),
        tracks=M(view=supernaut.TrackTable(auto__model=Track)),
        storybook=M(view=storybook.storybook),
        playground=M(view=playground.PlaygroundPage),
        iommi_admin=Admin.m(),
        login=M(
            view=EXTERNAL,
            display_name='Log in',
            url='/iommi-admin/login/?next=/',
            include=lambda request, **_: not request.user.is_authenticated,
        ),
        log_out=M(
            view=EXTERNAL,
            display_name='Log out',
            url='/iommi-admin/logout/',
            include=lambda request, **_: request.user.is_authenticated,
        ),
    ),
)
