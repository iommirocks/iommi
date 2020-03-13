import pytest
from tri_declarative import (
    Namespace,
)
from tri_struct import Struct

from iommi import (
    Column,
    Field,
    Form,
    Table,
)
from iommi.base import evaluated_refinable
from iommi.page import (
    Fragment,
    Page,
)
from iommi.traversable import (
    bound_members,
    build_long_path_by_path,
    reinvokable,
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
        members=Struct(
            foo=foo
        ),
    )

    expected = {
        '': '',
        'foo': 'foo',
        'bar': 'foo/bar',
        'baz': 'foo/bar/baz',
        'buzz': 'foo/bar/buzz',
    }
    actual = build_long_path_by_path(root)
    assert actual.items() == expected.items()
    assert len(actual.keys()) == len(set(actual.keys()))


@pytest.mark.django_db
def test_traverse_on_iommi():
    class MyPage(Page):
        header = Fragment()
        some_form = Form(fields=Namespace(
            fisk=Field(),
        ))
        some_other_form = Form(fields=Namespace(
            fjomp=Field(),
            fisk=Field(),
        ))
        a_table = Table(
            model=TFoo,
            columns=Namespace(
                columns=Column(),
                fusk=Column(attr='b', filter__include=True),
            ),
        )

    page = MyPage(_name='root')

    actual = build_long_path_by_path(page)
    assert len(actual.keys()) == len(set(actual.keys()))
    page = page.bind(request=req('get'))

    assert page.iommi_path == ''
    assert page.parts.header.iommi_path == 'header'
    assert page.parts.some_form.fields.fisk.iommi_path == 'fisk'
    assert page.parts.some_other_form.fields.fisk.iommi_path == 'some_other_form/fisk'
    assert page.parts.a_table.query.form.iommi_path == 'form'
    assert page.parts.a_table.query.form.fields.fusk.iommi_path == 'fusk'
    assert page.parts.a_table.columns.fusk.iommi_path == 'a_table/fusk'


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

    assert str(e.value) == 'The names bind, get_request, iommi_path, iommi_style, on_bind, own_evaluate_parameters are reserved by iommi, please pick other names'


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
                )
            )
        )
    )
    foo = foo.bind(request=None)

    assert foo.iommi_path == ''

    assert bound_members(foo).my_part2.iommi_path == 'my_part2'
    assert bound_members(foo).my_part2.iommi_dunder_path == 'my_part2'

    assert bound_members(bound_members(foo).my_part2).my_part.iommi_path == 'my_part'
    assert bound_members(bound_members(foo).my_part2).my_part.iommi_dunder_path == 'my_part2__my_part'


class MyReinvokable(Traversable):
    @reinvokable
    def __init__(self, **kwargs):
        self.kwargs = Struct(kwargs)


def test_reinvokable():
    x = MyReinvokable(foo=17)
    x = x.reinvoke(dict(bar=42))
    assert x.kwargs == dict(foo=17, bar=42)


def test_reinvokable_recurse():
    x = MyReinvokable(foo=MyReinvokable(bar=17))
    x = x.reinvoke(Namespace(foo__bar=42))

    assert isinstance(x.kwargs.foo, MyReinvokable)
    assert x.kwargs.foo.kwargs == dict(bar=42)


def test_reinvokable_recurse_retain_original():
    x = MyReinvokable(
        a=1,
        foo=MyReinvokable(
            b=2,
            bar=MyReinvokable(
                c=3,
                baz=17
            )
        )
    )
    x = x.reinvoke(Namespace(foo__bar__baz=42))

    assert isinstance(x.kwargs.foo, MyReinvokable)
    assert x.kwargs.a == 1
    assert x.kwargs.foo.kwargs.b == 2
    assert x.kwargs.foo.kwargs.bar.kwargs.c == 3
    assert x.kwargs.foo.kwargs.bar.kwargs.baz == 42


def test_reinvoke_path():
    class MyForm(Form):
        my_field = Field.choice(
            choices=[],
        )

    my_form = MyForm(
        fields__my_field__choices=[1, 2, 3],
    )

    assert my_form.bind().fields.my_field.choices == [1, 2, 3]


def test_reinvoke_dicts():
    class MyForm(Form):
        my_field = Field.choice(
            choices=[],
        )

    my_form = MyForm(
        fields=dict(
            my_field=dict(
                choices=[1, 2, 3],
            ),
        ),
    )

    assert my_form.bind().fields.my_field.choices == [1, 2, 3]


def test_extra_evaluated_function():
    class Foo(Traversable):
        @evaluated_refinable
        def foo():
            return 1

    f = Foo().bind(request=None)
    assert f.foo == 1
