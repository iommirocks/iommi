from iommi.shortcut import Shortcut

from docs.models import *
from iommi import *
from tests.helpers import req

request = req('get')


def test_registrations():
    # language=rst
    """
    Registrations
    =============

    To make iommi understand the specifics of your code base you can register various handlers and behaviors.
    """
    

def test_django_custom_fields():
    # language=rst
    """
    Django custom fields
    ~~~~~~~~~~~~~~~~~~~~

    To tell iommi how to handle your custom fields you have these options:


    * `register_factory`: register behavior for everything at once
    * `register_column_factory`: specific to `Column`
    * `register_filter_factory`: specific to `Filter`
    * `register_field_factory`: specific to `Field`


    You use the `register_factory` function to register your own factory. The simplest way is:
    """

    # @test
    class TimeField:
        pass
    # @end

    register_factory(
        TimeField,
        shortcut_name='time'
    )

    # language=rst
    """
    When iommi then sees a Django `TimeField` it will call the `Column.time` shortcut to create a column, `Filter.time` to create a `Filter` and `Field.time` to create a field.

    If you need different behavior for the three classes you need to use the more specific registration functions.

    You can also register `None` to tell iommi to just ignore the field type whenever it sees it.

    For more advanced behavior you can pass a `Shortcut` instance or a callable that returns a shortcut. This is the iommi definition for booleans:

    """

    # @test
    from django.db.models.fields import BooleanField
    # @end

    register_field_factory(
        BooleanField,
        factory=lambda model_field, **kwargs: (
            Shortcut(call_target__attribute='boolean')
            if not model_field.null
            else Shortcut(call_target__attribute='boolean_tristate')
        )
    )


def test_rendering_of_your_custom_types_in_a_table():
    # language=rst
    """
    Rendering of your custom types in a table
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    iommi renders `bool`, `list`, `set`, `tuple`, `QuerySet` and any type that has a `__html__` method with special logic to make it look nice in a table. If you have a type where you can't or don't want to implement a `__html__` method (or you want more complex rendering) you can plug into this system yourself with `register_cell_formatter`:
    """

    # @test
    class MyType:
        pass
    # @end

    register_cell_formatter(MyType, lambda value, **_: f'hello {value}')

    # language=rst
    """
    The callable you register gets the keyword arguments `value`, `table`, `column` and `row`.
    """


def test_the_search_fields_of_your_django_models():
    # language=rst
    """
    The search fields of your Django models
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    When searching for an object with `Query` we need to know which fields to use to find the object. This enables the advanced query language to be `my_car_brand='toyota'` instead of `my_car_brand.pk=42` which is a lot nicer. iommi will automatically use a field called `name` if it exists and is unique. If you have other fields you want iommi to use to find objects you can register it like this:



    """
    register_search_fields(model=Album, search_fields=['year'], allow_non_unique=True)

    # language=rst
    """
    On startup iommi registers just this one particular canonical name for you since you probably want it. Note also that you can use `__` separated paths here if you have a one-to-one with another model where the name field exists.
    """


def test_custom_styles():
    # language=rst
    """
    Custom styles
    ~~~~~~~~~~~~~

    You can register your own styles with `register_style`. By default the style `bootstrap` is used. You can use it as the basis of your custom look and feel or start with the `base` style and work from there.
    """
