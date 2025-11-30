from textwrap import dedent

import pytest
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.template import Template
from django.urls import reverse

from docs.models import Artist
from iommi import (
    Asset,
    Field,
    Form,
    Table,
)
from iommi.main_menu import (
    EXTERNAL,
    M,
    MainMenu,
    main_menu_middleware,
    path,
)
from iommi.path import (
    PathDecoder,
    register_path_decoding,
)
from iommi.style import (
    register_style,
    resolve_style,
    Style,
)
from iommi.style_base import base
from tests.helpers import (
    req,
    staff_req,
    verify_html,
)


def fake_view():
    pass  # pragma: no cover


def artist_include(artist: Artist) -> bool:
    """
    See :func:`test_path_decoding_include_denied`
    """
    included: bool = artist.name == "Black Sabbath"
    return included


menu_declaration = MainMenu(
    items=dict(
        foo=M(
            icon='edit',
            view=fake_view,
            items=dict(
                bar=M(
                    view=fake_view,
                    include=lambda user, **_: user.is_staff,
                    open=lambda **_: True,
                    items=dict(
                        baz=M(
                            view=fake_view,
                            attrs__class__baz=True,
                            paths=[
                                path('quux/', [
                                    path('', fake_view, name='quux'),
                                ])
                            ]
                        ),
                    ),
                ),
            ),
        ),
        artist=M(
            params={'artist'},
            path='<artist_pk>/',
            view=Form.edit(
                auto__model=Artist,
                instance=lambda artist, **_: artist,
            ),
        ),
        external=M(
            view=EXTERNAL,
            url='https://example.com',
        ),
        table=M(
            view=Table(auto__model=Artist),
            items=dict(
                detail=M(
                    include=lambda artist, **_: artist_include(artist),
                    params={'artist'},
                    path='<artist_pk>/',
                    view=Form(
                        auto__model=Artist,
                        instance=lambda artist, **_: artist,
                    ),
                ),
            ),
        ),
    ),
)

urlpatterns = menu_declaration.urlpatterns()


def test_menu_match():
    menu = menu_declaration.bind(request=staff_req('get', url='/foo/bar/baz/'))
    assert menu.active_item.url == '/foo/bar/baz/'

    menu = menu_declaration.bind(request=staff_req('get', url='/foo/bar/does_not_exist/'))
    assert menu.active_item.url == '/foo/bar/'


def test_urlpatterns():
    sitemap = []

    def generate_sitemap(urlpatterns, indent=0):
        for p in urlpatterns:
            sitemap.append('     ' * indent + (str(p.pattern) or "''") + ' - > ' + str(p.callback.__name__ if p.callback else None))
            if hasattr(p, 'url_patterns'):
                generate_sitemap(p.url_patterns, indent + 1)

    generate_sitemap(menu_declaration.urlpatterns())

    sitemap = '\n'.join(sitemap)
    print(sitemap)
    assert 'external/' not in sitemap
    assert sitemap == dedent('''
        foo/ - > None
             '' - > fake_view
             bar/ - > None
                  '' - > fake_view
                  baz/ - > None
                       '' - > fake_view
                       quux/ - > None
                            '' - > fake_view
        <artist_pk>/ - > None
             '' - > Form.as_view
        table/ - > None
             '' - > Table.as_view
             <artist_pk>/ - > None
                  '' - > Form.as_view
        ''').strip()


def test_automatic_display_name():
    menu = menu_declaration.bind(request=staff_req('get', url='/foo/bar/baz/'))
    assert menu.active_item.display_name == 'Baz'


def test_item_rendering():
    menu = menu_declaration.bind(request=staff_req('get', url='/foo/bar/baz/'))

    verify_html(
        actual_html=str(menu.active_item),
        expected_html='''
            <li class="baz is_active">        
                <a href="/foo/bar/baz/" title="Baz" ><span>Baz</span></a>
            </li>
        ''',
    )


