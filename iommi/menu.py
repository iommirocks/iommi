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
    Refinable,
    with_meta,
    setdefaults_path,
    Namespace,
)
from tri_struct import Struct

from iommi._web_compat import Template
from iommi.attrs import Attrs
from iommi.endpoint import path_join
from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.page import Fragment
from iommi.part import Part
from iommi.traversable import EvaluatedRefinable


class MenuBase(Part):
    tag: str = EvaluatedRefinable()
    sort: bool = EvaluatedRefinable()  # only applies for submenu items
    sub_menu: Dict = Refinable()
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = EvaluatedRefinable()

    @dispatch(
        sort=True,
        sub_menu=EMPTY,
        attrs=EMPTY,
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
        r = '%s -> %s\n' % (self._name, self.url)
        for items in self.sub_menu.values():
            r += '    ' + repr(items)
        return r

    def on_bind(self):
        bind_members(self, name='sub_menu')

        if self.sort:
            self.sub_menu = Struct({
                item._name: item
                for item in sorted(self.sub_menu.values(), key=lambda x: x.display_name)
            })

    def own_evaluate_parameters(self):
        return dict(menu_item=self)


class MenuItem(MenuBase):
    """
    Class that is used for the clickable menu items in a menu.

    See :doc:`Menu` for more complete examples.
    """

    display_name: str = EvaluatedRefinable()
    url: str = EvaluatedRefinable()
    regex: str = EvaluatedRefinable()
    group: str = EvaluatedRefinable()

    @dispatch(
        display_name=lambda menu_item, **_: menu_item._name.capitalize().replace('_', ' '),
        regex=lambda menu_item, **_: '^' + menu_item.url if menu_item.url else None,
        url=lambda menu_item, **_: '/' + path_join(getattr(menu_item._parent, 'url', None), menu_item._name) + '/',
        a__tag='a',
    )
    def __init__(self, *, a, **kwargs):
        super(MenuItem, self).__init__(**kwargs)
        self.fragment = None
        self.a = a

    def on_bind(self):
        super(MenuItem, self).on_bind()

        # If this is a section header, and all sub-parts are hidden, hide myself
        if not self.url and not self.sub_menu:
            self.include = False

    def own_evaluate_parameters(self):
        return dict(menu_item=self)

    def __html__(self, *, context=None, render=None):
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
                attrs__class__active=True,
            )

        fragment = Fragment(
            children__a=a,
            tag=self.tag,
            template=self.template,
            attrs=self.attrs,
            _name='fragment',
        )
        fragment = fragment.bind(parent=self)
        # need to do this here because otherwise the sub menu will get get double bind
        for name, item in self.sub_menu.items():
            assert name not in self.fragment.children
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

    @dispatch(
        sort=False,
        items_container=EMPTY,
    )
    def __init__(self, **kwargs):
        super(Menu, self).__init__(**kwargs)
        self.fragment = None

    def __html__(self, *, context=None, render=None):
        return self.fragment.__html__()

    def on_bind(self):
        super(Menu, self).on_bind()
        self.validate_and_set_active(current_path=self.get_request().path)

        self.fragment = Fragment(
            _name=self._name,
            tag=self.tag,
            template=self.template,
            attrs=self.attrs,
            children__items_container=Fragment(
                **self.items_container,
            )
        ).bind(parent=self)
        # need to do this here because otherwise the sub menu will get get double bind
        items_container = self.fragment.children.items_container
        for name, item in self.sub_menu.items():
            assert name not in items_container.children
            items_container.children[name] = item

    def validate_and_set_active(self, current_path: str):

        # verify there is no ambiguity for the MenuItems
        paths = set()
        for item in self.sub_menu.values():
            if '://' in item.url:
                continue

            path = urlparse(item.url).path
            if path in paths:
                raise MenuException(f'MenuItem paths are ambiguous; several non-external MenuItems have the path: {path}')

            paths.add(path)

        current = None
        current_parts_matching = 0
        path_parts = PurePosixPath(current_path).parts

        items = [(item, urlparse(item.url)) for item in self.sub_menu.values()]
        for (item, parsed_url) in items:
            if '://' in item.url:
                continue

            if current_path.startswith(parsed_url.path):
                parts = PurePosixPath(unquote(parsed_url.path)).parts
                matching_parts = 0
                for i in range(min(len(parts), len(path_parts))):
                    if parts[i] is path_parts[i]:
                        matching_parts += 1

                if matching_parts > current_parts_matching:
                    current = (item, parsed_url)
                    current_parts_matching = matching_parts

        if current:
            current[0]._active = True


class DebugMenu(Menu):
    code = MenuItem()
    tree = MenuItem(url='?/debug_tree')

    class Meta:
        attrs__style = {
            'float': 'right',
            'padding-left': '20px',
        }
        attrs__class = {
            'flex-column': False,
        }
