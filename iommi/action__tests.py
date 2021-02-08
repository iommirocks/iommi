import pytest
from tri_declarative import (
    dispatch,
    get_members,
    is_shortcut,
    Shortcut,
)
from tri_struct import Struct

from iommi import (
    Action,
    Column,
    Table,
)
from iommi._web_compat import Template
from iommi.action import group_actions
from iommi.base import (
    items,
    keys,
)
from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.traversable import (
    Traversable,
)
from tests.helpers import (
    prettify,
    verify_table_html,
)


def assert_renders(action, html):
    assert prettify(action.__html__()) == prettify(html)


def test_render():
    action = Action(_name='do_it', attrs__href='#').bind()
    assert_renders(
        action,
        '''
        <a href="#"> Do it </a>
    ''',
    )


def test_render_input():
    action = Action(_name='do_it', tag='input', attrs__href='#').bind()
    assert_renders(
        action,
        '''
        <input href="#" value="Do it">
    ''',
    )


def test_render_class():
    action = Action(_name='do_it', attrs__class__foo=True).bind()
    assert_renders(
        action,
        '''
        <a class="foo">Do it</a>
    ''',
    )


def test_render_button():
    submit = Action.button(_name='do_it').bind()
    assert_renders(
        submit,
        '''
       <button> Do it </button>
    ''',
    )


def test_render_submit():
    submit = Action.submit(display_name='Do it').bind()
    assert_renders(
        submit,
        '''
       <button accesskey="s" name="-">Do it</button>
    ''',
    )


def test_render_icon():
    submit = Action.icon(
        icon='flower',
        display_name='Name',
    ).bind()
    assert_renders(
        submit,
        '''
       <a> <i class="fa fa-flower"> </i> Name </a>
    ''',
    )


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

    all_shortcut_names = keys(
        get_members(
            cls=MyFancyAction,
            member_class=Shortcut,
            is_member=is_shortcut,
        )
    )

    thing = ThingWithActions(
        actions__action_of_type_icon__icon='flower',
        **{f'actions__action_of_type_{t}__call_target__attribute': t for t in all_shortcut_names},
    ).bind()

    for name, column in items(thing.actions):
        assert column.extra.get('fancy'), name


def test_template():
    assert Action(template=Template('{{action.group}}'), group='foo').bind(request=None).__html__() == 'foo'


def test_delete_action():
    assert Action.delete().bind(request=None).__html__() == '<button accesskey="s" name="-">Submit</button>'


def test_icon_action():
    assert Action.icon('foo', display_name='dn').bind(request=None).__html__() == '<a><i class="fa fa-foo"></i> dn</a>'


def test_icon_action_with_icon_classes():
    assert (
        Action.icon('foo', display_name='dn', icon_classes=['a', 'b']).bind(request=None).__html__()
        == '<a><i class="fa fa-foo fa-a fa-b"></i> dn</a>'
    )


def test_display_name_to_value_attr():
    assert (
        Action.delete(display_name='foo').bind(request=None).__html__() == '<button accesskey="s" name="-">foo</button>'
    )


def test_lambda_tag():
    assert Action(tag=lambda action, **_: 'foo', display_name='').bind(request=None).__html__() == '<foo></foo>'


def test_action_groups():
    non_grouped, grouped = group_actions(
        dict(
            a=Action(),
            b=Action(),
            c=Action(group='a'),
            d=Action(group='a'),
            e=Action(group='a'),
            f=Action(group='b'),
            g=Action(group='b'),
        )
    )
    assert len(non_grouped) == 2
    assert len(grouped) == 2
    assert len(grouped[0][2]) == 3
    assert len(grouped[1][2]) == 2


def test_actions():
    class TestTable(Table):
        foo = Column(header__attrs__title="Some title")

        class Meta:
            sortable = False
            actions = dict(
                a=Action(display_name='Foo', attrs__href='/foo/', include=lambda table, **_: table.rows is not rows),
                b=Action(display_name='Bar', attrs__href='/bar/', include=lambda table, **_: table.rows is rows),
                c=Action(display_name='Baz', attrs__href='/bar/', group='Other'),
                d=dict(display_name='Qux', attrs__href='/bar/', group='Other'),
                e=Action.icon('icon_foo', display_name='Icon foo', attrs__href='/icon_foo/'),
                f=Action.icon('icon_bar', icon_classes=['lg'], display_name='Icon bar', attrs__href='/icon_bar/'),
                g=Action.icon(
                    'icon_baz', icon_classes=['one', 'two'], display_name='Icon baz', attrs__href='/icon_baz/'
                ),
            )

    rows = [Struct(foo="foo")]

    verify_table_html(
        table=TestTable(rows=rows),
        find=dict(class_='links'),
        expected_html="""
        <div class="links">
            <div class="btn-group">
                <button class="btn btn-primary dropdown-toggle" data-target="#" data-toggle="dropdown" href="/page.html" id="id_dropdown_other" role="button" type="button">
                    Other
                </button>
                <div aria-labelledby="id_dropdown_Other" class="dropdown-menu" role="menu">
                    <a class="dropdown-item" href="/bar/" role="menuitem"> Baz </a>
                    <a class="dropdown-item" href="/bar/" role="menuitem"> Qux </a>
                </div>
            </div>

            <a href="/bar/"> Bar </a>

            <a href="/icon_foo/"> <i class="fa fa-icon_foo " /> Icon foo </a>
            <a href="/icon_bar/"> <i class="fa fa-icon_bar fa-lg" /> Icon bar </a>
            <a href="/icon_baz/"> <i class="fa fa-icon_baz fa-one fa-two" /> Icon baz </a>
        </div>""",
    )


def test_check_for_bad_value_usage():
    with pytest.raises(AssertionError) as e:
        Action(tag='button', attrs__value='foo')

    assert str(e.value) == 'You passed attrs__value, but you should pass display_name'