def test_rendering():
    assert resolve_style(None).name == 'test'

    menu = menu_declaration.bind(request=staff_req('get', url='/foo/bar/baz/'))
    verify_html(
        actual_html=str(menu),
        # language=html
        expected_html='''
                      <div class="main_menu">
                          <nav>
                              <a href="/" id="menu-logo">
                                  <div class="iommi_logo_menu">
                                  </div>
                              </a>
                              <ul>
                                  <li class="is_active">
                                      <details open>
                                          <summary>
                                              <div class="menu_open_close"></div>
                                              <a href="/foo/" title="Foo"><i class="fa fa-edit"></i><span>Foo</span></a>
                                          </summary>

                                          <ul>
                                              <li class="is_active">
                                                  <details open>
                                                      <summary>
                                                          <div class="menu_open_close"></div>
                                                          <a href="/foo/bar/" title="Bar"><span>Bar</span></a>
                                                      </summary>
                                                      <ul>
                                                          <li class="baz is_active">
                                                              <a href="/foo/bar/baz/" title="Baz"><span>Baz</span></a>
                                                          </li>
                                                      </ul>
                                                  </details>
                                              </li>
                                          </ul>
                                      </details>
                                  </li>
                                  <li>
                                      <a title="External" href="https://example.com" target=\'"blank"\'>
                                <span>
                                    External
                                    <i class="fa fa-external-link">
                                    </i>
                                </span>
                                      </a>
                                  </li>
                                  <li>
                                      <a href="/table/" title="Table">
                                          <span>
                                              Table
                                          </span>
                                      </a>
                                  </li>
                              </ul>
                          </nav>
                      </div>
                      ''',
    )


def test_access(settings):
    settings.IOMMI_MAIN_MENU = 'iommi.main_menu__tests.menu_declaration'
    settings.ROOT_URLCONF = 'iommi.main_menu__tests'

    ok = object()
    inner = main_menu_middleware(lambda request: ok)

    assert inner(staff_req('get', url='/foo/')) == ok
    assert inner(staff_req('get', url='/foo/bar/')) == ok
    assert inner(staff_req('get', url='/foo/bar/baz/')) == ok
    assert inner(staff_req('get', url='/foo/bar/baz/quux/')) == ok

    # Access denied for non-staff
    assert isinstance(inner(req('get', url='/foo/bar/')), HttpResponseForbidden)
    assert isinstance(inner(req('get', url='/foo/bar/baz/')), HttpResponseForbidden)
    assert isinstance(inner(req('get', url='/foo/bar/baz/quux/')), HttpResponseForbidden)


def test_error_on_external_with_subitem():
    with pytest.raises(AssertionError):
        MainMenu(
            items=dict(
                foo=M(
                    view=EXTERNAL,
                    items=dict(
                        bar=M(
                            view=EXTERNAL,
                        )
                    )
                )
            )
        )


def test_path_type_handling():
    class MyForm(Form):
        field = Field()

    p = path('', MyForm)
    assert p.callback(req('get'))


def test_reprs():
    assert repr(menu_declaration) == '<MainMenu>'
    assert repr(menu_declaration.items['foo']) == '<M foo>'
    menu = menu_declaration.bind(request=req('get'))
    assert repr(menu) == '<BoundMainMenu>'
    assert repr(menu.items['foo']) == '<BoundM foo>'


@pytest.mark.django_db
def test_path_decoding(settings, black_sabbath):
    settings.IOMMI_MAIN_MENU = 'iommi.main_menu__tests.menu_declaration'
    settings.ROOT_URLCONF = 'iommi.main_menu__tests'

    def decode_artist(string, **_):
        return Artist.objects.get(pk=string)

    with register_path_decoding(artist_pk=PathDecoder(decode=decode_artist, name='artist')):
        ok = object()
        inner = main_menu_middleware(lambda request: ok)

        assert inner(staff_req('get', url=f'/{black_sabbath.pk}/')) == ok

    # Path decoder raises PermissionDenied
    def decode_artist_permission_denied(**_):
        raise PermissionDenied()

    with register_path_decoding(artist_pk=PathDecoder(decode=decode_artist_permission_denied, name='artist')):
        ok = object()
        inner = main_menu_middleware(lambda request: ok)

        result = inner(staff_req('get', url=f'/{black_sabbath.pk}/'))
        assert isinstance(result, HttpResponseForbidden)


