from iommi import (
    Menu,
    MenuItem,
)
from tests.helpers import req


def test_menu():
    class MyMenu(Menu):
        home = MenuItem(url='/')
        artists = MenuItem()
        albums = MenuItem(include=False)
        empty_sub_menu = MenuItem(url=None, sub_menu=dict(foo=MenuItem(include=False)))

    menu = MyMenu().bind(request=req('GET'))
    assert menu.sub_menu
    assert menu.__html__() == '<nav><ul><li><a class="active link" href="/">Home</a></li><li><a class="link" href="/artists/">Artists</a></li></ul></nav>'

    assert repr(menu) == """root
    home -> /
    artists -> /artists/
"""


def test_submenu():
    class MyMenu(Menu):
        sub_menu = MenuItem(url=None, sub_menu=dict(foo=MenuItem(), bar=MenuItem()))

    menu = MyMenu().bind(request=req('GET'))
    assert menu.sub_menu
    assert menu.__html__() == '<nav><ul><li><a class="link">Sub menu</a><li><a class="link" href="/bar/">Bar</a></li><li><a class="link" href="/foo/">Foo</a></li></li></ul></nav>'
