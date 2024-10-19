import warnings
from itertools import groupby
from typing import (
    Callable,
    Dict,
    List,
    Tuple,
)

from django.utils.translation import gettext_lazy

from iommi._web_compat import (
    format_html,
    slugify,
)
from iommi.attrs import (
    Attrs,
    render_attrs,
)
from iommi.base import (
    capitalize,
    values,
)
from iommi.declarative.namespace import (
    EMPTY,
    setdefaults_path,
)
from iommi.declarative.with_meta import with_meta
from iommi.fragment import (
    Fragment,
    Tag,
)
from iommi.member import Members
from iommi.part import Part
from iommi.refinable import (
    EvaluatedRefinable,
    Prio,
    Refinable,
    SpecialEvaluatedRefinable,
)
from iommi.shortcut import with_defaults


@with_meta
class Action(Fragment):
    # language=rst
    """
    The `Action` class describes buttons and links.

    Examples:

    .. code-block:: python

        # @test
        actions = dict(
        # @end

        # Link
        example=Action(attrs__href='http://example.com'),

        # Link with icon
        edit=Action.icon('pencil-square', attrs__href="edit/"),

        # Button
        button=Action.button(display_name='Button title!'),

        # A submit button
        submit=Action.submit(display_name='Do this'),

        # The primary submit button on a form.
        primary=Action.primary(),

        # @test
        )

        from iommi.refinable import Prio
        foo = Page(
            parts__css=html.style('''
                a, button {
                    display: block !important;
                    margin-bottom: 0.5rem;
                }
            '''),
            parts=actions,
        )
        show_output(foo)
        # @end

    Notice that because forms
    with a single primary submit button are so common, iommi assumes
    that if you have an action called submit and do NOT explicitly
    specify the action that it is a primary action. This is only
    done for the action called `submit`, inside the Forms actions
    `Namespace`.

    For that reason this works:

    .. code-block:: python

        class MyForm(Form):
            class Meta:
                @staticmethod
                def actions__submit__post_handler(form, **_):
                    if not form.is_valid():
                        return

                    ...

    and is roughly equivalent to

    .. code-block:: python

        def on_submit(form, **_):
            if not form.is_valid():
                return

        class MyOtherForm(Form):
            class Meta:
                actions__submit = Action.primary(post_handler=on_submit)

        # @test
        r = req('post', **{'-submit': ''})
        MyForm().bind(request=r).render_to_response()
        MyOtherForm().bind(request=r).render_to_response()
        # @end
    """

    group: str = EvaluatedRefinable()
    display_name: str = EvaluatedRefinable()
    post_handler: Callable = Refinable()

    @with_defaults(
        tag='a',
        display_name=lambda action, **_: capitalize(action._name).replace('_', ' '),
    )
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_refine_done(self):
        if self.tag == 'input':
            if self.display_name and 'value' not in self.attrs:
                self.attrs.value = self.display_name
        else:
            self.children['text'] = self.display_name
            if self.tag == 'button' and 'value' in self.attrs:
                assert False, 'You passed attrs__value, but you should pass display_name'
        super().on_refine_done()

    def on_bind(self):
        super().on_bind()

    def own_evaluate_parameters(self):
        return dict(action=self)

    def __repr__(self):
        return Part.__repr__(self)

    def own_target_marker(self):
        return f'-{self.iommi_path}'

    def is_target(self):
        return self.own_target_marker() in self.iommi_parent().iommi_parent()._request_data

    @classmethod
    @with_defaults(
        tag='button',
    )
    def button(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        attrs__accesskey='s',
        attrs__name=lambda action, **_: action.own_target_marker(),
        display_name=gettext_lazy('Submit'),
    )
    def submit(cls, **kwargs):
        return cls.button(**kwargs)

    @classmethod
    @with_defaults
    def primary(cls, **kwargs):
        return cls.submit(**kwargs)

    @classmethod
    @with_defaults
    def delete(cls, **kwargs):
        return cls.submit(**kwargs)

    @classmethod
    @with_defaults(
        extra__icon_attrs__class=EMPTY,
        extra__icon_attrs__style=EMPTY,
    )
    def icon(cls, icon, *, display_name=None, icon_classes=None, **kwargs):
        if icon_classes is not None:
            assert False, 'icon_classes is removed, use the extra__icon_attrs__class namespace'
        return cls(**kwargs).refine(
            extra__icon=icon,
            extra__orig_display_name=display_name,
            display_name=default_action__icon__display_name,
            prio=Prio.shortcut,
        )


def default_action__icon__display_name(action, **_):
    if not action.extra.get('icon', None):
        return action.extra.orig_display_name

    attrs = action.extra.icon_attrs
    attrs['class'][action.extra.get('icon_prefix', '') + action.extra.icon] = True

    return format_html('<i{}></i> {}', render_attrs(attrs), action.extra.orig_display_name or capitalize(action._name).replace('_', ' '))


def group_actions(actions: Dict[str, Action]):
    actions_with_group = (action for action in values(actions) if action.group is not None)

    grouped_actions: List[Tuple[str, str, List[Action]]] = [
        (group_name, slugify(group_name), list(actions_in_group))
        for group_name, actions_in_group in groupby(actions_with_group, key=lambda x: x.group)
    ]

    for _, _, actions_in_group in grouped_actions:
        for action in actions_in_group:
            action.attrs.role = 'menuitem'
            action.attrs['class']['dropdown-item'] = True

    actions_without_group = [action for action in values(actions) if action.group is None]
    return actions_without_group, grouped_actions


class Actions(Members, Tag):
    attrs: Attrs = SpecialEvaluatedRefinable()
    tag = EvaluatedRefinable()
