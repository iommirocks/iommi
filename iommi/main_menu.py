from functools import cached_property
from pathlib import PurePosixPath
from urllib.parse import urlparse

import django.utils.decorators
from django.conf import settings
from django.conf.urls import handler403
from django.core.exceptions import PermissionDenied
from django.urls import (
    URLResolver,
    get_resolver,
    include,
)
from django.urls import (
    path as orig_path,
)
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy

from iommi import (
    MISSING,
)
from iommi._web_compat import (
    format_html,
    render_template,
)
from iommi.attrs import (
    evaluate_attrs,
    render_attrs,
)
from iommi.base import capitalize
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    Namespace,
)
from iommi.evaluate import (
    evaluate_as_needed,
    evaluate_strict,
)
from iommi.fragment import Tag
from iommi.path import decode_path_components
from iommi.struct import Struct
from iommi.style import resolve_style

EXTERNAL = object()


class NoTranslateString(str):
    pass


def path(path, view_or_list, name=None, kwargs=None):
    if isinstance(view_or_list, list):
        assert kwargs is None
        return orig_path(path, include(view_or_list), name=name)
    elif isinstance(view_or_list, type):
        return orig_path(path, view_or_list().as_view(), name=name, kwargs=kwargs)
    else:
        try:
            return orig_path(path, view_or_list.as_view(), name=name, kwargs=kwargs)
        except AttributeError:
            return orig_path(path, view_or_list, name=name, kwargs=kwargs)


def join_routes(route, sub_route):
    """Join the routes of a resolver and of what it includes, as Django does for `ResolverMatch.route`."""
    if not route:
        return sub_route
    return route + sub_route.removeprefix('^')


def is_route_below(route, *, item_route):
    """True if `route` is the route of the item, or of something below it in the URL hierarchy."""
    if not route.startswith(item_route):
        return False
    rest_of_route = route[len(item_route):]
    # `users` is not above `users_archive/`
    return not item_route or item_route.endswith('/') or not rest_of_route or rest_of_route.startswith('/')


class MenuRoutes:
    """Where the items of the main menus are in a URL configuration: the route of each item, and for each path that is declared in a menu the item it belongs to."""

    def __init__(self, url_patterns):
        self.item_by_declared_route = {}
        self.routes_and_items = []
        self._collect(url_patterns, route='', item=None)

    def _collect(self, url_patterns, *, route, item):
        for url_pattern in url_patterns:
            pattern_route = join_routes(route, str(url_pattern.pattern))
            pattern_item = getattr(url_pattern, 'iommi_menu_item', item)
            if pattern_item is not item:
                self.routes_and_items.append((pattern_route, pattern_item))
            if isinstance(url_pattern, URLResolver):
                self._collect(url_pattern.url_patterns, route=pattern_route, item=pattern_item)
            elif pattern_item is not None:
                # Django resolves the first of two paths with the same route
                self.item_by_declared_route.setdefault(pattern_route, pattern_item)

    def find_item(self, route):
        """The item that the path with this route is declared in, or else the deepest item it is below."""
        if route in self.item_by_declared_route:
            return self.item_by_declared_route[route]

        deepest_route, deepest_item = '', None
        for item_route, item in self.routes_and_items:
            if is_route_below(route, item_route=item_route) and (deepest_item is None or len(item_route) > len(deepest_route)):
                deepest_route, deepest_item = item_route, item
        return deepest_item


def get_menu_routes(urlconf):
    resolver = get_resolver(urlconf)
    # Kept on the resolver, which Django caches per URL configuration and drops when the URL configuration changes
    if not hasattr(resolver, 'iommi_menu_routes'):
        resolver.iommi_menu_routes = MenuRoutes(resolver.url_patterns)
    return resolver.iommi_menu_routes


def path_of_item(item):
    """The paths of an item, as its parent includes them: marked with the item, which is how the access check finds the item of a resolved path."""
    url_resolver = path(item.path, item.urlpatterns(), name=item.name)
    url_resolver.iommi_menu_item = item
    return url_resolver


