import pytest
from tri_declarative import (
    declarative,
    dispatch,
)

from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.traversable import Traversable


class Fruit(Traversable):
    include = True

    def __init__(self, taste=None, **kwargs):
        super(Fruit, self).__init__(**kwargs)
        self.taste = taste


@declarative(Fruit, 'fruits_dict')
class Basket(Traversable):

    @dispatch
    def __init__(self, fruits=None, fruits_dict=None):
        super(Basket, self).__init__()
        collect_members(parent=self, name='fruits', items=fruits, items_dict=fruits_dict, cls=Fruit)

    def on_bind(self):
        bind_members(parent=self, name='fruits')


def test_empty_collect():
    assert Basket()._declared_members.fruits == {}


def test_collect_from_arg():
    bucket = Basket(fruits__banana__taste="sweet")
    assert bucket._declared_members.fruits.banana.taste == 'sweet'


def test_collect_from_declarative():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    bucket = MyBasket()
    assert bucket._declared_members.fruits.orange.taste == 'sour'


def test_collect_unapplied_config():
    class MyBasket(Basket):
        pear = Fruit()

    bucket = MyBasket(fruits__pear__taste='meh')
    assert bucket._unapplied_config == dict(fruits=dict(pear=dict(taste='meh')))


def test_bind_from_arg():
    bucket = Basket(fruits__banana__taste="sweet").bind()
    assert bucket.fruits.banana.taste == 'sweet'


def test_bind_from_declarative():
    class MyBasket(Basket):
        orange = Fruit(taste='sour')

    bucket = MyBasket().bind()
    assert bucket.fruits.orange.taste == 'sour'


def test_bind_via_unapplied_config():
    class MyBasket(Basket):
        pear = Fruit()

    bucket = MyBasket(fruits__pear__taste='meh').bind()
    assert bucket.fruits.pear.taste == 'meh'

    with pytest.raises(ValueError) as e:
        MyBasket(fruits__pear__color='green').bind()

    assert str(e.value) == 'Unable to set color on pear'


def test_ordering():
    class OrderFruit(Fruit):
        after = None

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
