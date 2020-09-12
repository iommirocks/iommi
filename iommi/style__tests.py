import pytest
from tri_declarative import (
    class_shortcut,
    Namespace,
    Refinable,
    RefinableObject,
)

from iommi.attrs import render_attrs
from iommi.base import items
from iommi.style import (
    apply_style_recursively,
    get_style_name_for,
    get_style_data_for_object,
    InvalidStyleConfigurationException,
    register_style,
    Style,
    validate_styles,
)
from iommi.style_base import base


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
    assert items(B()) == dict(foo=None, bar=None)
    assert items(B.shortcut1()) == dict(foo=None, bar=None)
    assert items(B.shortcut2()) == dict(foo=None, bar=None)

    # Now let's add the style
    b = B()
    apply_style_recursively(style_data=overrides.component(b), obj=b)
    assert items(b) == dict(foo=5, bar=7)

    b = B.shortcut1()
    assert overrides.component(b) == dict(foo=4, bar=7)
    assert b.__tri_declarative_shortcut_stack == ['shortcut1']
    apply_style_recursively(style_data=overrides.component(b), obj=b)
    assert items(b) == dict(foo=4, bar=7)

    b = B.shortcut2()
    assert b.__tri_declarative_shortcut_stack == ['shortcut2', 'shortcut1']
    assert overrides.component(b) == dict(foo=4, bar=7)
    apply_style_recursively(style_data=overrides.component(b), obj=b)
    assert items(b) == dict(foo=4, bar=7)


def test_apply_checkbox_style():
    from iommi import Form
    from iommi import Field

    class MyForm(Form):
        class Meta:
            iommi_style = 'bootstrap'

        foo = Field.boolean()

    form = MyForm()
    form = form.bind(request=None)

    assert get_style_name_for(form.fields.foo) == 'bootstrap'
    assert get_style_data_for_object(style_name=get_style_name_for(form.fields.foo), obj=form.fields.foo)['attrs'] == {'class': {'form-group': True, 'form-check': True}}
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
            iommi_style = 'bootstrap'
            template = 'override'

    form = MyForm()
    form = form.bind(request=None)

    assert form.template == 'override'


def test_validate_default_styles():
    validate_styles()


def test_error_when_trying_to_style_non_existent_attribute():
    class Foo:
        def __repr__(self):
            return '<Foo>'

    style = Namespace(something_that_does_not_exist='!!!')

    with pytest.raises(InvalidStyleConfigurationException) as e:
        apply_style_recursively(style_data=style, obj=Foo())

    assert str(e.value) == 'Object <Foo> has no attribute something_that_does_not_exist which the style tried to set.'


def test_error_message_for_invalid_style():
    class Foo:
        pass

    style = Style(
        ClassThatDoesNotExist__foo='',
        ClassThatDoesNotExist2__foo='',
        Foo__shortcuts__does_not_exist__foo='',
        Foo__shortcuts__does_not_exist2__foo='',
    )

    with pytest.raises(InvalidStyleConfigurationException) as e:
        validate_styles(additional_classes=[Foo], default_classes=[], styles=dict(foo=style))

    assert str(e.value) == '''
Invalid class names:
    Style: foo - class: ClassThatDoesNotExist
    Style: foo - class: ClassThatDoesNotExist2

Invalid shortcut names:
    Style: foo - class: Foo - shortcut: does_not_exist
    Style: foo - class: Foo - shortcut: does_not_exist2
'''.strip()


@pytest.mark.django_db
def test_style_bulk_form():
    from iommi import style
    from iommi import Column, Table
    from tests.models import Foo

    register_style('my_style', Style(
        base,
        Table__bulk__attrs__class__foo=True,
    ))

    class MyTable(Table):
        class Meta:
            iommi_style = 'my_style'
            model = Foo
        bar = Column(bulk__include=True)

    table = MyTable()
    table = table.bind(request=None)

    assert 'foo' in render_attrs(table.bulk.attrs)

    del style._styles['my_style']


@pytest.mark.django_db
def test_style_bulk_form_broken_on_no_form():
    from iommi import style
    from iommi import Table
    from tests.models import Foo

    register_style('my_style', Style(
        base,
        Table__bulk__attrs__class__foo=True,
    ))

    class MyTable(Table):
        class Meta:
            iommi_style = 'my_style'
            model = Foo

    table = MyTable()
    table = table.bind(request=None)

    assert table.bulk is None

    del style._styles['my_style']
