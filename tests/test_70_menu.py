from iommi import (
    Menu,
    MenuItem,
)
from tests.helpers import req


def test_menu():
    class MyMenu(Menu):
        home = MenuItem(url='/')
        artists = MenuItem()

    menu = MyMenu().bind(request=req('GET'))
    assert menu.sub_menu
    assert menu.__html__() == '<nav><ul><li><a class="active link" href="/">Home</a></li><li><a class="link" href="/artists/">Artists</a></li></ul></nav>'