class MainMenu:
    # language=rst
    """
    See the :ref:`MainMenu <mainmenu>` docs and the :ref:`MainMenu cookbook <cookbook-main-menu>`.
    """

    @dispatch(
        items=EMPTY,
        attrs__style=EMPTY,
        attrs__class=EMPTY,
        extra=EMPTY,
        extra_evaluated=EMPTY,
    )
    def __init__(self, *, items=None, attrs, template=MISSING, paths=None, extra, extra_evaluated):
        self.items = items
        self.attrs = attrs
        self.template = template
        self.paths = paths or []
        self.extra = extra
        self.extra_evaluated = extra_evaluated
        for name, c in self.items.items():
            c.parent = self
            c._set_name(name)

    def urlpatterns(self):
        if 'iommi.main_menu.main_menu_middleware' not in settings.MIDDLEWARE:
            # This is an explicit raise instead of an `assert` because I'm paranoid of people running Python in optimized mode with skipped asserts.
            raise AssertionError('To use the iommi main menu, you must add `iommi.main_menu.main_menu_middleware` to the MIDDLEWARE list.')

        return [
            path_of_item(x)
            for x in self.items.values()
            if x.view is not EXTERNAL
        ] + self.paths

    def bind(self, request):
        style = resolve_style(None)
        conf = Namespace(*style.resolve(self))

        style_template = conf.pop('template', 'iommi/main_menu/menu.html')
        if self.template is MISSING:
            self.template = style_template

        assets = {
            k: v.bind(request=request)
            for k, v in conf.pop('assets', {}).items()
            if v
        }

        attrs = Namespace(self.attrs, conf.pop('attrs', {}))

        assert not conf, f'Unknown configuration {conf} for `MainMenu`'

        return BoundMainMenu(
            self,
            request,
            attrs=attrs,
            template=self.template,
            assets=assets,
        )

    def _name_path(self):
        return 'main_menu'

    def __repr__(self):
        return '<MainMenu>'


class BoundMainMenu:
    def __init__(self, main_menu, request, attrs, template, assets):
        self.main_menu = main_menu
        self.request = request
        self.attrs = attrs
        self.template = template
        self.paths = main_menu.paths
        self.assets = assets
        self._own_evaluate_parameters = self.own_evaluate_parameters()

        self.attrs = evaluate_attrs(self, **self._own_evaluate_parameters)

        self.raw_items = {
            k: v.bind(request=request, root=self)
            for k, v in self.main_menu.items.items()
        }
        self.items = {k: v for k, v in self.raw_items.items() if v.include}

        # Set active_item
        self.url = None
        best_match = None
        path_parts = PurePosixPath(urlparse(self.request.get_full_path()).path).parts

        def url_likeness(x):
            if x is None:
                return 0
            a = PurePosixPath(urlparse(x.url).path).parts
            b = path_parts
            # if a starts with b
            if a == b[:len(a)]:
                return len(a)
            return 0

        def foo(x):
            nonlocal best_match

            if not x.params_are_satisfied():
                return

            if x.url and '://' not in x.url and url_likeness(best_match) < url_likeness(x):
                best_match = x

            for sub_item in x.raw_items.values():
                foo(sub_item)

        foo(self)
        self.active_item = best_match

    def check_access(self):
        self.check_access_to_resolved_path()

        for item in self.raw_items.values():
            if not item.is_active():
                continue
            item.check_access()

    def check_access_to_resolved_path(self):
        """Refuse a path that is declared in, or is below, an item the user does not have: that item or one above it.

        This goes by the route Django resolved, where `active_item` goes by the links of the items. A link is what
        the user clicks on, and can differ from the path of its item: a query string, or the URL of another object.
        """
        resolver_match = getattr(self.request, 'resolver_match', None)
        # The parameters of a django-ninja path are not decoded, so the items above it can't be evaluated
        if resolver_match is None or resolver_match.route is None or resolver_match.app_name == 'ninja':
            return

        item_or_main_menu = get_menu_routes(getattr(self.request, 'urlconf', None)).find_item(resolver_match.route)
        items_from_the_top = []
        while isinstance(item_or_main_menu, M):
            items_from_the_top.insert(0, item_or_main_menu)
            item_or_main_menu = item_or_main_menu.parent
        # Not below an item, or below an item of another main menu
        if item_or_main_menu is not self.main_menu:
            return

        bound_items = self.raw_items
        for item in items_from_the_top:
            bound_item = next((x for x in bound_items.values() if x.m is item), None)
            # An item is only bound if the user has every item above it
            if bound_item is None or not bound_item.include:
                raise PermissionDenied()
            bound_items = bound_item.raw_items

    def params_are_satisfied(self):
        return True

    def __str__(self):
        return self.__html__()

    def __html__(self):
        return render_template(self.request, self.template, self._own_evaluate_parameters)

    def render_items(self):
        return format_html('{}' * len(self.items), *[x.__html__() for x in self.items.values()])

    @property
    def extra(self):
        return self.main_menu.extra

    @cached_property
    def extra_evaluated(self):
        return Struct(evaluate_as_needed(self.main_menu.extra_evaluated or {}, self._own_evaluate_parameters))

    def __repr__(self):
        return '<BoundMainMenu>'

    def own_evaluate_parameters(self):
        request = self.request
        return {
            'request': request,
            'user': getattr(request, 'user', None) if request else None,
            'main_menu': self,
            **getattr(request, 'iommi_view_params', {}),
        }


