import pytest
from tri_declarative import (
    class_shortcut,
    dispatch,
    Namespace,
    Refinable,
)
from tri_struct import Struct

from iommi import (
    Asset,
    Fragment,
    Page,
    Table,
)
from iommi.attrs import render_attrs
from iommi.base import items
from iommi.reinvokable import reinvokable
from iommi.style import (
    apply_style_data,
    get_style,
    get_style_data_for_object,
    InvalidStyleConfigurationException,
    register_style,
    reinvoke_new_defaults,
    Style,
    unregister_style,
    validate_styles,
)
from iommi.style_base import base
from iommi.style_test_base import test
from iommi.traversable import (
    get_iommi_style_name,
    Traversable,
)
from tests.helpers import (
    prettify,
    req,
)


def test_style():
    class A(Traversable):
        @dispatch
        @reinvokable
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        foo = Refinable()
        bar = Refinable()

        @classmethod
        @class_shortcut
        def shortcut1(cls, call_target, **kwargs):
            return call_target(**kwargs)

        def items(self):
            return dict(foo=self.foo, bar=self.bar)

    class B(A):
        @dispatch
        @reinvokable
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        @classmethod
        @class_shortcut(call_target__attribute='shortcut1')
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
    b = apply_style_data(style_data=overrides.component(b), obj=b)
    assert items(b) == dict(foo=5, bar=7)

    b = B.shortcut1()
    assert overrides.component(b) == dict(foo=4, bar=7)
    assert b.__tri_declarative_shortcut_stack == ['shortcut1']
    b = apply_style_data(style_data=overrides.component(b), obj=b)
    assert items(b) == dict(foo=4, bar=7)

    b = B.shortcut2()
    assert b.__tri_declarative_shortcut_stack == ['shortcut2', 'shortcut1']
    assert overrides.component(b) == dict(foo=4, bar=7)
    b = apply_style_data(style_data=overrides.component(b), obj=b)
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

    assert get_iommi_style_name(form.fields.foo) == 'bootstrap'
    assert (
        get_style_data_for_object(
            style_name='bootstrap',
            obj=form.fields.foo,
            is_root=False,
        )['attrs']
        == {'class': {'form-group': True, 'form-check': True}}
    )
    assert render_attrs(form.fields.foo.attrs) == ' class="form-check form-group"'
    assert (
        render_attrs(form.fields.foo.input.attrs) == ' class="form-check-input" id="id_foo" name="foo" type="checkbox"'
    )
    assert render_attrs(form.fields.foo.label.attrs) == ' class="form-check-label" for="id_foo"'


def test_apply_style_data_does_not_overwrite():
    foo = Namespace(bar__template='specified')
    style = Namespace(bar__template='style_template')

    foo = apply_style_data(style_data=style, obj=foo)
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
        @reinvokable
        def __init__(self):
            pass

        def __repr__(self):
            return '<Foo>'

    style = Namespace(something_that_does_not_exist='!!!')

    with pytest.raises(InvalidStyleConfigurationException) as e:
        apply_style_data(style_data=style, obj=Foo())

    assert (
        str(e.value)
        == "Object <Foo> could not be updated with style configuration {'something_that_does_not_exist': '!!!'}"
    )


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

    assert (
        str(e.value)
        == '''
Invalid class names:
    Style: foo - class: ClassThatDoesNotExist
    Style: foo - class: ClassThatDoesNotExist2

Invalid shortcut names:
    Style: foo - class: Foo - shortcut: does_not_exist
    Style: foo - class: Foo - shortcut: does_not_exist2
'''.strip()
    )


@pytest.mark.django_db
def test_style_bulk_form():
    from iommi import Column, Table
    from tests.models import Foo

    register_style(
        'my_style',
        Style(
            base,
            Table__bulk__attrs__class__foo=True,
        ),
    )

    class MyTable(Table):
        class Meta:
            iommi_style = 'my_style'
            model = Foo

        bar = Column(bulk__include=True)

    table = MyTable()
    table = table.bind(request=None)

    assert 'foo' in render_attrs(table.bulk.attrs)

    unregister_style('my_style')


@pytest.mark.django_db
def test_style_bulk_form_broken_on_no_form():
    from iommi import Table
    from tests.models import Foo

    register_style(
        'my_style',
        Style(
            base,
            Table__bulk__attrs__class__foo=True,
        ),
    )

    class MyTable(Table):
        class Meta:
            iommi_style = 'my_style'
            model = Foo

    table = MyTable()
    table = table.bind(request=None)

    assert table.bulk is None

    unregister_style('my_style')


