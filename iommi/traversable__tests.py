from typing import Dict

import pytest
from iommi.struct import Struct

from iommi import (
    Column,
    Field,
    Form,
    Fragment,
    Menu,
    MenuItem,
    register_style,
    Style,
    Table,
)
from iommi.base import (
    items,
    keys,
)
from iommi.declarative import declarative
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    Namespace,
)
from iommi.declarative.with_meta import with_meta
from iommi.member import (
    bind_members,
    refine_done_members,
)
from iommi.page import (
    Page,
)
from iommi.refinable import (
    evaluated_refinable,
    EvaluatedRefinable,
    Refinable,
    RefinableMembers,
)
from iommi.shortcut import (
    superinvoking_classmethod,
    with_defaults,
)
from iommi.traversable import (
    build_long_path_by_path,
    Traversable,
)
from tests.helpers import (
    Basket,
    Box,
    Fruit,
    req,
)
from tests.models import TFoo


def test_traverse():
    bar = Basket(
        fruits=dict(
            baz=Fruit(),
            buzz=Fruit(),
        ),
    )
    foo = Box(
        items__bar=bar,
    )
    root = Box(
        _name='root',
        items__foo=foo,
    ).refine_done()

    expected = {
        '': '',
        'foo': 'items/foo',
        'bar': 'items/foo/items/bar',
        'baz': 'items/foo/items/bar/fruits/baz',
        'buzz': 'items/foo/items/bar/fruits/buzz',
    }
    actual = build_long_path_by_path(root)
    assert items(actual) == items(expected)
    assert len(keys(actual)) == len(set(keys(actual)))


@pytest.mark.django_db
def test_traverse_on_iommi():
    class MyPage(Page):
        header = Fragment()
        some_form = Form(
            fields=Namespace(
                fisk=Field(),
            )
        )
        some_other_form = Form(
            fields=Namespace(
                fjomp=Field(),
                fisk=Field(),
            )
        )
        a_table = Table(
            model=TFoo,
            columns=Namespace(
                columns=Column(),
                fusk=Column(attr='b', filter__include=True),
            ),
        )

    page = MyPage().refine_done()
    actual = build_long_path_by_path(page)
    assert actual == {
        '': 'parts/header',
        'a_table': 'parts/a_table',
        'a_table/columns': 'parts/a_table/columns/columns',
        'a_table/fusk': 'parts/a_table/columns/fusk',
        'advanced': 'parts/a_table/query/advanced',
        'ajax_enhance': 'parts/a_table/query/assets/ajax_enhance',
        'bulk_container': 'parts/a_table/bulk_container',
        'columns': 'parts/a_table/query/form/fields/columns',
        'columns/config': 'parts/a_table/query/form/fields/columns/endpoints/config',
        'columns/help': 'parts/a_table/query/form/fields/columns/help',
        'columns/input': 'parts/a_table/query/form/fields/columns/input',
        'columns/label': 'parts/a_table/query/form/fields/columns/label',
        'columns/non_editable_input': 'parts/a_table/query/form/fields/columns/non_editable_input',
        'columns/validate': 'parts/a_table/query/form/fields/columns/endpoints/validate',
        'config': 'parts/some_form/fields/fisk/endpoints/config',
        'csv': 'parts/a_table/endpoints/csv',
        'debug_tree': 'endpoints/debug_tree',
        'errors': 'parts/a_table/query/endpoints/errors',
        'fisk': 'parts/some_form/fields/fisk',
        'fisk/config': 'parts/some_other_form/fields/fisk/endpoints/config',
        'fisk/help': 'parts/some_other_form/fields/fisk/help',
        'fisk/input': 'parts/some_other_form/fields/fisk/input',
        'fisk/label': 'parts/some_other_form/fields/fisk/label',
        'fisk/non_editable_input': 'parts/some_other_form/fields/fisk/non_editable_input',
        'fisk/validate': 'parts/some_other_form/fields/fisk/endpoints/validate',
        'fjomp': 'parts/some_other_form/fields/fjomp',
        'fjomp/config': 'parts/some_other_form/fields/fjomp/endpoints/config',
        'fjomp/help': 'parts/some_other_form/fields/fjomp/help',
        'fjomp/input': 'parts/some_other_form/fields/fjomp/input',
        'fjomp/label': 'parts/some_other_form/fields/fjomp/label',
        'fjomp/non_editable_input': 'parts/some_other_form/fields/fjomp/non_editable_input',
        'fjomp/validate': 'parts/some_other_form/fields/fjomp/endpoints/validate',
        'form': 'parts/a_table/query/form',
        'form_container': 'parts/a_table/query/form_container',
        'freetext_search': 'parts/a_table/query/form/fields/freetext_search',
        'freetext_search/config': 'parts/a_table/query/form/fields/freetext_search/endpoints/config',
        'freetext_search/help': 'parts/a_table/query/form/fields/freetext_search/help',
        'freetext_search/input': 'parts/a_table/query/form/fields/freetext_search/input',
        'freetext_search/label': 'parts/a_table/query/form/fields/freetext_search/label',
        'freetext_search/non_editable_input': 'parts/a_table/query/form/fields/freetext_search/non_editable_input',
        'freetext_search/validate': 'parts/a_table/query/form/fields/freetext_search/endpoints/validate',
        'fusk': 'parts/a_table/query/form/fields/fusk',
        'fusk/config': 'parts/a_table/query/form/fields/fusk/endpoints/config',
        'fusk/help': 'parts/a_table/query/form/fields/fusk/help',
        'fusk/input': 'parts/a_table/query/form/fields/fusk/input',
        'fusk/label': 'parts/a_table/query/form/fields/fusk/label',
        'fusk/non_editable_input': 'parts/a_table/query/form/fields/fusk/non_editable_input',
        'fusk/validate': 'parts/a_table/query/form/fields/fusk/endpoints/validate',
        'help': 'parts/some_form/fields/fisk/help',
        'input': 'parts/some_form/fields/fisk/input',
        'label': 'parts/some_form/fields/fisk/label',
        'header': 'parts/a_table/header',
        'non_editable_input': 'parts/some_form/fields/fisk/non_editable_input',
        'page': 'parts/a_table/parts/page',
        'query': 'parts/a_table/query',
        'query/columns': 'parts/a_table/query/filters/columns',
        'query/fusk': 'parts/a_table/query/filters/fusk',
        'query_form_toggle_script': 'parts/a_table/assets/query_form_toggle_script',
        'select': 'parts/a_table/columns/select',
        'some_form': 'parts/some_form',
        'some_other_form': 'parts/some_other_form',
        'some_other_form/fisk': 'parts/some_other_form/fields/fisk',
        'submit': 'parts/a_table/query/form/actions/submit',
        'table_js_select_all': 'parts/a_table/assets/table_js_select_all',
        'tbody': 'parts/a_table/endpoints/tbody',
        'toggle': 'parts/a_table/query/advanced/toggle',
        'validate': 'parts/some_form/fields/fisk/endpoints/validate',
    }
    assert len(actual.values()) == len(set(actual.values()))
    page = page.bind(request=req('get'))

    assert page.iommi_path == ''
    assert page.parts.header.iommi_path == 'header'
    assert page.parts.some_form.fields.fisk.iommi_path == 'fisk'
    assert page.parts.some_other_form.fields.fisk.iommi_path == 'some_other_form/fisk'
    assert page.parts.a_table.query.form.iommi_path == 'form'
    assert page.parts.a_table.query.form.fields.fusk.iommi_path == 'fusk'
    assert page.parts.a_table.columns.fusk.iommi_path == 'a_table/fusk'
    assert page._name == 'root'
    assert set(keys(page.iommi_evaluate_parameters())) == {'traversable', 'page', 'request'}


