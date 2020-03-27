from iommi import (
    Menu,
    MenuItem,
)
from iommi._web_compat import Template
from iommi.menu import DebugMenu
from tests.helpers import req


def test_menu():
    class MyMenu(Menu):
        home = MenuItem(url='/')
        artists = MenuItem()
        albums = MenuItem(include=False)
        empty_sub_menu = MenuItem(url=None, sub_menu=dict(foo=MenuItem(include=False)))

    menu = MyMenu().bind(request=req('GET'))
    assert menu._active is False
    assert menu.sub_menu
    assert menu.sub_menu.home._active is True
    assert menu.sub_menu.artists.regex == '^/artists/'
    assert menu.__html__() == '<nav><ul><li><a class="active link" href="/">Home</a></li><li><a class="link" href="/artists/">Artists</a></li></ul></nav>'

    assert repr(menu) == """root
    home -> /
    artists -> /artists/
"""


def test_submenu():
    class MyMenu(Menu):
        sub_menu = MenuItem(url=None, sub_menu=dict(bar=MenuItem(), foo=MenuItem(after=0)))

    menu = MyMenu().bind(request=req('GET'))
    assert menu.sub_menu
    assert menu.__html__() == '<nav><ul><li>Sub menu<li><a class="link" href="/bar/">Bar</a></li><li><a class="link" href="/foo/">Foo</a></li></li></ul></nav>'


def test_debug_menu():
    assert DebugMenu().bind(request=req('get')).__html__() == '<nav style="background: white; border: 1px solid black; bottom: -1px; position: fixed; right: -1px; z-index: 100"><ul style="list-style: none"><li><a class="link" href="/code/">Code</a></li><li><a class="link" href="?/debug_tree">Tree</a></li><li onclick="window.iommi_start_pick()"><a class="link" href="#">Pick</a></li></ul></nav>'


def test_template():
    menu = Menu(
        template=Template('{{ menu.sub_menu.foo.display_name }}'),
        sub_menu=dict(foo=MenuItem())
    ).bind(request=req('get'))
    assert menu.__html__() == 'Foo'


def test_validation():
    class MyMenu(Menu):
        sub_menu1 = MenuItem(url='foo', sub_menu=dict(bar=MenuItem(), foo=MenuItem(url='baz')))
        sub_menu2 = MenuItem(url='foo', sub_menu=dict(bar=MenuItem(), foo=MenuItem(url='baz')))
        sub_menu3 = MenuItem(url='bar', sub_menu=dict(bar=MenuItem(), foo=MenuItem(url='baz')))

    m = MyMenu().bind(request=req('get'))
    assert m.validate() == {
        '/bar/': [
            'bar',
            'sub_menu2/bar',
            'sub_menu3/bar',
        ],
        'baz': [
            'foo',
            'sub_menu2/foo',
            'sub_menu3/foo',
        ],
        'foo': [
            'sub_menu1',
            'sub_menu2',
        ],
    }
