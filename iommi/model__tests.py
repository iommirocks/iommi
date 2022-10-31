import pytest
from django.db.models import (
    AutoField,
    CASCADE,
    Max,
    OneToOneField,
)

from iommi.model import IommiModel
from tests.models import (
    MyAnnotatedIommiModel,
    MyIommiModel,
    NoRaceConditionModel,
    RaceConditionModel,
)


def test_model():
    m = MyIommiModel(foo=17)
    assert m.foo == 17

    assert m.get_updated_fields() == {'foo'}


def test_constructor_exception():
    with pytest.raises(TypeError):
        MyIommiModel(bar=17)


def test_attribute_exception():
    m = MyIommiModel()
    m._bar = 17
    with pytest.raises(TypeError):
        m.bar = 17


def test_reversed():
    class MyOtherModel(IommiModel):
        bar = OneToOneField(MyIommiModel, related_name='other', on_delete=CASCADE)

    o = MyOtherModel(bar=MyIommiModel())
    o.bar = MyIommiModel()

    MyIommiModel().other = MyOtherModel()


def test_updated_fields():
    m = MyIommiModel()
    m.foo = 17

    assert m.get_updated_fields() == {'foo'}


def test_ignore_pk_field():
    class WeirdPKNameModel(IommiModel):
        this_is_a_pk = AutoField(primary_key=True)

    m = WeirdPKNameModel()

    assert m.get_updated_fields() == set()


@pytest.mark.django_db
def test_race_condition_on_save():
    m = RaceConditionModel.objects.create(a=1, b=2)
    m2 = RaceConditionModel.objects.get(pk=m.pk)
    m2.b = 7
    m2.save()

    m.a = 17
    m.save()  # This save() overwrites the value of b
    assert RaceConditionModel.objects.get(pk=m.pk).b == 2


@pytest.mark.django_db
def test_no_race_condition_on_save():
    m = NoRaceConditionModel.objects.create(a=1, b=2)
    m2 = NoRaceConditionModel.objects.get(pk=m.pk)
    assert m2.get_updated_fields() == set()
    m2.b = 7
    assert m2.get_updated_fields() == {'b'}
    m2.save()

    m.a = 17
    assert m.get_updated_fields() == {'a'}
    m.save()  # This save() does NOT overwrite b!
    assert NoRaceConditionModel.objects.get(pk=m.pk).b == 7
    assert not m.get_updated_fields()


@pytest.mark.django_db
def test_annotation():
    MyIommiModel.objects.create(foo=2)
    with pytest.raises(TypeError):
        MyIommiModel.objects.annotate(fisk=Max('foo')).get()

    MyAnnotatedIommiModel.objects.create(foo=2)
    MyAnnotatedIommiModel.objects.annotate(fisk=Max('foo')).get()


@pytest.mark.django_db
def test_force_insert():
    MyIommiModel.objects.create(pk=3, foo=1)
