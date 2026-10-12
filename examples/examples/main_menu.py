from examples import (
    playground,
    storybook,
    views,
)
from examples.iommi import Admin, Form
from examples.models import (
    Album,
    Artist,
    Track,
)
from iommi import (
    M,
    MainMenu,
)
from iommi.main_menu import EXTERNAL

main_menu = MainMenu(
    items=dict(
        albums=M(
            view=views.album_card_table(table_class=views.AlbumTable, columns__year__bulk__include=True),
            items=dict(
                create=M(view=Form.create(auto__model=Album)),
                album=M(
                    path='<album_pk>/',
                    params={'album'},
                    view=views.AlbumPage,
                    display_name=lambda album, **_: album.name,
                    url=lambda album, **_: album.get_absolute_url(),
                ),
            ),
        ),
        artists=M(
            view=views.ArtistTable(auto__model=Artist),
            items=dict(
                artist=M(
                    path='<artist_pk>/',
                    params={'artist'},
                    view=views.ArtistPage,
                    display_name=lambda artist, **_: artist.name,
                    url=lambda artist, **_: artist.get_absolute_url(),
                ),
            ),
        ),
        tracks=M(view=views.TrackTable(auto__model=Track)),
        load_more=M(
            view=EXTERNAL,
            display_name='Load more (tracks)',
            url='/experimental/pagination/load-more/',
        ),
        infinite_scroll=M(
            view=EXTERNAL,
            display_name='Infinite scroll (albums)',
            url='/experimental/pagination/infinite-scroll/',
        ),
        hybrid_scroll=M(
            view=EXTERNAL,
            display_name='Load more, then infinite scroll (albums)',
            url='/experimental/pagination/hybrid/',
        ),
        edit_table_load_more=M(
            view=EXTERNAL,
            display_name='Edit table: Load more (Black Sabbath)',
            url=views.black_sabbath_edit_url,
            include=lambda **_: Artist.objects.filter(name='Black Sabbath').exists(),
        ),
        calendar=M(view=views.AlbumCalendar()),
        storybook=M(view=storybook.storybook),
        playground=M(view=playground.PlaygroundPage),
        iommi_admin=Admin.m(),
        login=M(
            view=EXTERNAL,
            display_name='Log in',
            url='/iommi_admin/login/?next=/',
            include=lambda request, **_: not request.user.is_authenticated,
        ),
        log_out=M(
            view=EXTERNAL,
            display_name='Log out',
            url='/iommi_admin/logout/',
            include=lambda request, **_: request.user.is_authenticated,
        ),
    ),
)
