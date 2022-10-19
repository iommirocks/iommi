import pytest

from iommi import (
    Asset,
    Field,
    Form,
    Fragment,
    html,
    Menu,
    MenuItem,
    Page,
    Query,
    Table,
)
from iommi.attrs import render_attrs
from iommi.base import items
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import Namespace
from iommi.refinable import (
    Refinable,
    RefinableObject,
)
from iommi.shortcut import with_defaults
from iommi.style import (
    get_global_style,
    get_style_object,
    InvalidStyleConfigurationException,
    register_style,
    resolve_style,
    Style,
    validate_styles,
)
from iommi.style_base import base
from iommi.style_test_base import test
from iommi.traversable import (
    Traversable,
)
from tests.helpers import (
    prettify,
    req,
)
from tests.models import TBar


def test_style():
    class A(Traversable):
        @dispatch
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        foo = Refinable()
        bar = Refinable()

        @classmethod
        @with_defaults
        def shortcut1(cls, **kwargs):
            return cls(**kwargs)

        def items(self):
            return dict(foo=self.foo, bar=self.bar)

    class B(A):
        @dispatch
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        @classmethod
        @with_defaults
        def shortcut2(cls, **kwargs):
            return cls.shortcut1(**kwargs)

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

    def styled_items(obj):
        return items(obj.refine_done())

    # First the unstyled case
    assert styled_items(B()) == dict(foo=None, bar=None)
    assert styled_items(B.shortcut1()) == dict(foo=None, bar=None)
    assert styled_items(B.shortcut2()) == dict(foo=None, bar=None)

    # Now let's add the style
    b = B(iommi_style=overrides)
    assert styled_items(b) == dict(foo=5, bar=7)

    b = B.shortcut1(iommi_style=overrides)
    assert overrides.resolve(b) == [dict(bar=6, foo=5), dict(foo=4), dict(bar=7)]
    assert b.iommi_shortcut_stack == ['shortcut1']
    assert styled_items(b) == dict(foo=4, bar=7)

    b = B.shortcut2(iommi_style=overrides)
    assert b.iommi_shortcut_stack == ['shortcut2', 'shortcut1']
    assert overrides.resolve(b) == [dict(bar=6, foo=5), dict(foo=4), dict(bar=7)]
    assert styled_items(b) == dict(foo=4, bar=7)


def test_resolve_style_base():
    assert resolve_style(None) is get_global_style('test')


def test_resolve_style_trivial():
    assert resolve_style('test') is get_global_style('test')


def test_resolve_style_fail():
    with pytest.raises(Exception) as e:
        resolve_style('not_a_style')
    assert 'No registered iommi style not_a_style. Register a style with register_style().' in str(e.value)


def test_resolve_style_shadow_default():
    with register_style('my_style', Style()) as my_style:
        assert resolve_style('my_style', enclosing_style=Style()) is my_style


def test_resolve_style_shadow_default2():
    with register_style('my_style', Style()) as my_style:
        assert resolve_style('my_style', enclosing_style=my_style) is my_style


def test_resolve_style_sub_style():
    sub_style = Style()
    with register_style('my_style', Style(sub_styles=dict(sub_style=sub_style))) as my_style:
        assert resolve_style('sub_style', enclosing_style=my_style) is sub_style


def test_style_menu():
    class MyMenu(Menu):
        item = MenuItem()

    assert (
        MyMenu().bind(request=req('get')).__html__()
        == '<nav><ul><li><a class="link" href="/item/">Item</a></li></ul></nav>'
    )


def test_style_menu_active():
    class MyMenu(Menu):
        item = MenuItem(url='/')

    assert (
        MyMenu().bind(request=req('get')).__html__()
        == '<nav><ul><li><a class="active link" href="/">Item</a></li></ul></nav>'
    )