def test_evil_names_that_work():
    class EvilPage(Page):
        name = Fragment()
        parent = Fragment()
        path = Fragment()

    assert EvilPage().bind(request=req('get')).render_to_response().status_code == 200


def test_evil_names():
    class ErrorMessages(Page):
        bind = Fragment()
        iommi_style = Fragment()
        iommi_path = Fragment()
        iommi_dunderpath = Fragment()
        on_bind = Fragment()
        own_evaluate_parameters = Fragment()
        get_request = Fragment()

    with pytest.raises(Exception) as e:
        ErrorMessages().refine_done()

    assert (
        str(e.value)
        == 'The names bind, get_request, iommi_path, iommi_style, on_bind, own_evaluate_parameters are reserved by iommi, please pick other names'
    )


def test_dunder_path_is_fully_qualified_and_skipping_root():
    banana = Fruit()
    basket = Basket(fruits__banana=banana)
    root = basket.bind(request=None)

    assert root.iommi_path == ''

    assert root.iommi_bound_members().fruits.iommi_bound_members().banana.iommi_path == 'banana'
    assert root.iommi_bound_members().fruits.iommi_bound_members().banana.iommi_dunder_path == 'fruits__banana'


def test_evaluated_refinable_function():
    class Foo(Traversable):
        @staticmethod
        @evaluated_refinable
        def foo(**_):
            return 1

    f = Foo().bind(request=None)
    assert f.foo == 1


def test_extra_evaluated():
    class Foo(Traversable):
        extra_evaluated = Refinable()

        def own_evaluate_parameters(self):
            return dict(x=3)

    f = Foo(extra_evaluated__foo=lambda x, **_: x).bind(request=None)
    assert f.extra_evaluated.foo == 3


def test_attrs_evaluated():
    class Foo(Traversable):
        attrs = Refinable()

        def own_evaluate_parameters(self):
            return dict(x=3)

    f = Foo(attrs__foo=lambda x, **_: x).bind(request=None)
    assert f.attrs.foo == 3


