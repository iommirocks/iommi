from iommi._web_compat import Template
from tri_declarative import (
    dispatch,
    get_members,
    is_shortcut,
    Shortcut,
)

from iommi import Action
from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.traversable import (
    Traversable,
)
from tests.helpers import prettify


def assert_renders(action, html):
    assert prettify(action.__html__()) == prettify(html)


def test_render():
    action = Action(
        _name='do_it',
        attrs__href='#'
    ).bind()
    assert_renders(action, '''
        <a href="#"> Do it </a>
    ''')


def test_render_input():
    action = Action(
        _name='do_it',
        tag='input',
        attrs__href='#'
    ).bind()
    assert_renders(action, '''
        <input href="#" value="Do it">
    ''')


def test_render_class():
    action = Action(
        _name='do_it',
        attrs__class__foo=True
    ).bind()
    assert_renders(action, '''
        <a class="foo">Do it</a>
    ''')


def test_render_button():
    submit = Action.button(_name='do_it').bind()
    assert_renders(submit, '''
       <button> Do it </button>
    ''')


def test_render_submit():
    submit = Action.submit(_name='do_it').bind()
    assert_renders(submit, '''
       <input accesskey="s" name="-" type="submit" value="Do it"/>
    ''')


def test_render_icon():
    submit = Action.icon(
        icon='flower',
        display_name='Name',
    ).bind()
    assert_renders(submit, '''
       <a> <i class="fa fa-flower"> </i> Name </a>
    ''')


def test_all_action_shortcuts():
    class MyFancyAction(Action):
        class Meta:
            extra__fancy = True

    class ThingWithActions(Traversable):
        @dispatch
        def __init__(self, actions):
            super(ThingWithActions, self).__init__()
            collect_members(self, name='actions', items=actions, cls=MyFancyAction)

        def on_bind(self):
            bind_members(self, name='actions')

    all_shortcut_names = get_members(
        cls=MyFancyAction,
        member_class=Shortcut,
        is_member=is_shortcut,
    ).keys()

    thing = ThingWithActions(
        actions__action_of_type_icon__icon='flower',
        **{
            f'actions__action_of_type_{t}__call_target__attribute': t
            for t in all_shortcut_names
        },
    ).bind()

    for name, column in thing.actions.items():
        assert column.extra.get('fancy'), name


def test_template():
    assert Action(template=Template('{{action.group}}'), group='foo').bind(request=None).__html__() == 'foo'


def test_delete_action():
    assert Action.delete().bind(request=None).__html__() == '<input accesskey="s" name="-" type="submit" value="Root">'


def test_icon_action():
    assert Action.icon('foo', display_name='dn').bind(request=None).__html__() == '<a><i class="fa fa-foo"></i> dn</a>'


def test_icon_action_with_icon_classes():
    assert Action.icon('foo', display_name='dn', icon_classes=['a', 'b']).bind(request=None).__html__() == '<a><i class="fa fa-foo fa-a fa-b"></i> dn</a>'


def test_display_name_to_value_attr():
    assert Action.delete(display_name='foo').bind(request=None).__html__() == '<input accesskey="s" name="-" type="submit" value="foo">'


def test_display_name_to_value_attr_but_attr_overrides():
    assert Action.delete(display_name='foo', attrs__value='bar').bind(request=None).__html__() == '<input accesskey="s" name="-" type="submit" value="bar">'


def test_lambda_tag():
    assert Action(tag=lambda action, **_: 'foo', display_name='').bind(request=None).__html__() == '<foo></foo>'