class M:
    # language=rst
    """
    See the :ref:`MainMenu <mainmenu>` docs and the :ref:`MainMenu cookbook <cookbook-main-menu>`.
    """

    @dispatch(
        items=EMPTY,
        attrs__style=EMPTY,
        attrs__class=EMPTY,
        extra=EMPTY,
        extra_evaluated=EMPTY,
    )
    def __init__(self, *, icon=None, view=None, view_kwargs=None, path=MISSING, url=None, open=None, params=None, display_name=None, items=None, include=None, attrs, template=MISSING, paths=None, extra, extra_evaluated, render=True):

        assert view is not None or view is EXTERNAL, f'Items should either have a view function specified, or supply EXTERNAL to mark the item as having an external URL and thus not needing access control. Got {view!r}'

        self.name = None
        self.icon = icon
        self.render = render
        self.url = url
        assert url is None or isinstance(url, str) or callable(url)
        self.path = path
        assert path is MISSING or path is None or isinstance(path, str), f'`path` must be `MISSING`, `None` or a `str`. Got {type(self.path)} ({self.path}).'
        self.paths = paths or []
        assert isinstance(self.paths, list), f'`paths` must be of type list. Got type {type(self.paths)} ({self.paths}).'

        if path is not MISSING:
            assert url, "If you configure `path` you must also configure `url`. `path` is the Django path mapping and `url` is how to make a link the user can click on. You probably want the url to be an absolute url (starting with a /)."

        self.view = view
        self.view_kwargs = view_kwargs
        self.include = include
        self.display_name = display_name
        self._raw_display_name = None  # We need programmatic access to this from okrand for i18n
        self.dynamic_items = None
        self.items = {}

        if isinstance(items, Namespace) and 'call_target' in items:
            self.dynamic_items = items.pop('call_target')
            assert not items, "You can't mix dynamic items and static items"
        else:
            self.items = {
                k: M(**v) if isinstance(v, dict) else v
                for k, v in items.items()
            }

        self.parent = None
        self.params = params
        self.open = open
        self.attrs = attrs
        self.template = template
        self.extra = extra
        self.extra_evaluated = extra_evaluated
        if params is not None:
            assert isinstance(params, set), '`params` must be a `set`'
            assert self.path, 'if `params` is set, `path` must also be set'
        for name, c in self.items.items():
            c.parent = self
            c._set_name(name)

        if isinstance(self.url, str) and self.path is MISSING:
            assert not self.items and not self.paths, "External links can't have subitems"

        if self.view is EXTERNAL:
            assert not self.items, 'External views are not allowed to have subitems. Use a redirect view instead.'

    def __repr__(self):
        return f"<M {self.name}>"

    def _set_name(self, name):
        self.name = name
        # A `Promise` (`gettext_lazy` and friends) is a deferred lookup that must stay
        # deferred until render, so it resolves under the language of the request.
        if not callable(self.display_name) and not isinstance(self.display_name, NoTranslateString | Promise):
            self._raw_display_name = (self.display_name or name).replace('_', ' ')
            self.display_name = capitalize(gettext_lazy(self._raw_display_name))
        if self.path is MISSING:
            self.path = self.name + '/'

    def urlpatterns(self):
        if isinstance(self.url, str) and self.path is MISSING:
            return []

        if self.view is EXTERNAL:
            return []

        view = self.view
        from iommi.part import Part

        if isinstance(view, type) and issubclass(view, Part):
            view = view(_collect_instantiated_at_info=False)

        return [
            path('', view, name=self._name_path(), kwargs=self.view_kwargs)
        ] + [
            path_of_item(x)
            for x in self.items.values()
            if x.view is not EXTERNAL
        ] + self.paths

    def bind(self, request, root):
        return BoundM(
            self,
            request=request,
            root=root,
            parent=None,
        )

    def _name_path(self):
        return '.'.join([self.parent._name_path(), self.name])