def test_instance_in_eval_args():
    class Foo(Traversable):
        bar = EvaluatedRefinable()

    f = Foo(bar=lambda traversable, **_: traversable).bind(request=None)
    assert f.bar == f


def test_initial_setup():
    t = Traversable()
    assert t.iommi_name() is None
    assert t.iommi_parent() is None
    assert t._is_bound is False
    assert t.get_request() is None
    assert t.iommi_evaluate_parameters() is None


def test_traversable_repr():
    banana = Fruit(_name='banana')
    basket = Basket(_name='basket', fruits__banana=banana)

    assert repr(basket) == '<tests.helpers.Basket basket>'
    assert repr(banana) == '<tests.helpers.Fruit banana>'

    basket = basket.bind(request=None)

    assert repr(basket) == "<tests.helpers.Basket basket (bound) members:['fruits']>"
    assert repr(basket._bound_members.fruits) == "<iommi.member.Members fruits (bound) path:<no path>>"


def test_apply_style_not_affecting_definition(settings):
    with register_style(
        'my_style',
        Style(
            Fragment__attrs__class__foo=True,
        ),
    ), register_style(
        'other_style',
        Style(
            Fragment__attrs__class__bar=True,
        ),
    ):

        definition = Fragment()

        settings.IOMMI_DEFAULT_STYLE = 'my_style'
        fragment = definition.bind(request=None)
        assert fragment.attrs['class'] == dict(foo=True)

        settings.IOMMI_DEFAULT_STYLE = 'other_style'
        fragment = definition.bind(request=None)
        assert fragment.attrs['class'] == dict(bar=True)


def test_apply_style_not_affecting_definition_2():
    with register_style(
        'foo_style',
        Style(
            MenuItem__attrs__class__foo=True,
            MenuItem__active_class='active',
        ),
    ), register_style(
        'bar_style',
        Style(
            MenuItem__attrs__class__bar=True,
            MenuItem__active_class='active',
        ),
    ):

        class MyPage(Page):
            menu = Menu(sub_menu=dict(root=MenuItem()))

        class OtherPage(Page):
            menu = MyPage.menu

        page = MyPage(iommi_style='foo_style').bind(request=req('get'))
        assert page.parts.menu.sub_menu.root.attrs['class'] == dict(foo=True)

        page = OtherPage(iommi_style='bar_style').bind(request=req('get'))
        assert page.parts.menu.sub_menu.root.attrs['class'] == dict(bar=True)


def test_get_config():
    with register_style(
        'fruit_style',
        Style(
            Fruit__attrs__class__style=True,
        ),
    ):
        class FruitBase(Traversable):
            attrs = Refinable()

            @dispatch(
                attrs__class__fruit_base=True,
            )
            def __init__(self, **kwargs):
                super(FruitBase, self).__init__(**kwargs)

            @classmethod
            @with_defaults(
                attrs__class__fruit_shortcut_base=True,
            )
            def fruit_shortcut(cls, **kwargs):
                return cls(**kwargs)

        class Fruit(FruitBase):
            @dispatch(
                attrs__class__fruit=True,
            )
            def __init__(self, **kwargs):
                super(Fruit, self).__init__(**kwargs)

            @classmethod
            @superinvoking_classmethod
            @with_defaults(
                attrs__class__fruit_shortcut=True,
            )
            def fruit_shortcut(cls, super_classmethod=None, **kwargs):
                return super_classmethod(**kwargs)

        @declarative(Fruit, 'fruits', add_init_kwargs=False)
        @with_meta
        class BasketBase(Traversable):
            fruits: Dict = RefinableMembers()

            class Meta:
                fruits__banana__attrs__class__basket_base = True

            @dispatch(
                fruits=EMPTY,
            )
            def __init__(self, **kwargs):
                super(BasketBase, self).__init__(**kwargs)

            def on_refine_done(self):
                refine_done_members(self, name='fruits', members_from_namespace=self.fruits, members_from_declared=self.get_declared('fruits'), cls=Fruit)

            def on_bind(self) -> None:
                bind_members(self, name='fruits')

        class Basket(BasketBase):
            class Meta:
                fruits__banana__attrs__class__basket = True
                iommi_style = 'fruit_style'

        class MyBasket(Basket):
            banana = Fruit.fruit_shortcut(
                attrs__class__my_basket_fruit_invoke=True,
            )

        basket = MyBasket(fruits__banana__attrs__class__my_basket_invoke=True).bind(request=None)

        assert sorted(set(basket.fruits.banana.attrs['class'].keys())) == sorted({
            'fruit',
            'fruit_base',
            'style',
            'basket',
            'basket_base',
            'my_basket_invoke',
            'fruit_shortcut',
            'fruit_shortcut_base',
            'my_basket_fruit_invoke',
        })
