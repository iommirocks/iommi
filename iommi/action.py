from copy import copy
from itertools import groupby
from typing import (
    Callable,
    Dict,
    List,
    Tuple,
)

from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.text import slugify
from tri_declarative import (
    class_shortcut,
    dispatch,
    EMPTY,
    Refinable,
    setdefaults_path,
    with_meta,
)

from iommi.attrs import Attrs
from iommi.member import Members
from iommi.page import Fragment
from iommi.part import Part
from iommi.traversable import (
    EvaluatedRefinable,
    get_parent,
)


@with_meta
class Action(Part):
    """
    The `Action` class describes buttons and links.

    Examples:

    .. code:: python

        # Link
        Action(attrs__href='http://example.com')

        # Link with icon
        Action.icon('edit', attrs__href="edit/")

        # Button
        Action.button(attrs__value='Button title!')
    """

    tag: str = EvaluatedRefinable()
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    group: str = EvaluatedRefinable()
    template = EvaluatedRefinable()
    display_name: str = EvaluatedRefinable()
    post_handler: Callable = Refinable()

    @dispatch(
        tag='a',
        display_name=lambda action, **_: action._name.capitalize().replace('_', ' '),
        attrs__class=EMPTY,
    )
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def own_target_marker(self):
        return f'-{self.iommi_path}'

    def is_target(self):
        return self.own_target_marker() in get_parent(get_parent(self))._request_data

    @dispatch(
        context=EMPTY,
        render=EMPTY,
    )
    def __html__(self, *, context=None, render=None):
        assert not render
        assert self._is_bound
        if self.template:
            return render_to_string(self.template, dict(**context, action=self))
        else:
            display_name = self.display_name
            attrs = self.attrs
            if self.tag == 'input':
                if display_name and 'value' not in attrs:
                    attrs = copy(attrs)
                    attrs.value = self.display_name
                display_name = None
            return Fragment(display_name, tag=self.tag, attrs=attrs).bind(parent=self).__html__()

    @classmethod
    @class_shortcut(
        tag='button',
    )
    def button(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='button',
        tag='input',
        attrs__type='submit',
        attrs__accesskey='s',
        attrs__name=lambda action, **_: action.own_target_marker(),
    )
    def submit(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='submit',
    )
    def delete(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        icon_classes=[],
    )
    def icon(cls, icon, *, display_name=None, call_target=None, icon_classes=None, **kwargs):
        icon_classes_str = ' '.join(['fa-' + icon_class for icon_class in icon_classes]) if icon_classes else ''
        if icon_classes_str:
            icon_classes_str = ' ' + icon_classes_str
        setdefaults_path(
            kwargs,
            display_name=format_html('<i class="fa fa-{}{}"></i> {}', icon, icon_classes_str, display_name),
        )
        return call_target(**kwargs)

    def own_evaluate_parameters(self):
        return dict(action=self)


def group_actions(actions: Dict[str, Action]):
    grouped_actions = []
    actions_without_group = []

    if actions is not None:
        actions_with_group = (action for action in actions.values() if action.group is not None)

        grouped_actions: List[Tuple[str, str, List[Action]]] = [
            (group_name, slugify(group_name), list(actions_in_group))
            for group_name, actions_in_group in groupby(
                actions_with_group,
                key=lambda l: l.group
            )
        ]

        for _, _, actions_in_group in grouped_actions:
            for action in actions_in_group:
                action.attrs.role = 'menuitem'

        actions_without_group = [
            action
            for action in actions.values()
            if action.group is None
        ]

    return actions_without_group, grouped_actions


class Actions(Members):
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    tag = EvaluatedRefinable()

    @dispatch(
        attrs__class=EMPTY,
    )
    def __init__(self, **kwargs):
        super(Actions, self).__init__(**kwargs)
