import pytest

from iommi import (
    Page,
    Table,
)
from iommi.endpoint import find_target
from tests.helpers import req


def test_debug_tree_on_debug_false():
    class NestedPage(Page):
        foo = 'foo'

    class MyPage(Page):
        bar = 'bar'
        nested = NestedPage()

    root = MyPage().bind(request=req('get', **{'/debug_tree': '7'}))

    with pytest.raises(AssertionError):
        find_target(path='/debug_tree', root=root)


def test_debug_tree(settings):
    settings.DEBUG = True

    class NestedPage(Page):
        foo = 'foo'

    class MyPage(Page):
        bar = 'bar'
        nested = NestedPage()

    root = MyPage().bind(request=req('get', **{'/debug_tree': '7'}))
    target = find_target(path='/debug_tree', root=root)
    result = target.func(value='', **target._evaluate_parameters)

    assert isinstance(result, Table)
    tree = [
        ', '.join([str(x.value) for x in cells])
        for cells in result.cells_for_rows()
    ]
    expected = """, , MyPage, True
endpoints, None, Members[Endpoint], True
endpoints__debug_tree, debug_tree, Endpoint, True
parts, None, Members[Part], True
parts__bar, bar, Fragment, True
parts__bar__endpoints, None, Members, True
parts__bar__children, None, Members[str], True
parts__bar__children__text, None, str, False
parts__nested, nested, NestedPage, True
parts__nested__endpoints, None, Members[Endpoint], True
parts__nested__endpoints__debug_tree, nested/debug_tree, Endpoint, True
parts__nested__parts, None, Members[Part], True
parts__nested__parts__foo, foo, Fragment, True
parts__nested__parts__foo__endpoints, None, Members, True
parts__nested__parts__foo__children, None, Members[str], True
parts__nested__parts__foo__children__text, None, str, False"""
    assert '\n'.join(tree) == expected