class BoundM(Tag):
    def __init__(self, m, *, request, parent, root):
        self.tag = 'li'
        self.m = m
        self.request = request
        self.parent = parent
        self.root = root
        self.include = self._include()

        style = resolve_style(None)
        conf = Namespace(*style.resolve(self))

        template = conf.pop('template', 'iommi/main_menu/menu_item.html')
        if self.m.template is not MISSING:
            template = self.m.template

        self.template = template
        attrs = Namespace(self.m.attrs, conf.pop('attrs', {}))
        self.attrs = attrs

        assert not conf, f'Unsupported configuration {conf}'

        self._own_evaluate_parameters = self.own_evaluate_parameters()

        self.render_item = evaluate_strict(self.m.render, **self._own_evaluate_parameters)

        if self.include:
            self.display_name = self._display_name()
            items = self.m.items

            if self.m.dynamic_items:
                assert not items
                items = evaluate_strict(self.m.dynamic_items, **self._own_evaluate_parameters)

            self.raw_items = {
                k: BoundM(
                    v,
                    request=request,
                    root=root,
                    parent=self,
                )
                for k, v in items.items()
            }
            self.items = {k: v for k, v in self.raw_items.items() if v.include}
        else:
            self.raw_items = {}
            self.items = {}

        self.attrs = evaluate_attrs(self, **self._own_evaluate_parameters)

        self.has_rendered_items = len([x for x in self.items.values() if x.render_item]) > 0

    def __str__(self):
        return self.__html__()

    def __html__(self):
        if not self.render_item:
            return ''
        return self.render()

    def render(self):
        return render_template(self.request, self.template, context=self.own_evaluate_parameters())

    def __repr__(self):
        return f'<BoundM {self.m.name}>'

    def iommi_open_tag(self):
        if self.is_active():
            self.attrs['class']['is_active'] = True
        return super().iommi_open_tag()

    def iommi_open_details_tag(self):
        return format_html('<details{}>', " open" if self.open else '')

    def iommi_close_details_tag(self):
        return format_html('</details>', )

    def is_active(self):
        return self.root.active_item is self or any([item.is_active() for item in self.raw_items.values()])

    def own_evaluate_parameters(self):
        request = self.request
        return {
            'request': request,
            'user': request.user if request else None,
            'item': self,
            'main_menu': self.root,
            **getattr(request, 'iommi_view_params', {}),
        }

    @cached_property
    def rendered_attrs(self):
        if self.is_active():
            self.attrs['class']['is_active'] = True
        return render_attrs(self.attrs)

    @cached_property
    def open(self):
        if self.m.open is not None:
            return evaluate_strict(self.m.open, **self.own_evaluate_parameters())

        return self.is_active()

    def params_are_satisfied(self):
        assert hasattr(self.request, 'resolver_match')
        if self.m.params:
            return len(self.m.params & set(getattr(self.request, 'iommi_view_params', {}).keys())) == len(self.m.params)
        else:
            return True

    def _include(self):
        if self.m.include is not None:
            return self.params_are_satisfied() and evaluate_strict(self.m.include, **self.own_evaluate_parameters())
        return self.params_are_satisfied()

    @cached_property
    def icon(self):
        return evaluate_strict(self.m.icon, **self.own_evaluate_parameters())

    @cached_property
    def link(self):
        url = self.url
        icon = ''
        external = ''
        target = ''

        style = resolve_style(None)

        if self.icon is not None:
            icon = style.icon_formatter(self.icon)

        if url.startswith('https://') or url.startswith('http://'):
            external = format_html(' {} ', style.icon_formatter('external'))
            target = ' target="blank"'
        return format_html('<a href="{}" title="{}" {}>{}<span>{}{}</span></a>', url, self.display_name, target, icon, self.display_name, external)

    @property
    def extra(self):
        return self.m.extra

    @cached_property
    def extra_evaluated(self):
        return Struct(evaluate_as_needed(self.m.extra_evaluated or {}, self._own_evaluate_parameters))

    @cached_property
    def url(self):
        if self.m.url is None:
            if self.parent is not None and self.parent.url is not None:
                assert self.parent.url.endswith('/')
                return self.parent.url + self.m.name + '/'
            else:
                return '/' + self.m.name + '/'

        return evaluate_strict(self.m.url, **self.own_evaluate_parameters())

    def _display_name(self):
        return evaluate_strict(self.m.display_name, **self.own_evaluate_parameters())

    def check_access(self):
        if self.is_active() and not self.include:
            raise PermissionDenied()
        for item in self.raw_items.values():
            if not item.is_active():
                continue
            item.check_access()


