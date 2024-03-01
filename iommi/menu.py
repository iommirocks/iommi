from collections import defaultdict
from pathlib import PurePosixPath
from typing import (
    Dict,
    Union,
)
from urllib.parse import (
    unquote,
    urlparse,
)

from iommi import Fragment
from iommi._web_compat import (
    Template,
    settings,
)
from iommi.attrs import Attrs
from iommi.base import (
    capitalize,
    items,
    values,
)
from iommi.declarative import declarative
from iommi.declarative.namespace import (
    EMPTY,
    Namespace,
    setdefaults_path,
)
from iommi.declarative.with_meta import with_meta
from iommi.endpoint import path_join
from iommi.evaluate import evaluate_strict
from iommi.fragment import Tag
from iommi.member import (
    bind_members,
    refine_done_members,
)
from iommi.part import Part
from iommi.refinable import (
    EvaluatedRefinable,
    Refinable,
    RefinableMembers,
    SpecialEvaluatedRefinable,
)
from iommi.shortcut import with_defaults
from iommi.struct import Struct


class MenuBase(Part, Tag):
    tag: str = EvaluatedRefinable()
    sort: bool = EvaluatedRefinable()  # only applies for submenu items
    sub_menu: Dict = RefinableMembers()
    attrs: Attrs = SpecialEvaluatedRefinable()
    template: Union[str, Template] = EvaluatedRefinable()

    class Meta:
        sub_menu = EMPTY
        attrs__class = EMPTY
        attrs__style = EMPTY

    @with_defaults(
        sort=True,
    )
    def __init__(self, **kwargs):
        super(MenuBase, self).__init__(**kwargs)
        self._active = False

    def on_refine_done(self):
        refine_done_members(
            self,
            name='sub_menu',
            members_from_namespace=self.sub_menu,
            members_from_declared=self.get_declared('_sub_menu_dict'),
            cls=MenuItem,
        )
        super().on_refine_done()

    def __repr__(self):
        r = f'{self._name}'
        if self.sub_menu:
            for i in values(self.sub_menu):
                r += ''.join([f'\n    {x}' for x in repr(i).split('\n')])
        return r

    def on_bind(self):
        bind_members(self, name='sub_menu')

        if self.sort:
            self.sub_menu = Struct(
                {item._name: item for item in sorted(values(self.sub_menu), key=lambda x: x.display_name)}
            )


@with_meta
class MenuItem(MenuBase):
    """
    Class that is used for the clickable menu items in a menu.

    See :doc:`Menu` for more complete examples.
    """

    display_name: str = EvaluatedRefinable()
    url: str = SpecialEvaluatedRefinable()
    regex: str = EvaluatedRefinable()
    group: str = EvaluatedRefinable()
    a = Refinable()
    active_class = Refinable()
    active_class_on_item = Refinable()

    class Meta:
        a = EMPTY

    @with_defaults(
        display_name=lambda menu_item, **_: capitalize(menu_item.iommi_name()).replace('_', ' '),
        regex=lambda menu_item, **_: '^' + str(menu_item.url) if menu_item.url else None,
        url=lambda menu_item, **_: (
            '/' + path_join(getattr(menu_item.iommi_parent(), 'url', None), menu_item.iommi_name()) + '/'
        ),
    )
    def __init__(self, **kwargs):
        super(MenuItem, self).__init__(**kwargs)

    def on_bind(self):
        super(MenuItem, self).on_bind()
        assert self.active_class is not None, 'No active_class provided'
        self.url = evaluate_strict(self.url, **self.iommi_evaluate_parameters())

        # If this is a section header, and all sub-parts are hidden, hide myself
        if not self.url and self.sub_menu is not None and not self.sub_menu:
            self.include = False

    def own_evaluate_parameters(self):
        return dict(menu_item=self)

    def __repr__(self):
        r = f'{self._name} -> {self.url}'
        if self.sub_menu:
            if isinstance(self.sub_menu, dict):
                for i in values(self.sub_menu):
                    r += ''.join([f'\n    {x}' for x in repr(i).split('\n')])
            else:
                r += str(self.sub_menu)
        return r

    def __html__(self, *, render=None):
        a = setdefaults_path(
            Namespace(),
            self.a,
            children__text=self.display_name,
            attrs__href=self.url,
            _name='a',
        )
        if self._active and not self.active_class_on_item:
            setdefaults_path(
                a,
                attrs__class={self.active_class: True},
            )

        if self.url is None and a.tag == 'a':
            a.tag = None

        fragment = Namespace(
            call_target=Fragment,
            children__a=a,
            tag=self.tag,
            template=self.template,
            attrs=self.attrs,
            _name='fragment',
        )
        if self._active and self.active_class_on_item:
            setdefaults_path(
                fragment,
                attrs__class={self.active_class: True},
            )

        fragment = fragment().bind(parent=self)
        # need to do this here because otherwise the sub menu will get get double bind
        for name, item in items(self.sub_menu):
            assert name not in fragment.children
            fragment.children[name] = item

        return fragment.__html__()


class MenuException(Exception):
    pass


def _path_plus_query(url):
    x = urlparse(str(url))
    parsed_url = x.path
    if x.query:
        parsed_url += f'?{x.query}'
    return parsed_url


