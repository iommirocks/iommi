from iommi.render import render_attrs
from iommi.style import (
    Style,
    apply_style_recursively,
    get_style_for_object,
    validate_styles,
)
from tri_declarative import (
    Refinable,
    RefinableObject,
    class_shortcut,
    Namespace,
)


def test_style():
    class A(RefinableObject):
        foo = Refinable()
        bar = Refinable()

        @classmethod
        @class_shortcut
        def shortcut1(cls, call_target, **kwargs):
            return call_target(**kwargs)

        def items(self):
            return dict(foo=self.foo, bar=self.bar)

    class B(A):
        @classmethod
        @class_shortcut(
            call_target__attribute='shortcut1'
        )
        def shortcut2(cls, call_target, **kwargs):
            return call_target(**kwargs)

    base = Style(
        A=dict(
            foo=1,
        ),
    )

    overrides = Style(
        base,
        A=dict(
            shortcuts=dict(
                shortcut1__foo=4,
            ),
            foo=5,
            bar=6,
        ),
        B=dict(
            bar=7,
        ),
    )

    # First the unstyled case
    assert B().items() == dict(foo=None, bar=None)
    assert B.shortcut1().items() == dict(foo=None, bar=None)
    assert B.shortcut2().items() == dict(foo=None, bar=None)

    # Now let's add the style
    b = B()
    apply_style_recursively(style_data=overrides.component(b), obj=b)
    assert b.items() == dict(foo=5, bar=7)

    b = B.shortcut1()
    assert overrides.component(b) == dict(foo=4, bar=7)
    assert b.__tri_declarative_shortcut_stack == ['shortcut1']
    apply_style_recursively(style_data=overrides.component(b), obj=b)
    assert b.items() == dict(foo=4, bar=7)

    b = B.shortcut2()
    assert b.__tri_declarative_shortcut_stack == ['shortcut2', 'shortcut1']
    assert overrides.component(b) == dict(foo=4, bar=7)
    apply_style_recursively(style_data=overrides.component(b), obj=b)
    assert b.items() == dict(foo=4, bar=7)


def test_apply_checkbox_style():
    from iommi import Form
    from iommi import Field

    class MyForm(Form):
        class Meta:
            style = 'bootstrap'

        foo = Field.boolean()

    form = MyForm()
    form.bind(request=None)

    assert form.fields.foo.get_style() == 'bootstrap'
    assert get_style_for_object(style=form.fields.foo.get_style(), self=form.fields.foo)['attrs'] == {'class': {'form-group': True, 'form-check': True}}
    assert render_attrs(form.fields.foo.attrs) == ' class="form-check form-group"'
    assert render_attrs(form.fields.foo.input.attrs) == ' class="form-check-input" id="id_foo" name="foo" type="checkbox"'
    assert render_attrs(form.fields.foo.label.attrs) == ' class="form-check-label" for="id_foo"'


def test_apply_style_recursively_does_not_overwrite():
    foo = Namespace(bar__template='specified')
    style = Namespace(bar__template='style_template')

    apply_style_recursively(style_data=style, obj=foo)
    assert foo == Namespace(bar__template='specified')


def test_last_win():
    from iommi import Form

    class MyForm(Form):
        class Meta:
            style = 'bootstrap'
            template = 'override'

    form = MyForm()
    form.bind(request=None)

    assert form.template == 'override'


def test_validate_default_styles():
    validate_styles()
