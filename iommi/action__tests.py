from typing import Dict

import pytest

from iommi import (
    Action,
    Column,
    Part,
    Style,
    Table,
)
from iommi._web_compat import Template
from iommi.action import (
    Actions,
    default_action__icon__display_name,
    group_actions,
)
from iommi.base import (
    items,
    keys,
)
from iommi.declarative import get_members
from iommi.member import (
    bind_members,
    refine_done_members,
)
from iommi.refinable import (
    Prio,
    RefinableMembers,
)
from iommi.shortcut import (
    Shortcut,
    is_shortcut,
)
from iommi.struct import Struct
from iommi.traversable import Traversable
from tests.helpers import (
    prettify,
    req,
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

    class ThingWithActions(Part):
        actions: Dict[str, Action] = RefinableMembers()

        def on_refine_done(self):
            refine_done_members(
                self,
                name='actions',
                members_from_namespace=self.actions,
                cls=MyFancyAction,
                members_cls=Actions,
            )
            super(ThingWithActions, self).on_refine_done()

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
    with pytest.raises(AssertionError):
        Action.icon('foo', display_name='dn', icon_classes=['a', 'b']).bind(request=None).__html__()


def test_display_name_to_value_attr():
    assert (
        Action.delete(display_name='foo').bind(request=None).__html__() == '<button accesskey="s" name="-">foo</button>'
    )


def test_lambda_tag():
    assert Action(tag=lambda action, **_: 'foo', display_name='').bind(request=None).__html__() == '<foo></foo>'


def test_action_groups():
    non_grouped, grouped = group_actions(
        dict(
            a=Action(_name='a').refine_done(),
            b=Action(_name='b').refine_done(),
            c=Action(_name='c', group='a').refine_done(),
            d=Action(_name='d', group='a').refine_done(),
            e=Action(_name='e', group='a').refine_done(),
            f=Action(_name='f', group='b').refine_done(),
            g=Action(_name='g', group='b').refine_done(),
        )
    )

    assert [x._name for x in non_grouped] == ['a', 'b']

    actual = [
        (a, b, [x._name for x in c])
        for a, b, c in grouped
    ]

    expected = [
        ('a', 'a', ['c', 'd', 'e']),
        ('b', 'b', ['f', 'g']),
    ]

    assert actual == expected

    grouped_items_flattened = [
        *grouped[0][-1],
        *grouped[1][-1],
    ]

    for x in grouped_items_flattened:
        assert x.attrs.role == 'menuitem'
        assert x.attrs['class'].get('dropdown-item', False)


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
                f=Action.icon('icon_bar', extra__icon_attrs__class={'fa-lg': True}, display_name='Icon bar', attrs__href='/icon_bar/'),
                g=Action.icon(
                    'icon_baz', extra__icon_attrs__class__one=True, extra__icon_attrs__class__two=True, display_name='Icon baz', attrs__href='/icon_baz/'
                ),
            )

    rows = [Struct(foo="foo")]

    verify_table_html(
        table=TestTable(rows=rows),
        find__class='links',
        # language=html
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
                <a href="/icon_baz/"> <i class="fa fa-icon_baz one two" /> Icon baz </a>
            </div>
        """,
    )


def test_check_for_bad_value_usage():
    with pytest.raises(AssertionError) as e:
        Action(tag='button', attrs__value='foo').refine_done()

    assert str(e.value) == 'You passed attrs__value, but you should pass display_name'


def test_action_icon_customization():
    assert 'fa-edit' in Action.icon('edit', attrs__href="edit/", display_name='Action').bind().__html__()
    assert 'Action' in Action.icon('edit', attrs__href="edit/", display_name='Action').bind().__html__()

    from iommi import Form
    f = Form(
        actions__foo=Action.icon('edit'),
    )
    assert 'Foo' in f.bind(request=req('get')).__html__()

    assert 'Action' in Action.icon('edit', attrs__href="edit/").refine(display_name='Action', prio=Prio.shortcut).bind().__html__()


def test_default_action__icon__display_name():
    assert default_action__icon__display_name(action=Action.icon(icon='', display_name='foo').bind()) == 'foo'
    assert default_action__icon__display_name(action=Action.icon(icon='icon', display_name='foo').bind()) == '<i class="fa fa-icon"></i> foo'
    assert default_action__icon__display_name(action=Action.icon(icon='foo', _name='foo_bar').bind()) == '<i class="fa fa-foo"></i> Foo bar'
    assert default_action__icon__display_name(action=Action.icon(iommi_style=Style(), icon='foo', _name='foo_bar').bind()) == '<i class="foo"></i> Foo bar'


def test_action_render():
    action = Action(display_name='Title', template='test_action_render.html').bind(request=req('get'))
    assert action.__html__().strip() == 'tag=a display_name=Title'


def test_action_submit_render():
    action = Action.submit(display_name='Title').bind(request=req('get'))
    assert action.__html__().strip() == '<button accesskey="s" name="-">Title</button>'


def test_action_repr():
    assert repr(Action(_name='name', template='test_link_render.html')) == '<iommi.action.Action name>'


def test_action_shortcut_icon():
    assert (
        Action.icon('foo', display_name='title').bind(request=None).__html__()
        == '<a><i class="fa fa-foo"></i> title</a>'
    )
