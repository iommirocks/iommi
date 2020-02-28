import pytest
from tri_declarative import (
    declarative,
    dispatch,
    Refinable,
)

from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.traversable import (
    Traversable,
    declared_members,
    dispatch2,
)


class Fruit(Traversable):
    def __init__(self, taste=None, **kwargs):
        super(Fruit, self).__init__(**kwargs)
        self.taste = taste


@declarative(Fruit, 'fruits_dict')
class Basket(Traversable):

    @dispatch2
    def __init__(self, fruits=None, fruits_dict=None):
        super(Basket, self).__init__()
        collect_members(container=self, name='fruits', items=fruits, items_dict=fruits_dict, cls=Fruit)

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
    assert basket._declared_members.fruits.pear.taste == 'meh'


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

    assert str(e.value) == "'Fruit' object has no refinable attribute(s): color.\nAvailable attributes:\n    iommi_style"


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


def test_inclusion():
    class IncludableFruit(Fruit):
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
    assert Admin.header._unapplied_config == {}
    assert b.parts.header._unapplied_config == {}
    assert '#foo#' in a.__html__()
    assert '#foo#' not in b.__html__()
