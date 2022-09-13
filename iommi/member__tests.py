import pytest

from iommi import (
    Fragment,
    html,
    Page,
    register_style,
    Style,
)
from iommi.declarative.with_meta import with_meta
from iommi.member import ForbiddenNamesException
from iommi.refinable import Refinable
from iommi.shortcut import with_defaults
from tests.helpers import (
    Basket,
    Fruit,
)


def test_empty_collect():
    assert Basket().refine_done().iommi_namespace.fruits == {}


def test_collect_from_arg():
    basket = Basket(fruits__banana__taste="sweet").refine_done()
    assert basket.iommi_namespace.fruits.banana.taste == 'sweet'


def test_collect_from_declarative():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    basket = MyBasket().refine_done()
    assert basket.iommi_namespace.fruits.orange.taste == 'sour'


def test_collect_from_both():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    basket = MyBasket(fruits__banana__taste="sweet").refine_done()
    assert basket.iommi_namespace.fruits.banana.taste == 'sweet'
    assert basket.iommi_namespace.fruits.orange.taste == 'sour'


def test_collect_unapplied_config():
    class MyBasket(Basket):
        pear = Fruit()

    basket = MyBasket(fruits__pear__taste='meh').refine_done()
    assert basket.iommi_namespace.fruits.pear.taste == 'meh'


def test_unbound_error():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    basket = MyBasket().refine_done()
    assert basket.fruits is None


def test_empty_bind():
    basket = Basket().bind()
    assert basket.fruits == {}


def test_bind_from_arg():
    basket = Basket(fruits__banana__taste="sweet").bind()
    assert basket.fruits.banana.taste == 'sweet'


def test_bind_from_declarative():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    basket = MyBasket().bind()
    assert basket.fruits.orange.taste == 'sour'


def test_bind_via_unapplied_config():
    class MyBasket(Basket):
        pear = Fruit()

    basket = MyBasket(fruits__pear__taste='meh').bind()
    assert basket.fruits.pear.taste == 'meh'

    with pytest.raises(
        TypeError,
        match=(
            r'Fruit object has no refinable attribute\(s\): "color"\.\n'
            r'Available attributes:\n'
            r'    assets\n'
            r'    endpoints\n'
            r'    iommi_style\n'
            r'    taste\n'
        ),
    ):
        MyBasket(fruits__pear__color='green').bind()


def test_ordering():
    class OrderFruit(Fruit):
        after = Refinable()

    class MyBasket(Basket):
        banana = OrderFruit()
        pear = OrderFruit()
        orange = OrderFruit()

    basket = MyBasket(
        fruits__orange__after=0,
        fruits__banana__after='pear',
    ).bind()

    assert list(basket.fruits.keys()) == ['orange', 'pear', 'banana']
    assert basket._bound_members['fruits']._bound_members is basket.fruits


def test_inclusion():
    @with_meta
    class IncludableFruit(Fruit):
        include = Refinable()

        class Meta:
            include = True

    class MyBasket(Basket):
        banana = IncludableFruit()
        pear = IncludableFruit()
        orange = IncludableFruit(include=False)

    basket = MyBasket(
        fruits__banana__include=False,
    ).bind()

    assert list(basket.fruits.keys()) == ['pear']


def test_unapplied_config_does_not_remember_simple():
    from iommi import Page
    from iommi import html

    class MyPage(Page):
        link = html.a('Admin')

    a = MyPage(parts__link__attrs__href='#foo#').bind()
    b = MyPage().bind()
    assert '#foo#' in a.__html__()
    assert '#foo#' not in b.__html__()


def test_override_grandchild():
    class MyPage(Page):
        foo = Fragment(Fragment('bar'), tag='h1')

    assert MyPage(parts__foo__children__text__tag='span').bind().__html__() == '<h1><span>bar</span></h1>'


def test_unapplied_config_does_not_remember():
    from iommi import Page
    from iommi import html

    class MyPage(Page):
        header = html.h1(children__link=html.a('Admin'))

    a = MyPage(parts__header__children__link__attrs__href='#foo#').bind()
    b = MyPage().bind()
    assert '#foo#' in a.__html__()
    assert '#foo#' not in b.__html__()


@pytest.fixture
def foo_style():
    style = Style(
        Page__extra__foo='from style',
        Page__parts__foo=html.div('from style'),
    )

    with register_style('foo', style):
        yield style


def test_precedence(foo_style):
    class MyPage(Page):
        pass

    my_page = MyPage(iommi_style='foo').bind()
    assert my_page.extra.foo == 'from style'
    assert str(my_page) == '<div>from style</div>'


def test_precedence_override_style(foo_style):
    class MyPage(Page):
        class Meta:
            extra__foo = 'from declaration'

    my_page = MyPage(iommi_style='foo').bind()
    assert my_page.extra.foo == 'from declaration'


@pytest.mark.skip(reason='Does not work yet. Is this a too acrobatic override?')
def test_precedence_override_style_acrobatic(foo_style):
    class MyPage(Page):
        foo = html.div('from declaration')

    my_page = MyPage(iommi_style='foo').bind()
    assert str(my_page) == '<div>from declaration</div>'