def test_path_decoding_include_parent(settings):
    settings.IOMMI_MAIN_MENU = 'iommi.main_menu__tests.menu_declaration'
    settings.ROOT_URLCONF = 'iommi.main_menu__tests'

    ok = object()
    inner = main_menu_middleware(lambda request: ok)

    assert (
        inner(req('get', url='/table/')) == ok
    ), "Could not access M containing items with `params` and `include` functions that use them."


@pytest.mark.django_db
def test_path_decoding_include_permitted(settings, black_sabbath):
    settings.IOMMI_MAIN_MENU = 'iommi.main_menu__tests.menu_declaration'
    settings.ROOT_URLCONF = 'iommi.main_menu__tests'

    def decode_artist(string, **_):
        return Artist.objects.get(pk=string)

    with register_path_decoding(artist_pk=PathDecoder(decode=decode_artist, name='artist')):
        ok = object()
        inner = main_menu_middleware(lambda request: ok)

        assert (
            inner(req('get', url=f'/table/{black_sabbath.pk}/')) == ok
        ), "Could not access M with `params`, whose `include` uses them to allow access."


@pytest.mark.django_db
def test_path_decoding_include_denied(settings, ozzy):
    settings.IOMMI_MAIN_MENU = 'iommi.main_menu__tests.menu_declaration'
    settings.ROOT_URLCONF = 'iommi.main_menu__tests'

    def decode_artist(string, **_):
        return Artist.objects.get(pk=string)

    with register_path_decoding(artist_pk=PathDecoder(decode=decode_artist, name='artist')):
        menu = menu_declaration.bind(request=req('get', url=f'/table/{ozzy.pk}/'))
        assert (
                menu.active_item.url == "/table/"
        ), "Not forbidden to access M with `params`, whose `include` uses them to deny access."


def test_m_template():
    menu = MainMenu(
        items=dict(
            foo=M(
                template=Template('<div>test</div>'),
                view=fake_view,
            ),
        ),
    ).bind(request=req('get'))

    assert '<div>test</div>' in str(menu)


def test_m_url():
    menu = MainMenu(
        items=dict(
            foo=M(
                view=EXTERNAL,
                url='https://example.com',
            ),
        ),
    ).bind(request=req('get'))

    assert 'https://example.com' in str(menu)


def test_m_url_error_case():
    with pytest.raises(AssertionError) as e:
        MainMenu(
            items=dict(
                foo=M(
                    url='https://example.com',
                    view=EXTERNAL,
                    items=dict(
                        foo=M(view=fake_view),
                    )
                ),
            ),
        ).urlpatterns()

    assert str(e.value) == "External links can't have subitems"


def test_m_extra():
    menu = MainMenu(
        items=dict(
            foo=M(
                view=EXTERNAL,
                url=lambda item, **_: item.extra.url,
                extra__url='https://example.com',
            ),
        ),
    ).bind(request=req('get'))

    assert 'https://example.com' in str(menu)


def test_m_extra_evaluated():
    menu = MainMenu(
        items=dict(
            foo=M(
                view=EXTERNAL,
                url=lambda item, **_: item.extra_evaluated.url,
                extra_evaluated__url=lambda **_: 'https://example.com',
            ),
        ),
    ).bind(request=req('get'))

    assert 'https://example.com' in str(menu)


def test_main_menu_extra():
    menu = MainMenu(
        extra__url='https://example.com',
        items=dict(
            foo=M(
                view=EXTERNAL,
                url=lambda main_menu, **_: main_menu.extra.url,
            ),
        ),
    ).bind(request=req('get'))

    assert 'https://example.com' in str(menu)


