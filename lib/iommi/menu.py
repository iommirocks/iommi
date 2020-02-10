from typing import (
    Dict,
    Union,
    List,
)
from urllib.parse import (
    urlparse,
    unquote,
)
from pathlib import PurePosixPath

from tri_declarative import (
    EMPTY,
    Refinable,
    dispatch,
)
from tri_struct import Struct

from iommi import Part
from iommi._web_compat import (
    Template,
)
from iommi.base import (
    bind_members,
    collect_members,
    evaluate_attrs,
    evaluate_strict_container,
    EvaluatedRefinable,
    is_evaluated_refinable,
    evaluate_members,
)
from iommi.page import Fragment
from iommi.render import Attrs


class MenuBase(Part):
    tag: str = Refinable()
    sort: bool = Refinable()  # only applies for submenu items
    sub_menu: Dict = Refinable()
    attrs: Attrs = Refinable()
    template: Union[str, Template] = Refinable()

    @dispatch(
        sort=True,
        attrs=EMPTY,
        attrs__class__nav=True,  # TODO: style!
        attrs__class={'nav-pills': True},  # TODO: style!
        tag='ul',  # TODO: style!
        sub_menu=EMPTY,
    )
    def __init__(self, sub_menu, **kwargs):
        super(MenuBase, self).__init__(**kwargs)

        collect_members(
            self,
            name='sub_menu',
            items=sub_menu,
            # TODO: cls=self.get_meta().menu_item_class,
            cls=MenuItem,
            unapplied_config={},
        )

    def __repr__(self):
        r = '%s -> %s\n' % (self.name, self.url)
        for items in self.sub_menu.values():
            r += '    ' + repr(items)
        return r

    def on_bind(self):
        bind_members(self, name='sub_menu')

        # TODO:
        if self.sort:
            self.sub_menu = Struct({
                item.name: item
                for item in sorted(self.sub_menu.values(), key=lambda x: x.display_name)
            })

    def own_evaluate_parameters(self):
        return dict(menu_item=self)


class MenuItem(MenuBase):
    display_name: str = Refinable()
    url: str = Refinable()
    regex: str = Refinable()
    group: str = Refinable()

    @dispatch(
        display_name=lambda menu_item, **_: menu_item.name.title(),
        url=lambda menu_item, **_: '^' + menu_item.url if menu_item.url else None,
        tag='li',
    )
    def __init__(self, **kwargs):
        super(MenuItem, self).__init__(**kwargs)
        self.fragment = None
        self.a = None

    def on_bind(self):
        super(MenuItem, self).on_bind()

        # If this is a section header, and all sub-parts are hidden, hide myself
        if not self.url and not self.sub_menu:
            self.include = False

        self.a = Fragment(
            tag='a',
            attrs__href=self.url,
            attrs__class={'nav-link': True},  # TODO: style!
            child=self.display_name,
        )
        self.fragment = Fragment(
            tag=self.tag,
            template=self.template,
            attrs=self.attrs,
            child=self.a,
            children=self.sub_menu.values(),
        ).bind(parent=self)

    def __html__(self, *, context=None, render=None):
        return self.fragment.__html__()


class MenuException(Exception):
    pass


class Menu(MenuBase):
    @dispatch(
        sort=False
    )
    def __init__(self, **kwargs):
        super(Menu, self).__init__(**kwargs)
        self.fragment = None

    def __html__(self, *, context=None, render=None):
        return self.fragment.__html__()

    def on_bind(self):
        super(Menu, self).on_bind()
        self.validate_and_set_active(current_path=self.request().path)

        self.fragment = Fragment(
            tag=self.tag,
            template=self.template,
            attrs=self.attrs,
            children=self.sub_menu.values(),
        ).bind(parent=self)

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
            current[0].a.attrs['class']['active'] = True