def test_precedence_override_meta(foo_style):
    class MyPage(Page):
        foo = html.div('from declaration')

        class Meta:
            parts__foo = html.div('from class Meta')
            extra__foo = 'from class Meta'

    my_page = MyPage(iommi_style='foo').bind()
    assert my_page.extra.foo == 'from class Meta'
    assert str(my_page) == '<div>from class Meta</div>'

    my_page = MyPage(
        iommi_style='foo',
        extra__foo='from constructor call',
        parts__foo=html.div('from constructor call'),
    ).bind()

    assert my_page.extra.foo == 'from constructor call'
    assert str(my_page) == '<div>from constructor call</div>'


def test_precedence_override_shortcut(foo_style):
    class MyPage(Page):
        foo = html.div('from declaration')

        @classmethod
        @with_defaults(
            extra__foo='from shortcut',
            parts__foo=html.div('from shortcut'),
        )
        def shortcut(cls, **kwargs):
            return cls(**kwargs)

    my_page = MyPage.shortcut().bind()
    assert my_page.extra.foo == 'from shortcut'
    assert str(my_page) == '<div>from shortcut</div>'

    my_page = MyPage.shortcut(iommi_style='foo').bind()
    assert my_page.extra.foo == 'from style'
    assert str(my_page) == '<div>from style</div>'

    my_page = MyPage.shortcut(
        iommi_style='foo',
        extra__foo='from constructor call',
        parts__foo=html.div('from constructor call'),
    ).bind()
    assert my_page.extra.foo == 'from constructor call'
    assert str(my_page) == '<div>from constructor call</div>'


def test_precedence_override_style_with_shortcut(foo_style):
    bar_style = Style(
        foo_style,
        Page__shortcuts__shortcut__extra__foo='from style',
        Page__shortcuts__shortcut__parts__foo=html.div('from style'),
    )

    with register_style('bar', bar_style):

        class MyPage(Page):
            foo = html.div('from declaration')

            @classmethod
            @with_defaults(
                extra__foo='from shortcut',
                parts__foo=html.div('from shortcut'),
            )
            def shortcut(cls, **kwargs):
                return cls(**kwargs)

        my_page = MyPage.shortcut().bind()
        assert my_page.extra.foo == 'from shortcut'
        assert str(my_page) == '<div>from shortcut</div>'

        my_page = MyPage.shortcut(iommi_style='bar').bind()
        assert my_page.extra.foo == 'from style'
        assert str(my_page) == '<div>from style</div>'

        my_page = MyPage.shortcut(
            iommi_style='bar',
            extra__foo='from constructor call',
            parts__foo=html.div('from constructor call'),
        ).bind()
        assert my_page.extra.foo == 'from constructor call'
        assert str(my_page) == '<div>from constructor call</div>'


def test_lazy_bind():
    class ExplodingFruit(Fruit):
        def on_bind(self):
            raise Exception('Boom')

    class MyBasket(Basket):
        tasty_banana = Fruit(taste='sweet')
        exploding_orange = ExplodingFruit(taste='strange')

    my_basket = MyBasket().bind()
    assert my_basket.fruits.tasty_banana.taste == 'sweet'

    with pytest.raises(Exception, match='Boom'):
        # noinspection PyStatementEffect
        my_basket.fruits.exploding_orange


def test_lazy_repr():
    class MyBasket(Basket):
        banana = Fruit(taste='sweet')
        orange = Fruit(taste='strange')

    my_basket = MyBasket().bind()
    # noinspection PyStatementEffect
    my_basket.fruits.banana
    assert repr(my_basket.fruits) == '<MemberBinder: banana (bound), orange>'
    assert str(my_basket.fruits) == '<MemberBinder: banana (bound), orange>'


def test_forbidden_names():
    class MyBasket(Basket):
        _name = Fruit()
        iommi_style = Fruit()

    with pytest.raises(
        ForbiddenNamesException, match='The names _name, iommi_style are reserved by iommi, please pick other names'
    ):
        MyBasket().refine_done()


def test_collect_sets_name():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    basket = MyBasket().refine_done()
    assert basket.iommi_namespace.fruits.orange._name == 'orange'

    basket = MyBasket(fruits__orange=Fruit(taste='sour')).refine_done()
    assert basket.iommi_namespace.fruits.orange._name == 'orange'


def test_none_members_should_be_discarded_after_being_allowed_through():
    class MyBasket(Basket):
        orange = Fruit()

    basket = MyBasket(fruits__orange=None).refine_done()
    assert 'orange' not in basket.iommi_namespace.fruits
    assert basket.fruits.orange is None


def test_bind_not_reorder():
    class MyBasket(Basket):
        banana = Fruit()
        orange = Fruit()

    my_basket = MyBasket().bind()
    # noinspection PyStatementEffect
    my_basket.fruits.orange
    assert list(my_basket.fruits.keys()) == ['banana', 'orange']


def test_unknown_attribute():
    class MyBasket(Basket):
        orange = Fruit()
        banana = Fruit()

    my_basket = MyBasket().bind()
    with pytest.raises(
        AttributeError,
        match=(
            r"'MemberBinder' object has no member 'fruit_fly'\.\n"
            r"Available members:\n"
            r"    banana\n"
            r"    orange\n"
        ),
    ):
        # noinspection PyStatementEffect
        my_basket.fruits.fruit_fly
