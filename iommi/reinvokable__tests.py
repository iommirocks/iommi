from tri_declarative import (
    class_shortcut,
    Namespace,
    Refinable,
)
from tri_struct import Struct

from iommi import (
    Field,
    Form,
)
from iommi.reinvokable import (
    reinvokable,
    reinvoke,
    set_and_remember_for_reinvoke,
)


class MyReinvokable:
    _name = None

    @reinvokable
    def __init__(self, **kwargs):
        self.kwargs = Struct(kwargs)


def test_reinvokable():
    x = MyReinvokable(foo=17)
    x = reinvoke(x, dict(bar=42))
    assert x.kwargs == dict(foo=17, bar=42)


def test_set_and_remember_for_reinvoke():
    x = MyReinvokable(foo=17)
    assert x._iommi_saved_params == dict(foo=17)
    assert x.kwargs.foo == 17

    set_and_remember_for_reinvoke(x, foo=42)
    assert x.foo == 42
    x = reinvoke(x, dict(bar=42))
    assert x.kwargs == dict(foo=42, bar=42)


def test_reinvokable_recurse():
    x = MyReinvokable(foo=MyReinvokable(bar=17))
    x = reinvoke(x, Namespace(foo__bar=42))

    assert isinstance(x.kwargs.foo, MyReinvokable)
    assert x.kwargs.foo.kwargs == dict(bar=42)


def test_reinvoke_namespace_merge():
    class ReinvokableWithExtra(Namespace):
        _name = None
        extra = Refinable()

        @reinvokable
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    assert reinvoke(ReinvokableWithExtra(extra__foo=17), Namespace(extra__bar=42)).extra == dict(bar=42, foo=17)

    # Try again with pre-Namespaced kwargs
    assert reinvoke(ReinvokableWithExtra(**Namespace(extra__foo=17)), Namespace(extra__bar=42)).extra == dict(
        bar=42, foo=17
    )


def test_reinvokable_recurse_retain_original():
    x = MyReinvokable(a=1, foo=MyReinvokable(b=2, bar=MyReinvokable(c=3, baz=17)))
    x = reinvoke(x, Namespace(foo__bar__baz=42))

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


def test_reinvoke_extra():
    class MyForm(Form):
        my_field = Field(
            extra__foo=17,
        )

    f = MyForm(fields__my_field__extra__bar=42)

    assert f.bind().fields.my_field.extra == dict(foo=17, bar=42)


def test_reinvoke_extra_shortcut():
    class MyField(Field):
        @classmethod
        @class_shortcut(
            extra__buz=4711,
        )
        def shortcut(cls, call_target, **kwargs):
            return call_target(**kwargs)

    class MyForm(Form):
        my_field = MyField.shortcut(
            extra__foo=17,
        )

    f = MyForm(fields__my_field__extra__bar=42)

    assert f.bind().fields.my_field.extra == dict(foo=17, bar=42, buz=4711)


def test_reinvoke_change_shortcut():
    class ReinvokableWithShortcut(MyReinvokable):
        @classmethod
        @class_shortcut
        def shortcut(cls, call_target=None, **kwargs):
            kwargs['shortcut_was_here'] = True
            return call_target(**kwargs)

    assert (
        reinvoke(
            ReinvokableWithShortcut(),
            dict(
                call_target__attribute='shortcut',
                foo='bar',
            ),
        ).kwargs
        == dict(foo='bar', shortcut_was_here=True)
    )
