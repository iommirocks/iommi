import itertools
from unittest import mock

import pytest
from django.test import override_settings

from iommi import Fragment
from iommi.attrs import (
    evaluate_attrs,
    render_attrs,
)
from iommi.declarative.namespace import Namespace
from iommi.evaluate import evaluate_strict
from iommi.struct import Struct


def render_attrs_test(attrs):
    return str(Fragment(attrs=attrs).bind().attrs)


def test_render_attrs():
    assert render_attrs_test(None) == ''
    assert render_attrs_test({'foo': 'bar', 'baz': 'quux'}) == ' baz="quux" foo="bar"'


def test_class_with_dunder():
    assert render_attrs_test(
        {
            'class__banana__foo': True,
            'class__banana__bar': lambda **_: True,
            'class__banana__baz': lambda **_: False,
        }
    ) == ' class="banana__bar banana__foo"'


def test_style_with_dunder():
    assert render_attrs_test({'style__banana__foo': 'fishy'}) == ' style="banana__foo: fishy"'


def test_render_class():
    assert (
        render_attrs_test({'apa': True, 'bepa': '', 'cepa': None, 'class': dict(foo=False, bar=True, baz=True)})
        == ' apa bepa="" class="bar baz"'
    )


def test_render_class_empty_special_case():
    assert render_attrs_test({'class': dict()}) == ''


def test_render_attrs_non_standard_types():
    assert render_attrs({'apa': True, 'bepa': '', 'cepa': None, 'class': 'bar baz'}) == ' apa bepa="" class="bar baz"'


def test_render_style():
    assert (
        render_attrs_test(
            dict(
                style=dict(
                    foo='1',
                    bar='2',
                )
            )
        )
        == ' style="bar: 2; foo: 1"'
    )


def test_render_style_fragment():
    f = Fragment(
        attrs__style=dict(
            foo='1',
            bar='2',
        )
    ).bind()
    assert str(f.attrs) == ' style="bar: 2; foo: 1"'


def test_render_with_empty():
    assert (
        render_attrs_test(
            dict(
                a='1',
                style={},
                z='2',
            )
        )
        == ' a="1" z="2"'
    )


def test_render_attrs_raises_for_some_common_pitfall_types():
    with pytest.raises(
        TypeError, match="Only the class and style attributes can be dicts, you sent {'a': 1} for key foo"
    ):
        render_attrs_test(dict(foo=dict(a=1)))

    with pytest.raises(TypeError, match="Attributes can't be of type list, you sent \\[] for key foo"):
        render_attrs_test(dict(foo=[]))

    with pytest.raises(TypeError, match="Attributes can't be of type tuple, you sent \\(\\) for key foo"):
        render_attrs_test(dict(foo=tuple()))

    with pytest.raises(TypeError, match="Attributes can't be callable, you sent foo=lambda foo: foo for key foo"):
        # fmt: off
        render_attrs(dict(
            foo=lambda foo: foo
        ))
        # fmt: on


def test_render_attrs_quote():
    assert (
        render_attrs_test(
            dict(
                a='"1"',
                b="'1'",
                style=dict(
                    foo='url("foo")',
                    bar="url('bar')",
                ),
            )
        )
        == ' a="&quot;1&quot;" b="\'1\'" style="bar: url(\'bar\'); foo: url(&quot;foo&quot;)"'
    )


def test_render_attrs_empty_class():
    assert (
        render_attrs_test(
            Namespace(
                class__foo=False,
                class__bar=False,
            )
        )
        == ''
    )


def test_render_attrs_empty_style():
    assert (
        render_attrs_test(
            Namespace(
                style__foo=None,
                style__bar=None,
            )
        )
        == ''
    )


def test_render_attrs_empty():
    assert render_attrs_test(Namespace()) == ''


def test_evaluate_attrs():
    class Foo:
        def __init__(self):
            self.attrs = Namespace(
                a=3,
                b=lambda foo: foo + 7,
                class__a=True,
                class__b=lambda foo: True,
                style__a=3,
                style__b=lambda foo: foo + 7,
            )

    expected = {
        'a': 3,
        'b': 8,
        'class': {
            'a': True,
            'b': True,
        },
        'style': {
            'a': 3,
            'b': 8,
        },
    }
    assert evaluate_attrs(Foo(), foo=1) == expected