def test_get_style_error():
    with pytest.raises(Exception) as e:
        get_style('does_not_exist')

    assert str(e.value).startswith('No registered style does_not_exist. Register a style with register_style().')


class MyReinvokable:
    _name = None

    @reinvokable
    def __init__(self, **kwargs):
        self.kwargs = Struct(kwargs)


def test_reinvokable_new_defaults_recurse():
    x = MyReinvokable(foo=MyReinvokable(bar=17))
    x = reinvoke_new_defaults(x, Namespace(foo__bar=42, foo__baz=43))

    assert isinstance(x.kwargs.foo, MyReinvokable)
    assert x.kwargs.foo.kwargs == dict(bar=17, baz=43)


def test_reinvoke_new_default_change_shortcut():
    class ReinvokableWithShortcut(MyReinvokable):
        @classmethod
        @class_shortcut
        def shortcut(cls, call_target=None, **kwargs):
            kwargs['shortcut_was_here'] = True
            return call_target(**kwargs)

    assert (
        reinvoke_new_defaults(
            ReinvokableWithShortcut(),
            dict(
                call_target__attribute='shortcut',
                foo='bar',
            ),
        ).kwargs
        == dict(foo='bar', shortcut_was_here=True)
    )


@pytest.mark.skip('Broken since there is no way to set things on the container of Action')
def test_set_class_on_actions_container():  # pragma: no cover
    t = Table()
    style_data = Namespace(
        actions__attrs__class={'object-tools': True},
    )
    reinvoke_new_defaults(t, style_data)


def test_assets_render_from_style():
    register_style(
        'my_style',
        Style(
            test,
            root__assets__an_asset=Asset.css(attrs__href='http://foo.bar/baz'),
        ),
    )

    expected = prettify(
        '''
        <!DOCTYPE html>
        <html>
            <head>
                <title/>
                <link href='http://foo.bar/baz' rel="stylesheet"/>
            </head>
            <body/>
        </html>
    '''
    )
    actual = prettify(Page(iommi_style='my_style').bind(request=req('get')).render_to_response().content)
    assert actual == expected

    unregister_style('my_style')


def test_deprecated_assets_style(settings, capsys):
    settings.DEBUG = True
    register_style(
        'my_style',
        Style(
            test,
            assets__an_asset=Asset.css(attrs__href='http://foo.bar/baz'),
        ),
    )

    captured = capsys.readouterr()
    assert 'Warning: The preferred way to add top level assets config' in captured.out

    settings.DEBUG = False

    expected = prettify(
        '''
        <!DOCTYPE html>
        <html>
            <head>
                <title/>
                <link href='http://foo.bar/baz' rel="stylesheet"/>
            </head>
            <body/>
        </html>
    '''
    )
    actual = prettify(Page(iommi_style='my_style').bind(request=req('get')).render_to_response().content)
    assert actual == expected

    unregister_style('my_style')


def test_assets_render_any_fragment_from_style():
    register_style(
        'my_style',
        Style(
            test,
            root__assets__an_asset=Fragment('This is a fragment!'),
        ),
    )

    class MyPage(Page):
        class Meta:
            iommi_style = 'my_style'

    expected = prettify(
        '''
        <!DOCTYPE html>
        <html>
            <head>
                <title/>
                This is a fragment!
            </head>
            <body/>
        </html>
    '''
    )
    actual = prettify(MyPage().bind(request=req('get')).render_to_response().content)
    assert actual == expected

    unregister_style('my_style')


def test_assets_render_from_bulma_style():
    class MyPage(Page):
        class Meta:
            iommi_style = 'bulma'
            assets__axios = None

    expected = prettify(
        '''\
        <!DOCTYPE html>
        <html>
            <head>
                <title></title>
                <script crossorigin="anonymous" integrity="sha256-WpOohJOqMqqyKL9FccASB9O0KwACQJpFTUBLTYOVvVU=" src="https://code.jquery.com/jquery-3.4.1.js"></script>
                <link href="https://cdn.jsdelivr.net/npm/bulma@0.9.1/css/bulma.min.css" rel="stylesheet">
                <script>
    $(document).ready(function() {
          // Check for click events on the navbar burger icon
          $(".navbar-burger").click(function() {

              // Toggle the "is-active" class on both the "navbar-burger" and the "navbar-menu"
              $(".navbar-burger").toggleClass("is-active");
              $(".navbar-menu").toggleClass("is-active");

          });
    });
</script>
                <link href="https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container main"/>
            </body>
        </html>
    '''
    )
    actual = prettify(MyPage().bind(request=req('get')).render_to_response().content)
    assert actual == expected
