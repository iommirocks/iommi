from functools import cached_property
from pathlib import PurePosixPath
from urllib.parse import urlparse

from django.conf import settings
from django.conf.urls import handler403
from django.core.exceptions import PermissionDenied
from django.urls import (
    get_resolver,
    include,
    path as orig_path,
)
from django.utils.translation import gettext_lazy

from iommi import (
    Asset,
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
from iommi.evaluate import evaluate_strict
from iommi.path import decode_path_components
from iommi.struct import Struct
from iommi.style import resolve_style

EXTERNAL = object()


class NoTranslateString(str):
    pass


def path(path, view_or_list, kwargs=None):
    if isinstance(view_or_list, list):
        assert kwargs is None
        return orig_path(path, include(view_or_list))
    elif isinstance(view_or_list, type):
        return orig_path(path, view_or_list().as_view(), kwargs=kwargs)
    else:
        try:
            return orig_path(path, view_or_list.as_view(), kwargs=kwargs)
        except AttributeError:
            return orig_path(path, view_or_list, kwargs=kwargs)


class MainMenu:
    @dispatch(
        items=EMPTY,
        attrs__style=EMPTY,
        attrs__class=EMPTY,
    )
    def __init__(self, *, items=None, attrs, template=MISSING, paths=None):
        self.items = items
        self.attrs = attrs
        self.template = template
        self.paths = paths or []
        for name, c in self.items.items():
            c.parent = self
            c._set_name(name)

    def urlpatterns(self):
        if 'iommi.experimental.main_menu.main_menu_middleware' not in settings.MIDDLEWARE:
            # This is an explicit raise instead of an `assert` because I'm paranoid of people running Python in optimized mode with skipped asserts.
            raise AssertionError('To use the iommi main menu, you must add `iommi.experimental.main_menu.main_menu_middleware` to the MIDDLEWARE list.')

        return [
            path(x.path, x.urlpatterns())
            for x in self.items.values()
            if x.view is not EXTERNAL
        ] + self.paths

    def bind(self, request):
        style = resolve_style(None)
        conf = Namespace(*style.resolve(self))

        template = conf.pop('template', 'iommi/main_menu/menu.html')
        if self.template is MISSING:
            template = template

        attrs = Namespace(self.attrs, conf.pop('attrs', {}))

        return BoundMainMenu(
            self,
            request,
            attrs=attrs,
            template=template,
        )

    def __repr__(self):
        return '<MainMenu>'


class BoundMainMenu:
    def __init__(self, main_menu, request, attrs, template):
        self.main_menu = main_menu
        self.request = request
        self.attrs = attrs
        self.template = template
        self.paths = main_menu.paths

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
            a = PurePosixPath(x.url).parts
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
        for item in self.raw_items.values():
            if not item.is_active():
                continue
            item.check_access()

    def params_are_satisfied(self):
        return True

    def __str__(self):
        return self.__html__()

    def __html__(self):
        return render_template(self.request, self.template, dict(menu=self))

    def render_items(self):
        return format_html('{}' * len(self.items), *[x.__html__() for x in self.items.values()])

    def assets(self):
        # TODO: this needs to come from the Style
        return dict(
            iommi_main_menu_css=Asset.css(
                attrs__href='/static/css/iommi_main_menu.css'
            ).bind(request=self.request),
        )

    def __repr__(self):
        return '<BoundMainMenu>'


class M:
    @dispatch(
        items=EMPTY,
        attrs__style=EMPTY,
        attrs__class=EMPTY,
    )
    def __init__(self, *, icon=None, view=None, view_kwargs=None, path=MISSING, url=None, open=None, params=None, display_name=None, items=None, include=None, attrs, template=MISSING, paths=None):

        assert view is not None or view is EXTERNAL, f'Items should either have a view function specified, or supply EXTERNAL to mark the item as having an external URL and thus not needing access control. Got {view!r}'

        self.name = None
        self.icon = icon
        self.url = url
        assert url is None or isinstance(url, str) or callable(url)
        self.path = path
        assert path is MISSING or path is None or isinstance(path, str), f'`path` must be `MISSING`, `None` or a `str`. Got {type(self.path)} ({self.path}).'
        self.paths = paths or []
        assert isinstance(self.paths, list), f'`paths` must be of type list. Got type {type(self.paths)} ({self.paths}).'
        self.view = view
        self.view_kwargs = view_kwargs
        self.include = include
        self.display_name = display_name
        self._raw_display_name = None  # We need programmatic access to this from okrand for i18n
        self.items = {
            k: M(**v) if isinstance(v, dict) else v
            for k, v in items.items()
        }
        self.parent = None
        self.params = params
        self.open = open
        self.attrs = attrs
        self.template = template
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
        if not callable(self.display_name) and not isinstance(self.display_name, NoTranslateString):
            self._raw_display_name = (self.display_name or name).replace('_', ' ')
            self.display_name = capitalize(gettext_lazy(self._raw_display_name))
        if self.path is MISSING:
            self.path = self.name + '/'

    def urlpatterns(self):
        if isinstance(self.url, str) and self.path is MISSING:
            return []

        if self.view is EXTERNAL:
            return []

        return [
            path('', self.view, kwargs=self.view_kwargs)
        ] + [
            path(x.path, x.urlpatterns())
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


class BoundM:
    def __init__(self, m, *, request, parent, root):
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

        if self.include:
            self.display_name = self._display_name()
            self.raw_items = {
                k: BoundM(
                    v,
                    request=request,
                    root=root,
                    parent=self,
                )
                for k, v in self.m.items.items()
            }
            self.items = {k: v for k, v in self.raw_items.items() if v.include}
        else:
            self.raw_items = {}
            self.items = {}

        self._own_evaluate_parameters = self.own_evaluate_parameters()

        self.attrs = evaluate_attrs(self, **self._own_evaluate_parameters)

    def __str__(self):
        return self.__html__()

    def __html__(self):
        return self.render()

    def render(self):
        return render_template(self.request, self.template, context=self.own_evaluate_parameters())

    def __repr__(self):
        return f'<BoundM {self.m.name}>'

    def is_active(self):
        return self.root.active_item is self or any([item.is_active() for item in self.raw_items.values()])

    def own_evaluate_parameters(self):
        request = self.request
        return {
            'request': request,
            'user': request.user if request else None,
            'item': self,
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
            return evaluate_strict(self.m.include, **self.own_evaluate_parameters())
        return self.params_are_satisfied()

    @cached_property
    def link(self):
        url = self.url
        icon = ''
        external = ''
        target = ''

        style = resolve_style(None)

        if self.m.icon is not None:
            icon = style.icon_formatter(self.m.icon)

        if url.startswith('https://'):
            external = format_html(' {} ', style.icon_formatter('external'))
            target = ' target="blank"'
        return format_html('<a href="{}" alt="{}" {}>{}<span>{}{}</span></a>', url, self.display_name, target, icon, self.display_name, external)

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


def main_menu_middleware(get_response):
    def main_menu_middleware_inner(request):
        if request.resolver_match is None:
            request.resolver_match = get_resolver().resolve(request.path_info)

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

        return get_response(request)

    return main_menu_middleware_inner
