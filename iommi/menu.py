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

from tri_declarative import (
    declarative,
    dispatch,
    EMPTY,
    Namespace,
    Refinable,
    setdefaults_path,
    with_meta,
)
from tri_struct import Struct

from iommi import Fragment
from iommi._web_compat import (
    settings,
    Template,
)
from iommi.attrs import Attrs
from iommi.base import (
    capitalize,
    items,
    values,
)
from iommi.endpoint import path_join
from iommi.evaluate import evaluate_strict
from iommi.fragment import Tag
from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.part import Part
from iommi.reinvokable import reinvokable
from iommi.traversable import (
    EvaluatedRefinable,
)


class MenuBase(Part, Tag):
    tag: str = EvaluatedRefinable()
    sort: bool = EvaluatedRefinable()  # only applies for submenu items
    sub_menu: Dict = Refinable()
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = EvaluatedRefinable()

    @reinvokable
    @dispatch(
        sort=True,
        sub_menu=EMPTY,
        attrs__class=EMPTY,
        attrs__style=EMPTY,
    )
    def __init__(self, sub_menu, _sub_menu_dict=None, **kwargs):
        super(MenuBase, self).__init__(**kwargs)
        self._active = False

        collect_members(
            self,
            name='sub_menu',
            items=sub_menu,
            # TODO: cls=self.get_meta().member_class,
            items_dict=_sub_menu_dict,
            cls=MenuItem,
        )

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
    url: str = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    regex: str = EvaluatedRefinable()
    group: str = EvaluatedRefinable()
    a = Refinable()
    active_class = Refinable()

    @reinvokable
    @dispatch(
        display_name=lambda menu_item, **_: capitalize(menu_item.iommi_name()).replace('_', ' '),
        regex=lambda menu_item, **_: '^' + str(menu_item.url) if menu_item.url else None,
        url=lambda menu_item, **_: '/'
        + path_join(getattr(menu_item.iommi_parent(), 'url', None), menu_item.iommi_name())
        + '/',
        a=EMPTY,
    )
    def __init__(self, **kwargs):
        super(MenuItem, self).__init__(**kwargs)

    def on_bind(self):
        super(MenuItem, self).on_bind()

        self.url = evaluate_strict(self.url, **self.iommi_evaluate_parameters())

        # If this is a section header, and all sub-parts are hidden, hide myself
        if not self.url and self.sub_menu is not None and not self.sub_menu:
            self.include = False

    def own_evaluate_parameters(self):
        return dict(menu_item=self)

    def __repr__(self):
        r = f'{self._name} -> {self.url}'
        if self.sub_menu:
            for i in values(self.sub_menu):
                r += ''.join([f'\n    {x}' for x in repr(i).split('\n')])
        return r

    def __html__(self, *, render=None):
        a = setdefaults_path(
            Namespace(),
            self.a,
            children__text=self.display_name,
            attrs__href=self.url,
            _name='a',
        )
        if self._active:
            setdefaults_path(
                a,
                attrs__class={self.active_class: True},
            )

        if self.url is None and a.tag == 'a':
            a.tag = None

        fragment = Fragment(
            children__a=a,
            tag=self.tag,
            template=self.template,
            attrs=self.attrs,
            _name='fragment',
        )
        fragment = fragment.bind(parent=self)
        # need to do this here because otherwise the sub menu will get get double bind
        for name, item in items(self.sub_menu):
            assert name not in fragment.children
            fragment.children[name] = item

        return fragment.__html__()


class MenuException(Exception):
    pass


@with_meta
@declarative(MenuItem, '_sub_menu_dict')
class Menu(MenuBase):
    """
    Class that describes menus.

    Example:

    .. code:: python

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

    @reinvokable
    @dispatch(
        sort=False,
        items_container=EMPTY,
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
        self.set_active(current_path=self.get_request().path)

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

                parsed_url = urlparse(str(sub_item.url)).path

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
        tree = MenuItem(url='?/debug_tree', tag='li')
        pick = MenuItem(url='#', attrs__onclick='window.iommi_start_pick()', tag='li')
        edit = MenuItem(
            display_name=lambda request, **_: 'Edit'
            if request.GET.get('_iommi_live_edit') in (None, 'row')
            else 'Edit vertical',
            url=lambda request, **_: '?_iommi_live_edit'
            if request.GET.get('_iommi_live_edit') in (None, 'row')
            else '?_iommi_live_edit=row',
            tag='li',
            include=lambda **_: 'iommi.live_edit.Middleware' in settings.MIDDLEWARE,
        )
        profile = MenuItem(
            url='?_iommi_prof', tag='li', include=lambda **_: 'iommi.profiling.Middleware' in settings.MIDDLEWARE
        )
        sql_trace = MenuItem(
            display_name='SQL trace',
            url='?_iommi_sql_trace',
            tag='li',
            include=lambda **_: 'iommi.sql_trace.Middleware' in settings.MIDDLEWARE,
        )

    return DebugMenu(**kwargs)