def test_main_menu_extra_evaluated():
    menu = MainMenu(
        extra_evaluated__url=lambda **_: 'https://example.com',
        items=dict(
            foo=M(
                view=EXTERNAL,
                url=lambda main_menu, **_: main_menu.extra_evaluated.url,
            ),
        ),
    ).bind(request=req('get'))

    assert 'https://example.com' in str(menu)


def test_reverse_name(settings):
    settings.DEBUG = True
    settings.IOMMI_MAIN_MENU = 'iommi.main_menu__tests.menu_declaration'
    settings.ROOT_URLCONF = 'iommi.main_menu__tests'

    assert reverse('main_menu.foo.bar.baz') == '/foo/bar/baz/'
    assert reverse('quux') == '/foo/bar/baz/quux/'


def test_styling_1(settings):
    settings.IOMMI_DEFAULT_STYLE = 'test_main_menu_style'
    test_main_menu_style = Style(
        base,
        MainMenu__assets = dict(
            iommi_main_menu_css__include=False,
        ),
    )
    assert isinstance(test_main_menu_style.resolve(MainMenu())[0]['assets']['iommi_main_menu_css'], Asset)
    with register_style('test_main_menu_style', test_main_menu_style):
        MainMenu().bind(request=req('get'))


def test_styling_2(settings):
    settings.IOMMI_DEFAULT_STYLE = 'test_main_menu_style'
    test_main_menu_style = Style(
        base,
        MainMenu=dict(
            attrs__class=dict(main_menu=False),
            assets=dict(
                iommi_main_menu_css__include=False,
            ),
        ),
    )
    assert isinstance(test_main_menu_style.resolve(MainMenu())[0]['assets']['iommi_main_menu_css'], Asset)
    with register_style('test_main_menu_style', test_main_menu_style):
        MainMenu().bind(request=req('get'))


def test_styling_3(settings):
    settings.IOMMI_DEFAULT_STYLE = 'test_main_menu_style'
    test_main_menu_style = Style(
        base,
        MainMenu__assets__iommi_main_menu_css__include=False,
    )
    assert isinstance(test_main_menu_style.resolve(MainMenu())[0]['assets']['iommi_main_menu_css'], Asset)
    with register_style('test_main_menu_style', test_main_menu_style):
        MainMenu().bind(request=req('get'))


def test_styling_4(settings):
    settings.IOMMI_DEFAULT_STYLE = 'test_main_menu_style'
    test_main_menu_style = Style(
        base,
        MainMenu__attrs__class__foo=True,
    )
    assert isinstance(test_main_menu_style.resolve(MainMenu())[0]['assets']['iommi_main_menu_css'], Asset)
    with register_style('test_main_menu_style', test_main_menu_style):
        MainMenu().bind(request=req('get'))


def test_styling_5(settings):
    settings.IOMMI_DEFAULT_STYLE = 'test_main_menu_style'
    test_main_menu_style = Style(
        base,
        MainMenu__assets__iommi_main_menu_css=None,
    )
    assert test_main_menu_style.resolve(MainMenu())[0]['assets']['iommi_main_menu_css'] is None
    with register_style('test_main_menu_style', test_main_menu_style):
        MainMenu().bind(request=req('get'))


def test_styling_6(settings):
    settings.IOMMI_DEFAULT_STYLE = 'test_main_menu_style'
    test_main_menu_style = Style(
        base,
        MainMenu=dict(
            attrs__class=dict(main_menu=False),
            assets=dict(
                iommi_main_menu_css=None,
            ),
        ),
    )
    assert test_main_menu_style.resolve(MainMenu())[0]['assets']['iommi_main_menu_css'] is None
    with register_style('test_main_menu_style', test_main_menu_style):
        MainMenu().bind(request=req('get'))