@with_meta
@declarative(MenuItem, '_sub_menu_dict', add_init_kwargs=False)
class Menu(MenuBase):
    """
    Class that describes menus.

    Example:

    .. code-block:: python

        menu = Menu(
            sub_menu=dict(
                root=MenuItem(url='/'),

                albums=MenuItem(url='/albums/'),

                # url defaults to /<name>/ so we
                # don't need to write /musicians/ here
                musicians=MenuItem(),
            ),
        )
    """

    items_container = Refinable()

    class Meta:
        items_container = EMPTY

    @with_defaults(
        sort=False,
    )
    def __init__(self, **kwargs):
        super(Menu, self).__init__(**kwargs)

    def __html__(self, *, render=None):
        fragment = Fragment(
            _name=self._name,
            tag=self.tag,
            template=self.template,
            children__items_container=Fragment(
                **self.items_container,
            ),
        ).bind(parent=self)
        # need to do this here because otherwise the sub menu will get get double bind
        items_container = fragment.children.items_container
        for name, item in items(self.sub_menu):
            assert name not in items_container.children
            items_container.children[name] = item

        # If we pass attrs to the fragment in on_bind, styling can't be applied, so we do this thing instead.
        fragment.attrs = self.attrs
        return fragment.__html__()

    def on_bind(self):
        super(Menu, self).on_bind()

        self.set_active(current_path=_path_plus_query(self.get_request().build_absolute_uri()))

    def own_evaluate_parameters(self):
        return dict(menu=self)

    def validate(self):
        # verify there is no ambiguity for the MenuItems
        paths = defaultdict(list)

        def _validate(item):
            for sub_item in values(item.sub_menu):
                if sub_item.url is None or '://' in sub_item.url or sub_item.url.startswith('#'):
                    continue

                _validate(sub_item)

                path = urlparse(sub_item.url).path
                paths[path].append(sub_item.iommi_path)

        _validate(self)

        ambiguous = {k: v for k, v in items(paths) if len(v) > 1}
        return ambiguous

    def set_active(self, current_path: str):
        current = None
        current_parts_matching = 0
        path_parts = PurePosixPath(current_path).parts

        def _set_active(item):
            nonlocal current_parts_matching
            nonlocal current
            for sub_item in values(item.sub_menu):
                _set_active(sub_item)

                if sub_item.url is None or '://' in sub_item.url:
                    continue

                parsed_url = _path_plus_query(sub_item.url)

                if current_path.startswith(parsed_url):
                    parts = PurePosixPath(unquote(parsed_url)).parts
                    matching_parts = 0
                    for item in range(min(len(parts), len(path_parts))):
                        if parts[item] is path_parts[item]:
                            matching_parts += 1

                    if matching_parts > current_parts_matching:
                        current = sub_item
                        current_parts_matching = matching_parts

        _set_active(self)

        if current:
            current._active = True


def get_debug_menu(**kwargs):
    class DebugMenu(Menu):
        code = MenuItem(tag='li')
        templates = MenuItem(url='?/debug_templates_used', tag='li', include=lambda request, **_: getattr(request, 'iommi_used_templates', None))
        tree = MenuItem(url='?/debug_tree', tag='li')
        pick = MenuItem(url='#', attrs__onclick='window.iommi_start_pick()', tag='li')
        edit = MenuItem(
            display_name=lambda request, **_: 'Edit vertical'
            if request.GET.get('_iommi_live_edit') is not None and request.GET.get('_iommi_live_edit_flow') != 'row' else 'Edit',
            url=lambda request, **_: '?_iommi_live_edit&_iommi_live_edit_flow=row'
            if request.GET.get('_iommi_live_edit') is not None and request.GET.get('_iommi_live_edit_flow') != 'row'
            else '?_iommi_live_edit',
            tag='li',
            include=lambda **_: 'iommi.live_edit.Middleware' in settings.MIDDLEWARE,
        )
        stop_editing = MenuItem(
            display_name='Stop editing',
            url='?_iommi_live_edit=stop',
            tag='li',
            include=lambda request, **_: '_iommi_live_edit' in request.GET,
        )
        edit_style = MenuItem(
            url='?_iommi_live_edit=style_editor',
            tag='li',
            include=lambda **_: 'iommi.live_edit.Middleware' in settings.MIDDLEWARE,
        )
        profile = MenuItem(
            url='?_iommi_prof', tag='li', include=lambda **_: 'iommi.profiling.Middleware' in settings.MIDDLEWARE
        )
        profile_post = MenuItem(
            display_name='Profile POST',
            url='#',
            # language=js
            attrs__onclick="""
            for (form of document.querySelectorAll('form')) {
                var input = document.createElement("input");
                input.setAttribute("type", "hidden");
                input.setAttribute("name", "_iommi_prof");
                form.appendChild(input);
            }
            """,
            tag='li',
            include=lambda **_: 'iommi.profiling.Middleware' in settings.MIDDLEWARE,
        )
        sql_trace = MenuItem(
            display_name='SQL trace',
            url='?_iommi_sql_trace',
            tag='li',
            include=lambda **_: 'iommi.sql_trace.Middleware' in settings.MIDDLEWARE,
        )

    return DebugMenu(**kwargs)
