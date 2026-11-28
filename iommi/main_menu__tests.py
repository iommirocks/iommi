from textwrap import dedent

import pytest
from django.conf.urls.i18n import i18n_patterns
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.template import Template
from django.urls import (
    clear_url_caches,
    reverse,
)
from django.utils import translation
from django.utils.translation import gettext_lazy

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
    Style,
    register_style,
    resolve_style,
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
            url=lambda artist, **_: artist.get_absolute_url(),
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
                    url=lambda artist, **_: artist.get_absolute_url(),
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


class UrlConfWithTableFirst:
    urlpatterns = list(reversed(urlpatterns))


url_conf_with_table_first = UrlConfWithTableFirst()


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


class JumpToCodePage(Form):
    field = Field()


def test_menu_view_class_jump_to_code_points_at_class():
    # When a view *class* is mounted on a menu item, the prototype instance is
    # created inside iommi's URL machinery. Its instantiation location must not
    # leak the menu/urls plumbing; the "jump to code" feature should resolve to
    # the view class definition instead.
    import inspect

    from iommi.debug import filename_and_line_num_from_part

    expected_filename = inspect.getsourcefile(JumpToCodePage)
    expected_line = inspect.findsource(JumpToCodePage)[1] + 1

    menu = MainMenu(items=dict(foo=M(view=JumpToCodePage)))

    def iommi_targets(patterns):
        from django.urls import URLPattern, URLResolver
        for p in patterns:
            if isinstance(p, URLResolver):
                yield from iommi_targets(p.url_patterns)
            elif isinstance(p, URLPattern):
                target = getattr(p.callback, '__iommi_target__', None)
                if target is not None:
                    yield target

    (target,) = list(iommi_targets(menu.urlpatterns()))

    filename, line_num = filename_and_line_num_from_part(target)
    assert (filename, line_num) == (expected_filename, expected_line)


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

    request = req('get', url='/table/')
    # In `urlpatterns` the path of `artist`, `<artist_pk>/`, comes first and resolves /table/ too
    request.urlconf = url_conf_with_table_first

    assert (
        inner(request) == ok
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


def test_main_menu_template():
    # Regression test for https://github.com/iommirocks/iommi/issues/708
    menu = MainMenu(
        template=Template('<div>custom main menu template</div>'),
        items=dict(
            foo=M(
                view=fake_view,
            ),
        ),
    ).bind(request=req('get'))

    assert '<div>custom main menu template</div>' in str(menu)


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


def test_lazy_display_name_is_not_resolved_at_declaration_time():
    # `gettext_lazy` is a deferred lookup, not a string: it must stay deferred until
    # render, so it resolves under the language of the request. Normalizing it here
    # (`.replace('_', ' ')`) forces it under whatever language is active when the menu
    # module is imported and freezes that text -- and re-wrapping the result would make
    # the frozen text the msgid, so no other language could ever match it again.
    with translation.override('de'):
        item = M(view=fake_view, display_name=gettext_lazy('Logout'))
        item._set_name('some_name')

    # Nothing for an i18n string extractor to pick up here: the `gettext_lazy` call in
    # the caller's source is what gets extracted.
    assert item._raw_display_name is None

    with translation.override('de'):
        assert str(item.display_name) == 'Abmelden'
    with translation.override('en'):
        assert str(item.display_name) == 'Logout'


def test_plain_display_name_is_still_translated_by_iommi():
    item = M(view=fake_view, display_name='some_name_here')
    item._set_name('ignored')

    assert item._raw_display_name == 'some name here'
    assert str(item.display_name) == 'Some name here'


def test_display_name_falls_back_to_the_item_name():
    item = M(view=fake_view)
    item._set_name('some_name_here')

    assert item._raw_display_name == 'some name here'
    assert str(item.display_name) == 'Some name here'


class UrlConfOfAccessMenu:
    """What `request.urlconf` points at in the access tests below: the menu's own paths, and one path declared beside it."""

    @property
    def urlpatterns(self):
        return access_menu_urlpatterns


access_menu_declaration = MainMenu(
    items=dict(
        # The link carries a query string, as for a list that opens filtered.
        staff_only=M(
            view=fake_view,
            include=lambda user, **_: user.is_staff,
            url='/staff_only/?filter=mine',
            path='staff_only/',
            items=dict(
                child=M(
                    view=fake_view,
                    path='child/',
                    url='/staff_only/child/',
                ),
            ),
            paths=[
                path('extra/', fake_view),
            ],
        ),
        # The link does not go to the item's own path.
        link_elsewhere=M(
            view=fake_view,
            include=lambda user, **_: user.is_staff,
            url='/somewhere/else/',
            path='link_elsewhere/',
            items=dict(
                child=M(
                    view=fake_view,
                    path='child/',
                    url='/link_elsewhere/child/',
                ),
            ),
        ),
        open_to_all=M(
            view=fake_view,
            items=dict(
                staff_child=M(
                    view=fake_view,
                    include=lambda user, **_: user.is_staff,
                    # The link of a child that is computed from something else than the request's path.
                    url=lambda **_: '/open_to_all/some_other_child/',
                    path='staff_child/',
                ),
            ),
        ),
    ),
)

access_menu_urlpatterns = access_menu_declaration.urlpatterns() + [
    path('staff_only/declared_beside_the_menu/', fake_view),
    path('not_in_the_menu/', fake_view),
]
url_conf_of_access_menu = UrlConfOfAccessMenu()


def access_menu_response(request):
    request.urlconf = url_conf_of_access_menu
    return main_menu_middleware(lambda request: 'ok')(request)


@pytest.mark.parametrize(
    'url',
    [
        '/staff_only/',
        '/staff_only/child/',
        '/staff_only/extra/',
        '/staff_only/declared_beside_the_menu/',
        '/link_elsewhere/',
        '/link_elsewhere/child/',
        '/open_to_all/staff_child/',
    ],
)
def test_access_follows_the_resolved_path_and_not_the_link_of_the_item(settings, url):
    settings.IOMMI_MAIN_MENU = 'iommi.main_menu__tests.access_menu_declaration'

    assert access_menu_response(staff_req('get', url=url)) == 'ok'
    assert isinstance(access_menu_response(req('get', url=url)), HttpResponseForbidden)


@pytest.mark.parametrize('url', ['/open_to_all/', '/not_in_the_menu/'])
def test_access_to_what_no_excluded_item_is_above(settings, url):
    settings.IOMMI_MAIN_MENU = 'iommi.main_menu__tests.access_menu_declaration'

    assert access_menu_response(req('get', url=url)) == 'ok'


class UrlConfWithLanguagePrefix:
    def __init__(self, *, prefix_default_language):
        self.urlpatterns = i18n_patterns(*access_menu_urlpatterns, prefix_default_language=prefix_default_language) + [
            path('sv/not_in_the_menu_and_not_translated/', fake_view),
        ]


@pytest.fixture
def language_prefix_settings(settings):
    settings.IOMMI_MAIN_MENU = 'iommi.main_menu__tests.access_menu_declaration'
    settings.LANGUAGES = [('en', 'English'), ('sv', 'Swedish'), ('de', 'German')]
    # The url caches know the language prefixes by the settings
    clear_url_caches()
    yield
    clear_url_caches()


def language_prefix_response(request, *, language, urlconf):
    request.urlconf = urlconf
    # As `LocaleMiddleware` does, before the main menu middleware
    with translation.override(language):
        return main_menu_middleware(lambda request: 'ok')(request)


@pytest.mark.parametrize('path_below_prefix', ['staff_only/', 'staff_only/child/', 'staff_only/declared_beside_the_menu/', 'open_to_all/staff_child/'])
def test_access_with_a_language_prefix(language_prefix_settings, path_below_prefix):
    urlconf = UrlConfWithLanguagePrefix(prefix_default_language=True)

    # Back to the first language at the end: each language keeps its own routes
    for language in ['en', 'sv', 'de', 'en']:
        url = f'/{language}/{path_below_prefix}'
        assert language_prefix_response(staff_req('get', url=url), language=language, urlconf=urlconf) == 'ok'
        assert isinstance(language_prefix_response(req('get', url=url), language=language, urlconf=urlconf), HttpResponseForbidden)


def test_access_with_a_language_prefix_to_what_no_excluded_item_is_above(language_prefix_settings):
    urlconf = UrlConfWithLanguagePrefix(prefix_default_language=True)

    for language in ['en', 'sv']:
        for url in [f'/{language}/open_to_all/', f'/{language}/not_in_the_menu/', '/sv/not_in_the_menu_and_not_translated/']:
            assert language_prefix_response(req('get', url=url), language=language, urlconf=urlconf) == 'ok'


def test_access_without_a_prefix_for_the_default_language(language_prefix_settings):
    urlconf = UrlConfWithLanguagePrefix(prefix_default_language=False)

    # The link of this item is to somewhere else, so only its route tells that the path is below it
    for language, url in [('sv', '/sv/link_elsewhere/'), ('en', '/link_elsewhere/'), ('sv', '/sv/link_elsewhere/child/'), ('en', '/link_elsewhere/child/')]:
        assert language_prefix_response(staff_req('get', url=url), language=language, urlconf=urlconf) == 'ok'
        assert isinstance(language_prefix_response(req('get', url=url), language=language, urlconf=urlconf), HttpResponseForbidden)

    assert language_prefix_response(req('get', url='/open_to_all/'), language='en', urlconf=urlconf) == 'ok'
    assert language_prefix_response(req('get', url='/sv/open_to_all/'), language='sv', urlconf=urlconf) == 'ok'


def test_active_item_of_a_link_with_a_query_string():
    menu = access_menu_declaration.bind(request=staff_req('get', url='/staff_only/'))
    assert menu.active_item.url == '/staff_only/?filter=mine'

    menu = access_menu_declaration.bind(request=staff_req('get', url='/staff_only/child/'))
    assert menu.active_item.url == '/staff_only/child/'


@pytest.mark.django_db
def test_path_decoding_include_denied_by_the_middleware(settings, ozzy, black_sabbath):
    settings.IOMMI_MAIN_MENU = 'iommi.main_menu__tests.menu_declaration'
    settings.ROOT_URLCONF = 'iommi.main_menu__tests'

    def decode_artist(string, **_):
        return Artist.objects.get(pk=string)

    with register_path_decoding(artist_pk=PathDecoder(decode=decode_artist, name='artist')):
        inner = main_menu_middleware(lambda request: 'ok')

        assert inner(req('get', url=f'/table/{black_sabbath.pk}/')) == 'ok'
        assert isinstance(inner(req('get', url=f'/table/{ozzy.pk}/')), HttpResponseForbidden)


def test_path_helper_passes_name_and_kwargs():
    from iommi import Page

    def view_function(request):
        pass  # pragma: no cover

    class MyPage(Page):
        pass

    class HasAsView:
        def as_view(self):
            return view_function

    p = path('a/', view_function, name='a', kwargs={'x': 1})
    assert (p.name, p.default_args, p.callback) == ('a', {'x': 1}, view_function)

    p = path('b/', MyPage, name='b', kwargs={'x': 2})
    assert (str(p.pattern), p.name, p.default_args, p.callback.__name__) == ('b/', 'b', {'x': 2}, 'MyPage.as_view')

    p = path('c/', HasAsView(), name='c', kwargs={'x': 3})
    assert (p.name, p.default_args, p.callback) == ('c', {'x': 3}, view_function)


def test_path_helper_with_django_class_based_view():
    from django.views import View

    class ClassBasedView(View):
        pass

    p = path('d/', ClassBasedView, name='d', kwargs={'x': 4})
    assert (p.name, p.default_args, p.callback.view_class) == ('d', {'x': 4}, ClassBasedView)


def test_urlpatterns_names_kwargs_and_items():
    # The urlpatterns must be built in the test, not at import time, for the code building them to be tested
    menu = MainMenu(
        items=dict(
            foo=M(
                view=fake_view,
                view_kwargs={'x': 1},
                items=dict(bar=M(view=fake_view)),
            ),
            with_url_and_path=M(view=fake_view, url='/somewhere/', path='somewhere/'),
        ),
    )
    foo, with_url_and_path = menu.urlpatterns()
    assert foo.iommi_menu_item is menu.items['foo']
    own, bar = foo.url_patterns
    assert (str(own.pattern), own.name, own.default_args) == ('', 'main_menu.foo', {'x': 1})
    assert bar.iommi_menu_item is menu.items['foo'].items['bar']
    assert [(str(x.pattern), x.name) for x in bar.url_patterns] == [('', 'main_menu.foo.bar')]
    assert str(with_url_and_path.pattern) == 'somewhere/'
    assert [x.name for x in with_url_and_path.url_patterns] == ['main_menu.with_url_and_path']


def test_urlpatterns_require_the_middleware(settings):
    settings.MIDDLEWARE = [x for x in settings.MIDDLEWARE if x != 'iommi.main_menu.main_menu_middleware']
    with pytest.raises(AssertionError) as e:
        MainMenu(items=dict(foo=M(view=fake_view))).urlpatterns()

    assert str(e.value) == (
        'To use the iommi main menu, you must add `iommi.main_menu.main_menu_middleware` to the MIDDLEWARE list.'
    )


def test_join_routes():
    from iommi.main_menu import join_routes

    assert join_routes('', '^foo/') == '^foo/'
    assert join_routes('a/', '^foo/') == 'a/foo/'
    assert join_routes('a/', 'foo/') == 'a/foo/'


@pytest.mark.parametrize(
    'route, item_route, expected',
    [
        ('users/', 'users/', True),
        ('users/1/', 'users/', True),
        ('users', 'users', True),
        ('users/1', 'users', True),
        ('users_archive/', 'users', False),
        ('other/', 'users/', False),
        ('anything/', '', True),
    ],
)
def test_is_route_below(route, item_route, expected):
    from iommi.main_menu import is_route_below

    assert is_route_below(route, item_route=item_route) is expected


def test_menu_routes():
    from iommi.main_menu import (
        MenuRoutes,
        get_menu_routes,
    )

    staff_only = access_menu_declaration.items['staff_only']
    child = staff_only.items['child']
    routes = MenuRoutes(access_menu_declaration.urlpatterns() + [path('staff_only/beside/', fake_view)])

    assert routes.item_by_declared_route['staff_only/'] is staff_only
    # declared in the paths of the item
    assert routes.item_by_declared_route['staff_only/extra/'] is staff_only
    assert routes.item_by_declared_route['staff_only/child/'] is child
    assert routes.find_item('staff_only/extra/') is staff_only
    # below an item, but not declared in it
    assert routes.find_item('staff_only/beside/') is staff_only
    assert routes.find_item('staff_only/child/whatever/') is child
    assert routes.find_item('not_in_the_menu/') is None

    assert get_menu_routes(url_conf_of_access_menu) is get_menu_routes(url_conf_of_access_menu)


def test_main_menu_template_and_attrs_from_style(settings):
    settings.IOMMI_DEFAULT_STYLE = 'test_main_menu_style'
    style = Style(
        base,
        MainMenu__template=Template('{{ main_menu.attrs }}'),
        BoundM__template=Template('item'),
        BoundM__attrs__class__from_style=True,
    )
    with register_style('test_main_menu_style', style):
        menu = MainMenu(
            attrs__class__mine=True,
            items=dict(foo=M(view=fake_view, attrs__class__own=True)),
        ).bind(request=req('get'))
        assert str(menu) == ' class="main_menu mine"'
        foo = menu.items['foo']
        assert foo.__html__() == 'item'
        assert foo.attrs['class'] == {'own': True, 'from_style': True}


def test_evaluated_attrs_render_and_dynamic_items():
    menu = MainMenu(
        attrs__class__staff=lambda user, **_: user.is_staff,
        items=dict(
            foo=M(
                view=fake_view,
                attrs__class__staff=lambda user, **_: user.is_staff,
                render=lambda user, **_: user.is_staff,
                items__call_target=lambda user, **_: dict(
                    dynamic=M(view=EXTERNAL, url='/dynamic/', display_name=f'staff {user.is_staff}'),
                ),
            ),
        ),
    )
    staff_menu = menu.bind(request=staff_req('get'))
    assert staff_menu.attrs['class']['staff'] is True
    staff_foo = staff_menu.items['foo']
    assert staff_foo.attrs['class']['staff'] is True
    assert staff_foo.__html__() != ''
    assert staff_foo.items['dynamic'].display_name == 'staff True'

    menu = menu.bind(request=req('get'))
    assert menu.attrs['class']['staff'] is False
    foo = menu.items['foo']
    assert foo.attrs['class']['staff'] is False
    assert foo.__html__() == ''
    assert foo.items['dynamic'].display_name == 'staff False'


def test_evaluate_parameters():
    request = staff_req('get', url='/foo/')
    request.iommi_view_params = dict(artist='the artist')
    menu = MainMenu(
        extra_evaluated__menu_params=lambda request, user, main_menu, artist, **_: (
            request.path,
            user.is_staff,
            main_menu,
            artist,
        ),
        items=dict(
            foo=M(
                view=fake_view,
                extra_evaluated__item_params=lambda request, user, item, main_menu, artist, **_: (
                    request.path,
                    user.is_staff,
                    item,
                    main_menu,
                    artist,
                ),
            ),
        ),
    ).bind(request=request)
    assert menu.extra_evaluated.menu_params == ('/foo/', True, menu, 'the artist')
    foo = menu.items['foo']
    assert foo.extra_evaluated.item_params == ('/foo/', True, foo, menu, 'the artist')


def test_item_tag_and_details_tags():
    menu = menu_declaration.bind(request=staff_req('get', url='/table/'))
    foo = menu.items['foo']
    assert foo.tag == 'li'
    assert str(foo.iommi_open_tag()).startswith('<li')
    assert not foo.is_active()
    assert foo.iommi_open_details_tag() == '<details>'
    assert foo.iommi_close_details_tag() == '</details>'

    menu = menu_declaration.bind(request=staff_req('get', url='/foo/'))
    assert menu.items['foo'].iommi_open_details_tag() == '<details open>'


def test_active_item_is_the_best_match():
    menu = MainMenu(
        items=dict(
            root=M(view=fake_view, url='/', path=''),
            deep=M(view=fake_view, url='/x/y/', path='x/y/'),
            shallow=M(view=fake_view, url='/x/', path='x/'),
        ),
    )
    assert menu.bind(request=staff_req('get', url='/')).active_item.m.name == 'root'
    assert menu.bind(request=staff_req('get', url='/x/y/')).active_item.m.name == 'deep'
    assert menu.bind(request=staff_req('get', url='/x/')).active_item.m.name == 'shallow'


def test_check_access_to_resolved_path_skips():
    from types import SimpleNamespace

    def check(resolver_match):
        request = req('get', url='/staff_only/')
        request.urlconf = url_conf_of_access_menu
        menu = access_menu_declaration.bind(request=request)
        request.resolver_match = resolver_match
        menu.check_access_to_resolved_path()

    with pytest.raises(PermissionDenied):
        check(SimpleNamespace(route='staff_only/', app_name=''))
    # django-ninja paths are not checked
    check(SimpleNamespace(route='staff_only/', app_name='ninja'))
    check(SimpleNamespace(route=None, app_name=''))
    check(None)


def test_check_access_checks_all_active_items():
    menu = MainMenu(
        items=dict(
            first=M(view=fake_view),
            second=M(
                view=fake_view,
                items=dict(
                    not_active=M(view=fake_view),
                    staff=M(view=fake_view, include=lambda user, **_: user.is_staff),
                ),
            ),
        ),
    )
    menu.bind(request=staff_req('get', url='/second/staff/')).check_access()
    bound = menu.bind(request=req('get', url='/second/staff/'))
    assert bound.active_item.m.name == 'staff'
    with pytest.raises(PermissionDenied):
        bound.check_access()


def test_menu_routes_with_a_root_item():
    from iommi.main_menu import MenuRoutes

    menu = MainMenu(
        items=dict(
            root=M(view=fake_view, url='/', path=''),
            x=M(view=fake_view, url='/x/', path='x/'),
        ),
    )
    routes = MenuRoutes(menu.urlpatterns())
    assert routes.find_item('other/') is menu.items['root']
    assert routes.find_item('x/y/') is menu.items['x']


def test_main_menu_with_a_style_without_main_menu_config(settings):
    settings.IOMMI_DEFAULT_STYLE = 'test_empty_main_menu_style'
    with register_style('test_empty_main_menu_style', Style()):
        menu = MainMenu(items=dict(foo=M(view=fake_view))).bind(request=req('get'))
        assert menu.template == 'iommi/main_menu/menu.html'
        assert menu.assets == {}
        assert menu.items['foo'].template == 'iommi/main_menu/menu_item.html'


def test_external_url_is_never_the_active_item():
    menu = MainMenu(
        items=dict(
            external=M(view=EXTERNAL, url='https://example.com/x/'),
        ),
    )
    assert menu.bind(request=staff_req('get', url='/x/')).active_item is None


def test_check_access_to_resolved_path_without_resolver_match():
    request = req('get', url='/staff_only/')
    menu = access_menu_declaration.bind(request=request)
    del request.resolver_match
    menu.check_access_to_resolved_path()