def test_apply_checkbox_style():
    from iommi import Form
    from iommi import Field

    class MyForm(Form):
        class Meta:
            iommi_style = 'bootstrap'

        foo = Field.boolean()

    form = MyForm()
    form = form.bind(request=None)

    assert get_style_object(form.fields.foo) == get_global_style('bootstrap')
    assert Namespace(
        *get_global_style('bootstrap').resolve(
            obj=form.fields.foo,
            is_root=False,
        )
    ).attrs == {'class': {'form-group': True, 'form-check': True}}
    assert render_attrs(form.fields.foo.attrs) == ' class="form-check form-group"'
    assert (
        render_attrs(form.fields.foo.input.attrs) == ' class="form-check-input" id="id_foo" name="foo" type="checkbox"'
    )
    assert render_attrs(form.fields.foo.label.attrs) == ' class="form-check-label" for="id_foo"'


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
    with pytest.raises(
        TypeError,
        match=(
            'Fragment object has no refinable attribute\\(s\\): "something_that_does_not_exist".\n'
            + 'Available attributes:\n'
            + '    after\n'
            + '    assets\n'
            + '    attrs\n'
            # ...
        ),
    ):
        Fragment(iommi_style=Style(Fragment__something_that_does_not_exist='!!!')).refine_done()


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

    with register_style(
        'my_style',
        Style(
            base,
            Table__bulk__attrs__class__foo=True,
        ),
    ):

        class MyTable(Table):
            class Meta:
                iommi_style = 'my_style'
                model = Foo

            bar = Column(bulk__include=True)

        table = MyTable()
        table = table.bind(request=None)

        assert 'foo' in render_attrs(table.bulk.attrs)


@pytest.mark.django_db
def test_style_bulk_form_broken_on_no_form():
    from iommi import Table
    from tests.models import Foo

    with register_style(
        'my_style',
        Style(
            base,
            Table__bulk__attrs__class__foo=True,
        ),
    ):

        class MyTable(Table):
            class Meta:
                iommi_style = 'my_style'
                model = Foo

        table = MyTable()
        table = table.bind(request=None)

        assert table.bulk is None


def test_get_style_error():
    with pytest.raises(Exception) as e:
        get_global_style('does_not_exist')

    assert str(e.value).startswith('No registered iommi style does_not_exist. Register a style with register_style().')


class MyRefinableObject(RefinableObject):

    foo: 'MyRefinableObject' = Refinable()
    bar: int = Refinable()
    baz: int = Refinable()

    def on_refine_done(self):
        if self.foo:
            self.foo = self.foo.refine_done(parent=self)


def test_reinvoke_new_default_change_shortcut():
    class RefinableObjectWithShortcut(MyRefinableObject):
        @classmethod
        @with_defaults
        def shortcut(cls, **kwargs):
            kwargs['baz'] = 'baz'
            return cls(**kwargs)

    x = RefinableObjectWithShortcut.shortcut(bar='bar').refine_done()
    assert x.bar == 'bar'
    assert x.baz == 'baz'


@pytest.mark.skip('Broken since there is no way to set things on the container of Action')
def test_set_class_on_actions_container():  # pragma: no cover
    t = Table()
    style_data = Namespace(
        actions__attrs__class={'object-tools': True},
    )
    assert bool(t.refine(**style_data).refine_done().actions.attrs['class']['object-tool'])


def test_assets_render_from_style():
    with register_style(
        'my_style',
        Style(
            test,
            root__assets__an_asset=Asset.css(attrs__href='http://foo.bar/baz'),
        ),
    ):

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


