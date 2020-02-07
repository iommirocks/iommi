from itertools import groupby
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Tuple,
)

from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.text import slugify
from iommi.base import (
    evaluate_attrs,
    evaluate_strict_container,
    Part,
)
from iommi.page import Fragment
from tri_declarative import (
    class_shortcut,
    dispatch,
    EMPTY,
    Refinable,
    setattr_path,
    setdefaults_path,
)


class Action(Part):
    tag: str = Refinable()
    attrs: Dict[str, Any] = Refinable()
    group: str = Refinable()
    template = Refinable()
    display_name: str = Refinable()
    post_handler: Callable = Refinable()

    @dispatch(
        tag='a',
        attrs=EMPTY,
    )
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.declared_action = None

        if self.tag == 'input' and self.display_name:
            assert False, "display_name is invalid on input tags. Maybe you want attrs__value if it's a button?"

    def own_target_marker(self):
        return f'-{self.path()}'

    def is_target(self):
        return self.own_target_marker() in self.parent.parent._request_data

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
            return Fragment(tag=self.tag, attrs=self.attrs, child=self.display_name).__html__()

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
        attrs__value='Submit',
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

    def on_bind(self) -> None:
        if self.parent is not None and self.parent.parent is not None:
            for k, v in getattr(self.parent.parent, '_actions_unapplied_data', {}).get(self.name, {}).items():
                setattr_path(self, k, v)
        evaluated_attributes = [
            'tag',
            'group',
            'template',
            'display_name',
            'name',
            'after',
            'style',
        ]
        for key in evaluated_attributes:
            self._evaluate_attribute(key)

        self.extra_evaluated = evaluate_strict_container(self.extra_evaluated, **self.evaluate_parameters())
        self.attrs = evaluate_attrs(self, **self.evaluate_parameters())

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

        for _, _, group_actions in grouped_actions:
            for action in group_actions:
                action.attrs.role = 'menuitem'

        actions_without_group = [
            action
            for action in actions.values()
            if action.group is None
        ]

    return actions_without_group, grouped_actions
