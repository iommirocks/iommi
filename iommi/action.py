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
from iommi.attrs import Attrs
from iommi.base import (
    capitalize,
    values,
)
from iommi.declarative.namespace import setdefaults_path
from iommi.declarative.with_meta import with_meta
from iommi.fragment import (
    Fragment,
    Tag,
)
from iommi.member import Members
from iommi.part import Part
from iommi.refinable import (
    EvaluatedRefinable,
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
        actions = [
        # @end

        # Link
        Action(attrs__href='http://example.com'),

        # Link with icon
        Action.icon('edit', attrs__href="edit/"),

        # Button
        Action.button(display_name='Button title!'),

        # A submit button
        Action.submit(display_name='Do this'),

        # The primary submit button on a form.
        Action.primary(),

        # @test
        ]

        from iommi.refinable import Prio
        foo = Page(
            parts={
                f'button_{i}': html.div(action.refine(display_name='Action', prio=Prio.shortcut))
                for i, action in enumerate(actions)
            }
        )
        show_output(foo)
        # @end

    Notice that because forms
    with a single primary submit button are so common, iommi assumes
    that if you have an action called submit and do NOT explicitly
    specify the action that it is a primary action. This is only
    done for the action called submit, inside the Forms actions
    Namespace.

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
    @with_defaults
    def icon(cls, icon, *, display_name=None, icon_classes=None, **kwargs):
        if icon_classes is None:
            icon_classes = []
        icon_classes_str = ' '.join(['fa-' + icon_class for icon_class in icon_classes]) if icon_classes else ''
        if icon_classes_str:
            icon_classes_str = ' ' + icon_classes_str
        setdefaults_path(
            kwargs,
            display_name=format_html('<i class="fa fa-{}{}"></i> {}', icon, icon_classes_str, display_name),
        )
        return cls(**kwargs)


def group_actions(actions: Dict[str, Action]):
    actions_with_group = (action for action in values(actions) if action.group is not None)

    grouped_actions: List[Tuple[str, str, List[Action]]] = [
        (group_name, slugify(group_name), list(actions_in_group))
        for group_name, actions_in_group in groupby(actions_with_group, key=lambda l: l.group)
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