def test_empty_class_and_struct_then_something():
    assert (
        str(
            evaluate_attrs(
                Struct(
                    attrs={
                        'class': {},
                        'style': {},
                        'z': 'bar',
                    }
                )
            )
        )
        == ' z="bar"'
    )


def test_empty_class_and_struct_after_eval_then_something():
    assert (
        render_attrs_test(
            {
                'class': {'foo': False},
                'style': {'foo': None},
                'z': 'bar',
            }
        )
        == ' z="bar"'
    )


def test_evaluate_attrs_2():
    actual = evaluate_attrs(
        Struct(
            attrs=Namespace(
                class__table=True,
                class__foo=lambda foo: True,
                data=1,
                data2=lambda foo: foo,
                style__foo=1,
                style__bar=lambda foo: f'foo{3}',
            ),
        ),
        foo=3,
    )

    expected = {
        'class': {
            'table': True,
            'foo': True,
        },
        'style': {'foo': 1, 'bar': 'foo3'},
        'data': 1,
        'data2': 3,
    }

    assert actual == expected


@override_settings(IOMMI_DEBUG=True)
def test_evaluate_attrs_show_debug_paths():
    actual = evaluate_attrs(
        Struct(
            attrs=Namespace(
                class__table=True,
            ),
            _name='foo',
            iommi_dunder_path='<path here>',
        ),
    )

    expected = {
        'class': {
            'table': True,
        },
        'style': {},
        'data-iommi-path': '<path here>',
        'data-iommi-type': 'Struct',
    }

    assert actual == expected


@override_settings(IOMMI_DEBUG=False)
def test_evaluate_attrs_hide_debug_paths():
    actual = evaluate_attrs(
        Struct(
            attrs=Namespace(
                class__table=True,
            ),
            _name='foo',
            iommi_dunder_path='<path here>',
        ),
    )

    expected = {
        'class': {
            'table': True,
        },
        'style': {},
    }

    assert actual == expected


def test_render_attrs_none():
    assert render_attrs(None) == ''


def test_empty_class_and_style_and_another():
    actual = render_attrs(
        attrs={
            'class': {},
            'style': {},
            'z': 'bar',
        },
    )

    expected = ' z="bar"'

    assert actual == expected


def test_class_style_callable():
    actual = evaluate_attrs(
        Namespace(
            attrs__class=lambda foo: {'foo' + foo: True},
            attrs__style=lambda foo: {'hey' + foo: 'yo'},
            _name='foo',
            iommi_dunder_path='<path here>',
        ),
        foo='bar',
    )

    expected = {
        'class': {
            'foobar': True,
        },
        'style': {
            'heybar': 'yo',
        },
    }

    assert actual == expected


def test_class_lambda():
    assert (
        render_attrs_test(
            {
                'class': lambda **_: {'foo': True},
                'style': lambda **_: {'bar': 'baz'},
            }
        )
        == ' class="foo" style="bar: baz"'
    )


def test_error_message_for_str_in_style():
    with pytest.raises(AssertionError) as e:
        evaluate_attrs(Namespace(attrs__style='display: none'))

    assert str(e.value).startswith('CSS styles')


def test_error_message_for_str_in_class():
    with pytest.raises(AssertionError) as e:
        evaluate_attrs(Namespace(attrs__class='foo bar'))

    assert str(e.value).startswith('CSS classes')


@mock.patch('iommi.evaluate.evaluate_strict')
def test_only_evaluate_callbacks(mock_evaluate_strict):
    counter = itertools.count()

    def side_effect(func_or_value, __signature=None, __match_empty=True, **kwargs):
        assert callable(func_or_value)
        next(counter)
        return evaluate_strict(
            func_or_value,
            __signature=__signature,
            __match_empty=__match_empty,
            **kwargs,
        )

    mock_evaluate_strict.side_effect = side_effect
    assert (
        render_attrs_test(
            {
                'apple': 'red',
                'banana': lambda **_: 'orange',
                'class': {'bar': lambda **_: True, 'foo': True},
                'style': {'fie': lambda **_: 'foe', 'fum': 'bink'},
            }
        )
        == ' apple="red" banana="orange" class="bar foo" style="fie: foe; fum: bink"'
    )
    assert next(counter) == 3
