import pytest
from tri_declarative import (
    class_shortcut,
    declarative,
    dispatch,
    EMPTY,
    Namespace,
    Refinable,
    with_meta,
)
from tri_struct import Struct

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
from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.page import (
    Page,
)
from iommi.reinvokable import reinvokable
from iommi.style import unregister_style
from iommi.traversable import (
    build_long_path_by_path,
    evaluated_refinable,
    EvaluatedRefinable,
    get_path_by_long_path,
    set_declared_member,
    Traversable,
)
from tests.helpers import (
    req,
    StubTraversable,
)
from tests.models import TFoo


def test_traverse():
    bar = Struct(
        _name='bar',
        _declared_members=dict(
            baz=Struct(_name='baz'),
            buzz=Struct(_name='buzz'),
        ),
    )
    foo = Struct(
        _name='foo',
        _declared_members=dict(
            bar=bar,
        ),
    )
    root = StubTraversable(
        _name='root',
        members=Struct(foo=foo),
    )

    expected = {
        '': '',
        'foo': 'foo',
        'bar': 'foo/bar',
        'baz': 'foo/bar/baz',
        'buzz': 'foo/bar/buzz',
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

    page = MyPage()

    actual = build_long_path_by_path(page)
    assert actual == {
        '': 'parts/header',
        'a_table': 'parts/a_table',
        'a_table/columns': 'parts/a_table/columns/columns',
        'a_table/fusk': 'parts/a_table/columns/fusk',
        'a_table/select': 'parts/a_table/columns/select',
        'advanced': 'parts/a_table/query/advanced',
        'columns': 'parts/a_table/query/form/fields/columns',
        'columns/config': 'parts/a_table/query/form/fields/columns/endpoints/config',
        'columns/validate': 'parts/a_table/query/form/fields/columns/endpoints/validate',
        'config': 'parts/some_form/fields/fisk/endpoints/config',
        'csv': 'parts/a_table/endpoints/csv',
        'errors': 'parts/a_table/query/endpoints/errors',
        'fisk': 'parts/some_form/fields/fisk',
        'fisk/config': 'parts/some_other_form/fields/fisk/endpoints/config',
        'fisk/validate': 'parts/some_other_form/fields/fisk/endpoints/validate',
        'fjomp': 'parts/some_other_form/fields/fjomp',
        'fjomp/config': 'parts/some_other_form/fields/fjomp/endpoints/config',
        'fjomp/validate': 'parts/some_other_form/fields/fjomp/endpoints/validate',
        'form': 'parts/a_table/query/form',
        'freetext_search': 'parts/a_table/query/form/fields/freetext_search',
        'freetext_search/config': 'parts/a_table/query/form/fields/freetext_search/endpoints/config',
        'freetext_search/validate': 'parts/a_table/query/form/fields/freetext_search/endpoints/validate',
        'fusk': 'parts/a_table/query/form/fields/fusk',
        'fusk/config': 'parts/a_table/query/form/fields/fusk/endpoints/config',
        'fusk/validate': 'parts/a_table/query/form/fields/fusk/endpoints/validate',
        'page': 'parts/a_table/parts/page',
        'query': 'parts/a_table/query',
        'query/columns': 'parts/a_table/query/filters/columns',
        'query/fusk': 'parts/a_table/query/filters/fusk',
        'query/select': 'parts/a_table/query/filters/select',
        'query_form_toggle_script': 'parts/a_table/assets/query_form_toggle_script',
        'select': 'parts/a_table/query/form/fields/select',
        'select/config': 'parts/a_table/query/form/fields/select/endpoints/config',
        'select/validate': 'parts/a_table/query/form/fields/select/endpoints/validate',
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
        ErrorMessages()

    assert (
        str(e.value)
        == 'The names bind, get_request, iommi_path, iommi_style, on_bind, own_evaluate_parameters are reserved by iommi, please pick other names'
    )


def test_warning_when_names_are_recalculated(capsys):
    page = Page(parts__foo=Fragment(_name='foo'))
    assert get_path_by_long_path(page) == {'parts/foo': ''}
    out, err = capsys.readouterr()
    assert out == ''

    set_declared_member(page, 'bar', Fragment(_name='bar'))
    assert get_path_by_long_path(page) == {
        'parts/foo': '',
        'bar': 'bar',
    }
    out, err = capsys.readouterr()
    assert out == '### A disturbance in the force... The namespace has been recalculated!\n'


def test_dunder_path_is_fully_qualified_and_skipping_root():
    foo = StubTraversable(
        _name='my_part3',
        members=Struct(
            my_part2=StubTraversable(
                _name='my_part2',
                members=Struct(
                    my_part=StubTraversable(
                        _name='my_part',
                    )
                ),
            )
        ),
    )
    foo = foo.bind(request=None)

    assert foo.iommi_path == ''

    assert foo.iommi_bound_members().my_part2.iommi_path == 'my_part2'
    assert foo.iommi_bound_members().my_part2.iommi_dunder_path == 'my_part2'

    assert foo.iommi_bound_members().my_part2.iommi_bound_members().my_part.iommi_path == 'my_part'
    assert foo.iommi_bound_members().my_part2.iommi_bound_members().my_part.iommi_dunder_path == 'my_part2__my_part'


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
    bar = StubTraversable(_name='bar')
    foo = StubTraversable(
        _name='foo',
        members=Struct(
            bar=bar,
        ),
    )

    assert repr(foo) == '<tests.helpers.StubTraversable foo>'
    assert repr(bar) == '<tests.helpers.StubTraversable bar>'

    foo = foo.bind(request=None)

    assert repr(foo) == "<tests.helpers.StubTraversable foo (bound) members:['bar']>"
    assert repr(foo._bound_members.bar) == "<tests.helpers.StubTraversable bar (bound) path:'bar'>"


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
        ),
    ), register_style(
        'bar_style',
        Style(
            MenuItem__attrs__class__bar=True,
        ),
    ):
        class MyPage(Page):
            menu = Menu(sub_menu=dict(root=MenuItem()))

        class OtherPage(Page):
            menu = MyPage.menu

        page = MyPage(iommi_style='foo_style').bind(request=Struct(path=''))
        assert page.parts.menu.sub_menu.root.attrs['class'] == dict(foo=True)

        page = OtherPage(iommi_style='bar_style').bind(request=Struct(path=''))
        assert page.parts.menu.sub_menu.root.attrs['class'] == dict(bar=True)