def test_assets_render_any_fragment_from_style():
    with register_style(
        'my_style',
        Style(
            test,
            root__assets__an_asset=Fragment('This is a fragment!'),
        ),
    ):

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
            <body >
                <div class="container main" />
            </body>
        </html>
    '''
    )
    actual = prettify(MyPage().bind(request=req('get')).render_to_response().content)
    assert actual == expected


def test_style_inheritance():
    with register_style(
        'custom_style',
        Style(
            test,
            Form__template='custom_style_form.html',
        ),
    ) as custom_style:
        page1 = Page(
            iommi_style='custom_style',
            parts__form=Form(),
        )

        form = page1.bind().parts.form
        assert form.iommi_style is custom_style

        assert form.template == 'custom_style_form.html'

        page2 = Page(
            iommi_style='base',
            parts__form=Form(
                iommi_style='custom_style',
            ),
        )
        page = page2.bind()
        assert page.iommi_style.name == 'base'

        form = page.parts.form
        assert form.iommi_style is custom_style

        assert form.template == 'custom_style_form.html'


def test_style_inheritance_tricky():
    with register_style(
        'custom_style',
        Style(
            test,
            sub_styles=dict(
                custom_sub_style=dict(
                    Form__template='sub.html',
                )
            ),
            Form__template='custom.html',
        ),
    ) as custom_style:
        page1 = Page(
            iommi_style=custom_style,
            parts__form=Form(
                iommi_style='custom_sub_style',
            ),
        )
        page = page1.bind()
        assert page.iommi_style.name == 'custom_style'

        form = page.parts.form
        assert form.iommi_style.name == 'custom_sub_style'

        assert form.template == 'sub.html'


@pytest.fixture
def styled_form():
    with register_style(
        'my_style',
        Style(
            test,
            Form__template='my_template.html',
            Form__attrs__thing='Styled',
            Field__template='my_other_template.html',
            Field__attrs__other_thing='Also styled',
        ),
    ):
        yield Form(
            iommi_style='my_style',
            fields__foo=Field(),
        )


def test_style_on_form_in_page(styled_form):
    bound_form = styled_form.bind(request=req('get'))
    assert bound_form.fields.foo.template == 'my_other_template.html'
    assert bound_form.fields.foo.attrs.other_thing == 'Also styled'
    assert bound_form.template == 'my_template.html'
    assert bound_form.attrs.thing == 'Styled'


def test_style_on_form_as_root(styled_form):
    page = Page(parts__form=styled_form)
    bound_page = page.bind(request=req('get'))
    assert bound_page.parts.form.fields.foo.template == 'my_other_template.html'
    assert bound_page.parts.form.fields.foo.attrs.other_thing == 'Also styled'
    assert bound_page.parts.form.template == 'my_template.html'
    assert bound_page.parts.form.attrs.thing == 'Styled'


def test_style_on_child():
    with register_style(
        'foo',
        Style(
            test,
            Fragment__extra__foo='foo',
            Table__tbody__extra__bar='bar',
        ),
    ):
        table = Table(iommi_style='foo').bind()
        assert table.tbody.extra.foo == 'foo'
        assert table.tbody.extra.bar == 'bar'


def test_style_repr():
    with register_style('foo', Style()) as foo:
        assert repr(foo) == '<Style: foo>'


@pytest.mark.django_db
def test_filter_assets_for_foreign_key():
    q = Query(
        auto__model=TBar,
        iommi_style='bootstrap',
        filters__foo__assets__select2_js=Asset.js(
            attrs__src='https://cdn.jsdelivr.net/npm/select2@4.0.12/dist/js/select2.min.js',
        ),
    ).bind(request=req('get'))
    assert 'select2_js' in q.iommi_collected_assets().keys()


def test_assets_from_different_sources():
    with register_style(
        'my_style',
        Style(
            test,
            Page__assets__an_asset=html.script('This is an asset'),
        ),
    ):

        class MyPage(Page):
            class Meta:
                iommi_style = 'my_style'
                assets__another_asset = html.script('This is another asset')

        # language=html
        expected = prettify(
            '''
                <!DOCTYPE html>
                <html>
                    <head>
                        <title/>
                        <script> This is an asset </script>
                        <script> This is another asset </script>
                    </head>
                    <body/>
                </html>
            '''
        )
        actual = prettify(MyPage().bind(request=req('get')).render_to_response().content)
        print(expected)
        print(actual)

        assert actual == expected


@pytest.mark.django_db
def test_filter_assets_for_foreign_key2():
    form = Form(auto__model=TBar, iommi_style='bootstrap').bind(request=req('get'))
    assert 'data-choices-endpoint' in form.fields.foo.__html__()
    q = Query(auto__model=TBar, iommi_style='bootstrap', form__iommi_style='bootstrap').bind(request=req('get'))
    assert 'data-choices-endpoint' in q.form.fields.foo.__html__()
    q = Query(auto__model=TBar, iommi_style='bootstrap').bind(request=req('get'))
    assert 'data-choices-endpoint' in q.form.fields.foo.__html__()


def test_bootstrap_template_snafu():
    from iommi.style_bootstrap import bootstrap

    assert Namespace(*bootstrap.resolve(Field.choice())).input.template == 'iommi/form/choice.html'
    assert (
        Namespace(*bootstrap.resolve(Field.choice_queryset(choices=TBar.objects.none()))).input.template
        == 'iommi/form/choice_select2.html'
    )


@pytest.mark.django_db
def test_filter_assets_for_foreign_key3():
    # form = Form(auto__model=TBar, iommi_style='bootstrap').bind(request=req('get'))
    # assert form.fields.foo.iommi_shortcut_stack == ['foreign_key', 'choice_queryset', 'choice']
    # assert 'data-choices-endpoint' in form.fields.foo.__html__()

    q = Query(auto__model=TBar, iommi_style='bootstrap', form__iommi_style='horizontal').bind(request=req('get'))
    assert q.form.fields.foo.iommi_style.name == 'horizontal'
    assert q.form.fields.foo.iommi_shortcut_stack == ['foreign_key', 'choice_queryset', 'choice']
    assert 'data-choices-endpoint' in q.form.fields.foo.__html__()

    form = Form(auto__model=TBar, iommi_style='bootstrap').bind(request=req('get'))
    assert 'data-choices-endpoint' in form.fields.foo.__html__()

    q = Query(auto__model=TBar, iommi_style='bootstrap').bind(request=req('get'))
    assert q.form.fields.foo.iommi_shortcut_stack == ['foreign_key', 'choice_queryset', 'choice']
    assert 'data-choices-endpoint' in q.form.fields.foo.__html__()


def test_resolve_root():
    assert Style(root__foo='bar').resolve(None, is_root=True) == [dict(foo='bar')]


class Dog:
    pass


def test_resolve_style():
    style = Style(
        Dog__tail='short',
    )
    assert style.resolve(Dog()) == [dict(tail='short')]


def test_resolve_inherit():
    base_style = Style(Dog__snout='yes')
    style = Style(
        base_style,
        Dog__tail='short',
    )
    assert style.resolve(Dog()) == [dict(snout='yes', tail='short')]


def test_resolve_substyle():
    style = Style(sub_styles__shepard__Dog__tail='long')
    assert style.resolve(Dog()) == []
    assert style.sub_styles['shepard'].resolve(Dog()) == [dict(tail='long')]


def test_resolve_substyle_merge():
    style = Style(
        sub_styles__shepard=dict(
            Dog__snout='long',
        ),
        Dog__fur='short',
    )
    sub_style = style.sub_styles['shepard']
    assert sub_style.resolve(Dog()) == [dict(snout='long', fur='short')]


def test_resolve_substyle_inherit():
    base_style = Style(
        sub_styles__shepard__Dog__snout='long',
    )
    style = Style(
        base_style,
        sub_styles__shepard__Dog__fur='short',
    )
    assert style.sub_styles['shepard'].resolve(Dog()) == [dict(snout='long', fur='short')]


def test_resolve_substyle_multiple_inheritance():
    base_style = Style(
        sub_styles__shepard__Dog__snout='long',
    )
    other_style = Style(
        sub_styles__shepard__Dog__fur='short',
    )
    style = Style(base_style, other_style)
    assert style.sub_styles['shepard'].resolve(Dog()) == [dict(snout='long', fur='short')]


def test_resolve_shortcut():
    class Cat:
        @classmethod
        @with_defaults
        def siamese(cls, **kwargs):
            return cls(**kwargs)

    style = Style(Cat__teeth='sharp', Cat__shortcuts__siamese__legs='long')

    assert style.resolve(Cat()) == [dict(teeth='sharp')]
    assert style.resolve(Cat.siamese()) == [dict(teeth='sharp'), dict(legs='long')]


def test_resolve_shortcut_chain():
    class Cat:
        @classmethod
        @with_defaults
        def siamese(cls, **kwargs):
            return cls(**kwargs)

        @classmethod
        @with_defaults
        def garfield(cls, **kwargs):
            return cls.siamese(**kwargs)

    style = Style(
        Cat__teeth='sharp',
        Cat__shortcuts__siamese__legs='long',
        Cat__shortcuts__garfield__belly='fat',
    )

    assert style.resolve(Cat()) == [dict(teeth='sharp')]
    assert style.resolve(Cat.garfield()) == [dict(teeth='sharp'), dict(legs='long'), dict(belly='fat')]


def test_resolve_shortcut_multi_base():
    class Cat:
        @classmethod
        @with_defaults
        def siamese(cls, **kwargs):
            return cls(**kwargs)

        @classmethod
        @with_defaults
        def garfield(cls, **kwargs):
            return cls.siamese(**kwargs)

    base_style = Style(
        Cat__teeth='sharp',
    )
    other_style = Style(
        Cat__shortcuts__siamese__legs='long',
        Cat__shortcuts__siamese__belly='slim',
    )
    style = Style(
        base_style,
        other_style,
        Cat__shortcuts__garfield__belly='fat',
    )

    assert style.resolve(Cat.garfield()) == [dict(teeth='sharp'), dict(legs='long', belly='slim'), dict(belly='fat')]


def test_warning_for_config_into_the_void():
    with pytest.warns() as records:
        Style(foo__bar=3)

    assert records[0].message