@django.utils.decorators.sync_and_async_middleware
def main_menu_middleware(get_response):
    from asgiref.sync import iscoroutinefunction

    def _setup_main_menu(request):
        if request.resolver_match is None:
            request.resolver_match = get_resolver(getattr(request, 'urlconf', None)).resolve(request.path_info)

        if request.resolver_match.app_name != 'ninja':
            if not hasattr(request, 'iommi_view_params'):
                try:
                    if not hasattr(request, 'iommi_view_params'):
                        request.iommi_view_params = Struct()
                    request.iommi_view_params.update(**decode_path_components(request, **request.resolver_match.kwargs))
                except PermissionDenied as exception:
                    return handler403(request, exception=exception)

        menu_fully_qualified_name = getattr(settings, 'IOMMI_MAIN_MENU', None)
        assert menu_fully_qualified_name is not None, "To use the main_menu_middleware, you must define settings.IOMMI_MAIN_MENU as a string to the full path to the main menu declaration"
        assert '.' in menu_fully_qualified_name, "IOMMI_MAIN_MENU must be in `your_module.symbol` format"
        menu_module_name, _, menu_symbol_name = menu_fully_qualified_name.rpartition('.')

        module = __import__(menu_module_name, fromlist=['_silly_importlib'])
        menu = getattr(module, menu_symbol_name)
        request.iommi_main_menu = menu.bind(request=request)

        try:
            request.iommi_main_menu.check_access()
        except PermissionDenied as exception:
            return handler403(request, exception=exception)

        return None

    if iscoroutinefunction(get_response):
        from asgiref.sync import sync_to_async

        async def main_menu_middleware_inner(request):
            error_response = await sync_to_async(_setup_main_menu)(request)
            if error_response is not None:
                return error_response
            return await get_response(request)
    else:
        def main_menu_middleware_inner(request):
            error_response = _setup_main_menu(request)
            if error_response is not None:
                return error_response
            return get_response(request)

    return main_menu_middleware_inner
