from textwrap import dedent

import pytest
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
    assert '<li><a class="link" href="?_iommi_code_finder=">Code finder</a></li>' in html
    assert '<li><a class="link" href="?_iommi_live_edit">Edit</a></li>' in html
    assert '<li><a class="link" href="?_iommi_live_edit=style_editor">Edit style</a></li>' in html
    assert '<li><a class="link" href="?_iommi_prof=">Profile</a></li>' in html
    assert '<a class="link" href="#">Profile POST</a></li>' in html
    assert '<li><a class="link" href="?_iommi_sql_trace=">SQL trace</a></li>' in html
    # Templates and Stop editing require specific request state and must be absent by default.
    assert 'Templates' not in html
    assert 'Stop editing' not in html


def test_debug_menu_with_live_edit_active_and_templates_used():
    request = req('get', **{'_iommi_live_edit': ''})
    request.iommi_used_templates = {'foo.html': 1}
    html = get_debug_menu().bind(request=request).__html__()

    assert '<li><a class="link" href="?/debug_templates_used">Templates</a></li>' in html
    assert '<li><a class="link" href="?_iommi_live_edit&amp;_iommi_live_edit_flow=row">Edit vertical</a></li>' in html
    assert '<li><a class="link" href="?_iommi_live_edit=stop">Stop editing</a></li>' in html


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




def test_menu_item_requires_active_class():
    class MyMenu(Menu):
        home = MenuItem(url='/', active_class=None)

    with pytest.raises(AssertionError) as e:
        MyMenu().bind(request=req('GET'))

    assert str(e.value) == 'No active_class provided'


def test_menu_attrs_and_items_container_attrs_are_rendered():
    menu = Menu(
        attrs__class__my_menu=True,
        items_container__attrs__class__my_items=True,
        sub_menu__foo__url='/foo/',
    ).bind(request=req('get'))
    assert (
        menu.__html__()
        == '<nav class="my_menu"><ul class="my_items"><li><a class="link" href="/foo/">Foo</a></li></ul></nav>'
    )


def test_menu_items_container_template():
    menu = Menu(
        items_container__template=Template('items container template'),
        sub_menu__foo__url='/foo/',
    ).bind(request=req('get'))
    assert menu.__html__() == '<nav>items container template</nav>'


def test_menu_items_container_gets_style_from_menu():
    from iommi import Style
    from iommi.style_test_base import test

    style = Style(test, Fragment__attrs__class__from_menu_style=True)
    menu = Menu(iommi_style=style, sub_menu__foo__url='/foo/').bind(request=req('get'))
    assert (
        menu.__html__() == '<nav><ul class="from_menu_style"><li><a class="link" href="/foo/">Foo</a></li></ul></nav>'
    )


def test_validation_ignores_anchor_urls():
    class MyMenu(Menu):
        foo = MenuItem(url='#')
        bar = MenuItem(url='#')

    assert MyMenu().bind(request=req('get')).validate() == {}


def test_set_active_ignores_external_urls():
    class MyMenu(Menu):
        external = MenuItem(url='https://example.com/foo/')

    menu = MyMenu().bind(request=req('get'))
    menu.set_active('/foo/')
    assert menu.sub_menu.external._active is False


def test_repr_three_levels():
    class MyMenu(Menu):
        a = MenuItem(
            url='/a/',
            sub_menu=dict(
                b=MenuItem(
                    url='/b/',
                    sub_menu=dict(c=MenuItem(url='/c/'), d=MenuItem(url='/d/')),
                ),
            ),
        )

    assert repr(MyMenu().bind(request=req('get'))) == dedent('''\
        root
            a -> /a/
                b -> /b/
                    c -> /c/
                    d -> /d/''')


def test_debug_menu_items_are_list_items_in_a_style_without_menu_item_tag():
    # The base style doesn't set a tag for MenuItem, so the debug menu must set it itself
    request = req('get', _iommi_live_edit='')
    request.iommi_used_templates = {'foo.html': 1}
    html = get_debug_menu(iommi_style='base').bind(request=request).__html__()

    for item in [
        '<li><a href="/code/">Code</a></li>',
        '<li><a href="?/debug_templates_used">Templates</a></li>',
        '<li><a href="?/debug_tree">Tree</a></li>',
        '<li onclick="window.iommi_start_pick()"><a href="#">Pick</a></li>',
        '<li><a href="?_iommi_live_edit=&amp;_iommi_code_finder=">Code finder</a></li>',
        '<li><a href="?_iommi_live_edit&amp;_iommi_live_edit_flow=row">Edit vertical</a></li>',
        '<li><a href="?_iommi_live_edit=stop">Stop editing</a></li>',
        '<li><a href="?_iommi_live_edit=style_editor">Edit style</a></li>',
        '<li><a href="?_iommi_live_edit=&amp;_iommi_prof=">Profile</a></li>',
        '<li><a href="?_iommi_live_edit=&amp;_iommi_sql_trace=">SQL trace</a></li>',
    ]:
        assert item in html

    profile_post = html[html.index('<li onclick="\n') : html.index('Profile POST</a></li>')]
    assert 'input.setAttribute(&quot;name&quot;, &quot;_iommi_prof&quot;);' in profile_post
    assert 'form.appendChild(input);' in profile_post


def test_debug_menu_edit_in_row_flow():
    html = get_debug_menu().bind(request=req('get', _iommi_live_edit='', _iommi_live_edit_flow='row')).__html__()
    assert '<li><a class="link" href="?_iommi_live_edit">Edit</a></li>' in html
    assert 'Edit vertical' not in html


def test_debug_menu_without_debug_middlewares(settings):
    settings.MIDDLEWARE = [
        x
        for x in settings.MIDDLEWARE
        if x not in ('iommi.live_edit.Middleware', 'iommi.profiling.Middleware', 'iommi.sql_trace.Middleware')
    ]
    html = get_debug_menu().bind(request=req('get')).__html__()
    assert html == (
        '<nav style="background: white; border: 1px solid black; bottom: -1px; position: fixed; right: -1px; z-index: 100">'
        '<ul style="list-style: none">'
        '<li><a class="link" href="/code/">Code</a></li>'
        '<li><a class="link" href="?/debug_tree">Tree</a></li>'
        '<li onclick="window.iommi_start_pick()"><a class="link" href="#">Pick</a></li>'
        '<li><a class="link" href="?_iommi_code_finder=">Code finder</a></li>'
        '</ul>'
        '</nav>'
    )
