import pytest
from tri_declarative import (
    declarative,
    dispatch,
    Refinable,
)

from iommi.base import (
    items,
    keys,
    values,
)
from iommi.member import (
    bind_members,
    collect_members,
    ForbiddenNamesException,
    NotBoundYetException,
)
from iommi.reinvokable import reinvokable
from iommi.traversable import (
    declared_members,
    Traversable,
)


class Fruit(Traversable):
    @reinvokable
    def __init__(self, taste=None, **kwargs):
        super(Fruit, self).__init__(**kwargs)
        self.taste = taste


@declarative(Fruit, 'fruits_dict')
class Basket(Traversable):
    @dispatch
    def __init__(self, fruits=None, fruits_dict=None, unknown_types_fall_through=False):
        super(Basket, self).__init__()
        collect_members(
            container=self,
            name='fruits',
            items=fruits,
            items_dict=fruits_dict,
            cls=Fruit,
            unknown_types_fall_through=unknown_types_fall_through,
        )

    def on_bind(self):
        bind_members(parent=self, name='fruits')


def test_empty_collect():
    assert declared_members(Basket()).fruits == {}


def test_collect_from_arg():
    basket = Basket(fruits__banana__taste="sweet")
    assert declared_members(basket).fruits.banana.taste == 'sweet'


def test_collect_from_declarative():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    basket = MyBasket()
    assert declared_members(basket).fruits.orange.taste == 'sour'


def test_collect_unapplied_config():
    class MyBasket(Basket):
        pear = Fruit()

    basket = MyBasket(fruits__pear__taste='meh')
    # noinspection PyUnresolvedReferences
    assert basket._declared_members.fruits.pear.taste == 'meh'


def test_unbound_error():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    expected = 'fruits of MyBasket is not bound, look in _declared_members[fruits] for the declared copy of this, or bind first'

    basket = MyBasket()
    assert repr(basket.fruits) == expected

    with pytest.raises(NotBoundYetException) as e:
        items(basket.fruits)

    with pytest.raises(NotBoundYetException) as e2:
        str(basket.fruits)

    with pytest.raises(NotBoundYetException) as e3:
        keys(basket.fruits)

    with pytest.raises(NotBoundYetException) as e4:
        values(basket.fruits)

    with pytest.raises(NotBoundYetException) as e5:
        for _ in basket.fruits:
            pass  # pragma: no cover as it is supposed to raise on iter

    assert str(e.value) == str(e2.value) == str(e3.value) == str(e4.value) == str(e5.value)
    assert str(e.value) == expected


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

    with pytest.raises(TypeError) as e:
        MyBasket(fruits__pear__color='green').bind()

    assert (
        str(e.value) == "'Fruit' object has no refinable attribute(s): color.\nAvailable attributes:\n    iommi_style"
    )


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
    class IncludableFruit(Fruit):
        @reinvokable
        def __init__(self, include=True, **kwargs):
            super(IncludableFruit, self).__init__(**kwargs)
            self.include = include

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

    class Admin(Page):
        link = html.a('Admin')

    a = Admin(parts__link__attrs__href='#foo#').bind()
    b = Admin().bind()
    assert '#foo#' in a.__html__()
    assert '#foo#' not in b.__html__()


def test_unapplied_config_does_not_remember():
    from iommi import Page
    from iommi import html

    class Admin(Page):
        header = html.h1(children__link=html.a('Admin'))

    a = Admin(parts__header__children__link__attrs__href='#foo#').bind()
    b = Admin().bind()
    assert '#foo#' in a.__html__()
    assert '#foo#' not in b.__html__()


def test_lazy_bind():
    class ExplodingFruit(Fruit):
        def on_bind(self):
            raise Exception('Boom')

    class MyBasket(Basket):
        tasty_banana = Fruit(taste='sweet')
        exploding_orange = ExplodingFruit(taste='strange')

    my_basket = MyBasket().bind()
    assert my_basket.fruits.tasty_banana.taste == 'sweet'

    with pytest.raises(Exception) as e:
        # noinspection PyStatementEffect
        my_basket.fruits.exploding_orange
    assert 'Boom' in str(e.value)


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

    with pytest.raises(ForbiddenNamesException) as e:
        MyBasket()

    assert str(e.value) == 'The names _name, iommi_style are reserved by iommi, please pick other names'


def test_collect_sets_name():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    basket = MyBasket()
    assert declared_members(basket).fruits.orange._name == 'orange'

    basket = MyBasket(fruits__orange=Fruit(taste='sour'))
    assert declared_members(basket).fruits.orange._name == 'orange'


def test_none_members_should_be_discarded_after_being_allowed_through():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    basket = MyBasket(fruits__orange=None)
    assert 'orange' not in declared_members(basket).fruits


def test_bind_not_reorder():
    class MyBasket(Basket):
        banana = Fruit(taste='sweet')
        orange = Fruit(taste='strange')

    my_basket = MyBasket().bind()
    # noinspection PyStatementEffect
    my_basket.fruits.orange
    assert list(my_basket.fruits.keys()) == ['banana', 'orange']
