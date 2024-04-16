from django.urls import (
    path,
    reverse_lazy,
)

from iommi import (
    Menu,
    MenuItem,
)
from iommi._web_compat import Template
from iommi.menu import get_debug_menu
from tests.helpers import req


def dummy_view(request):
    pass  # pragma: no cover


urlpatterns = [
    path('reverse_lazy_test', dummy_view, name='reverse-lazy-test'),
]


def test_menu():
    class MyMenu(Menu):
        home = MenuItem(url='/')
        artists = MenuItem()
        albums = MenuItem(include=False)
        empty_sub_menu = MenuItem(url=None, sub_menu=dict(foo=MenuItem(include=False)))

    menu = MyMenu().bind(request=req('GET'))
    assert menu._active is False
    assert menu.sub_menu is not None
    assert menu.sub_menu.home._active is True
    assert menu.sub_menu.artists.regex == '^/artists/'
    assert (
        menu.__html__()
        == '<nav><ul><li><a class="active link" href="/">Home</a></li><li><a class="link" href="/artists/">Artists</a></li></ul></nav>'
    )

    assert (
        repr(menu)
        == """root
    home -> /
    artists -> /artists/"""
    )


def test_set_active():
    class MyMenu(Menu):
        home = MenuItem(url='/')
        artists = MenuItem()
        albums = MenuItem()
        external = MenuItem(url='http://example.com')
        songs = MenuItem()
        with_query = MenuItem(url='/songs/?foo')

    menu = MyMenu().bind(request=req('GET'))

    menu.set_active('/')
    assert menu.sub_menu.home._active is True

    menu.set_active('/songs/')
    assert menu.sub_menu.songs._active is True

    menu.set_active('/songs/?foo')
    assert menu.sub_menu.with_query._active is True

    menu.set_active('/not_in_menu/')
    assert menu.sub_menu.home._active is True


def test_submenu():
    class MyMenu(Menu):
        sub_menu = MenuItem(url=None, sub_menu=dict(bar=MenuItem(), foo=MenuItem(after=0)))

    menu = MyMenu().bind(request=req('GET'))
    assert menu.sub_menu is not None
    assert (
        menu.__html__()
        == '<nav><ul><li>Sub menu<li><a class="link" href="/bar/">Bar</a></li><li><a class="link" href="/foo/">Foo</a></li></li></ul></nav>'
    )


def test_debug_menu():
    html = get_debug_menu().bind(request=req('get')).__html__()
    assert '<li><a class="link" href="/code/">Code</a></li>' in html
    assert '<li><a class="link" href="?/debug_tree">Tree</a></li>' in html
    assert '<li onclick="window.iommi_start_pick()"><a class="link" href="#">Pick</a></li>' in html
    assert '<li><a class="link" href="?_iommi_live_edit">Edit</a></li>' in html


def test_template():
    menu = Menu(template=Template('{{ menu.sub_menu.foo.display_name }}'), sub_menu=dict(foo=MenuItem())).bind(
        request=req('get')
    )
    assert menu.__html__() == 'Foo'


def test_validation():
    class MyMenu(Menu):
        external = MenuItem(url='http://example.com')  # first makes mutation testing happier
        sub_menu1 = MenuItem(
            url='foo',
            sub_menu=dict(bar=MenuItem(), external=MenuItem(url='http://example.com'), foo=MenuItem(url='baz')),
        )
        sub_menu2 = MenuItem(
            url='foo',
            sub_menu=dict(bar=MenuItem(), external=MenuItem(url='http://example.com'), foo=MenuItem(url='baz')),
        )
        sub_menu3 = MenuItem(
            url='bar',
            sub_menu=dict(bar=MenuItem(), external=MenuItem(url='http://example.com'), foo=MenuItem(url='baz')),
        )

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


def test_repr():
    class MyMenu(Menu):
        sub_menu1 = MenuItem(url='foo', sub_menu=dict(bar=MenuItem(), foo=MenuItem(url='baz')))
        sub_menu2 = MenuItem(url='foo', sub_menu=dict(bar=MenuItem(), foo=MenuItem(url='baz')))
        sub_menu3 = MenuItem(url='bar', sub_menu=dict(bar=MenuItem(), foo=MenuItem(url='baz')))

    menu = MyMenu().bind(request=req('get'))
    actual = repr(menu)
    expected = """root
    sub_menu1 -> foo
        bar -> /bar/
        foo -> baz
    sub_menu2 -> foo
        bar -> /bar/
        foo -> baz
    sub_menu3 -> bar
        bar -> /bar/
        foo -> baz"""
    assert actual == expected


def test_submenu_set_active():
    class MyMenu(Menu):
        qwe = MenuItem(url=None, sub_menu=dict(bar=MenuItem(), foo=MenuItem(after=0)))

    menu = MyMenu().bind(request=req('GET'))
    menu.set_active('/foo/')
    assert menu.sub_menu.qwe.sub_menu.foo._active is True


def test_reverse_lazy(settings):
    settings.ROOT_URLCONF = __name__

    class MyMenu(Menu):
        foo = MenuItem(url=reverse_lazy('reverse-lazy-test'))

    menu = MyMenu().bind(request=req('GET'))

    assert menu.sub_menu.foo.url == '/reverse_lazy_test'

    # This shouldn't raise
    str(menu)


def test_active_on_li():
    class MyMenu(Menu):
        qwe = MenuItem(
            url=None,
            sub_menu=dict(
                bar=MenuItem(active_class_on_item=True),
                foo=MenuItem(after=0, active_class_on_item=True),
            ),
        )

    menu = MyMenu().bind(request=req('GET'))
    menu.set_active('/foo/')
    assert menu.sub_menu.qwe.sub_menu.foo._active is True
    assert '<li class="active">' in menu.__html__()
