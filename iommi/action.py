from itertools import groupby
from typing import (
    Callable,
    Dict,
    List,
    Tuple,
)

from django.utils.translation import gettext_lazy
from tri_declarative import (
    class_shortcut,
    dispatch,
    EMPTY,
    Refinable,
    setdefaults_path,
    with_meta,
)

from iommi._web_compat import (
    format_html,
    slugify,
)
from iommi.attrs import Attrs
from iommi.base import (
    capitalize,
    values,
)
from iommi.fragment import (
    Fragment,
    Tag,
)
from iommi.member import Members
from iommi.part import Part
from iommi.reinvokable import reinvokable
from iommi.traversable import (
    EvaluatedRefinable,
)


@with_meta
class Action(Fragment):
    """
    The `Action` class describes buttons and links.

    Examples:

    .. code:: python

        # Link
        Action(attrs__href='http://example.com')

        # Link with icon
        Action.icon('edit', attrs__href="edit/")

        # Button
        Action.button(display_name='Button title!')

        # A submit button
        Action.submit(display_name='Do this')

        # The primary submit button on a form.
        Action.primary()

        # Notice that because forms
        # with a single primary submit button are so common, iommi assumes
        # that if you have a action called submit and do NOT explicitly
        # specify the action that it is a primary action. This is only
        # done for the action called submit, inside the Forms actions
        # Namespace.
        #
        # For that reason this works:

        class MyForm(Form):
            class Meta:
                @staticmethod
                def actions__submit__post_handler(form, **_):
                    if not form.is_valid():
                        return

                    ...

        # and is roughly equivalent to

        def on_submit(form, **_):
            if not form.is_valid():
                return

        class MyOtherForm(Form):
            class Meta:
                actions__submit = Action.primary(post_handler=on_submit)

    .. test
        r = req('post', **{'-submit': ''})
        MyForm().bind(request=r).render_to_response()
        MyOtherForm().bind(request=r).render_to_response()
    """

    group: str = EvaluatedRefinable()
    display_name: str = EvaluatedRefinable()
    post_handler: Callable = Refinable()

    @dispatch(
        tag='a',
        attrs=EMPTY,
        children=EMPTY,
        display_name=lambda action, **_: capitalize(action._name).replace('_', ' '),
    )
    @reinvokable
    def __init__(self, *, tag=None, attrs=None, children=None, display_name=None, **kwargs):
        if tag == 'input':
            if display_name and 'value' not in attrs:
                attrs.value = display_name
        else:
            children['text'] = display_name
            if tag == 'button' and 'value' in attrs:
                assert False, 'You passed attrs__value, but you should pass display_name'
        super().__init__(tag=tag, attrs=attrs, children=children, display_name=display_name, **kwargs)

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
    @class_shortcut(
        tag='button',
    )
    def button(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='button',
        attrs__accesskey='s',
        attrs__name=lambda action, **_: action.own_target_marker(),
        display_name=gettext_lazy('Submit'),
    )
    def submit(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='submit',
    )
    def primary(cls, call_target=None, **kwargs):
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
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    tag = EvaluatedRefinable()

    @dispatch(
        attrs__class=EMPTY,
        attrs__style=EMPTY,
    )
    @reinvokable
    def __init__(self, **kwargs):
        super(Actions, self).__init__(**kwargs)