def test_get_config():
    with register_style(
        'fruit_style',
        Style(
            Fruit__attrs__class__style=True,
        ),
    ):
        class Fruit(Traversable):
            attrs = Refinable()

            @reinvokable
            @dispatch(
                attrs__class__fruit=True,
            )
            def __init__(self, **kwargs):
                super(Fruit, self).__init__(**kwargs)

            @classmethod
            @class_shortcut(
                attrs__class__some_fruit=True,
            )
            def some_fruit(cls, *, call_target=None, **kwargs):
                return call_target(**kwargs)

        class SubFruit(Fruit):
            @reinvokable
            @dispatch(
                attrs__class__sub_fruit=True,
            )
            def __init__(self, **kwargs):
                super(SubFruit, self).__init__(**kwargs)

            @classmethod
            @class_shortcut(
                call_target__attribute='some_fruit',
                attrs__class__sub_some_fruit=True,
            )
            def some_fruit(cls, *, call_target=None, **kwargs):
                return call_target(**kwargs)

        @declarative(Fruit, '_fruits_dict')
        @with_meta
        class Basket(Traversable):
            fruits = Refinable()

            class Meta:
                fruits__banana__attrs__class__basket = True

            @dispatch(
                fruits=EMPTY,
            )
            def __init__(self, *, _fruits_dict, fruits, **kwargs):
                super(Basket, self).__init__(**kwargs)
                collect_members(self, name='fruits', items_dict=_fruits_dict, items=fruits, cls=Fruit)

            def on_bind(self) -> None:
                bind_members(self, name='fruits')

        class SubBasket(Basket):
            class Meta:
                fruits__banana__attrs__class__sub_basket = True
                iommi_style = 'fruit_style'

        class MyBasket(SubBasket):
            banana = SubFruit.some_fruit(
                attrs__class__my_basket_fruit_invoke=True,
            )

        basket = MyBasket(fruits__banana__attrs__class__my_basket_invoke=True).bind(request=None)

        assert list(basket.fruits.banana.attrs['class'].keys()) == [
            'fruit',
            'sub_fruit',
            'style',
            'basket',
            'sub_basket',
            'my_basket_invoke',
            'some_fruit',
            'sub_some_fruit',
            'my_basket_fruit_invoke',
        ]
