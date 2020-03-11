import json
from collections import defaultdict
from pathlib import Path

from django.contrib.auth import (
    login,
    logout,
)
from django.contrib.auth.models import User
from django.db import OperationalError

import iommi.part
import iommi.style
import iommi.traversable
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
)
from django.template import (
    RequestContext,
    Template,
)
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from iommi import (
    Action,
    Column,
    html,
    Page,
    Table,
)
from iommi.form import (
    choice_parse,
    Field,
    Form,
)
from iommi.menu import (
    Menu,
    MenuItem,
)
from iommi.style import validate_styles
from tri_declarative import (
    get_members,
    is_shortcut,
    Namespace,
    Shortcut,
)
from tri_struct import Struct

from .models import (
    Bar,
    Foo,
    TBar,
    TFoo,
    Album,
    Artist,
    Track,
)


def log_in(request):
    login(request, User.objects.filter(is_staff=True).get())
    return HttpResponseRedirect('/')


def log_out(request):
    logout(request)
    return HttpResponseRedirect('/')


# Use this function in your code to check that the style is configured correctly. Pass in all stylable classes in your system. For example if you have subclasses for Field, pass these here.
validate_styles()


def ensure_objects():
    if not User.objects.exists():
        User.objects.create(username='admin', is_staff=True, first_name='Tony', last_name='Iommi')

    for i in range(100 - Foo.objects.count()):
        Foo.objects.create(name=f'X{i}', a=i, b=True)

    if not Album.objects.exists():
        with open(Path(__file__).parent.parent / 'scraped_data.json') as f:
            artists = json.loads(f.read())

        for artist_name, albums in artists.items():
            artist, _ = Artist.objects.get_or_create(name=artist_name)
            for album_name, album_data in albums.items():
                album, _ = Album.objects.get_or_create(artist=artist, name=album_name, year=int(album_data['year']))
                for i, (track_name, duration) in enumerate(album_data['tracks']):
                    Track.objects.get_or_create(album=album, index=i+1, name=track_name, duration=duration)


try:
    ensure_objects()
except OperationalError:
    # We'll end up here in the management commands before the db is set up
    pass


def index(request):
    class AdminPage(Page):
        admin_header = html.h2('Admin example')

        admin_a = html.a('Admin', attrs__href="iommi-admin/")

    class IndexPage(Page):
        header = html.h1('iommi examples')

        log_in = html.a(
            'Log in',
            attrs__href='/log_in/',
            include=lambda fragment, **_: not fragment.get_request().user.is_authenticated,
        )

        log_out = html.a(
            'Log out',
            attrs__href='/log_out/',
            include=lambda fragment, **_: fragment.get_request().user.is_authenticated,
        )

        form_header = html.h2('Form examples')

        # We can create html fragments...
        f_a_1 = html.a('Example 1: echo submitted data', attrs__href="form_example_1/")
        f_b_1 = html.br()
        f_a_2 = html.a('Example 2: create a Foo', attrs__href="form_example_2/")
        f_b_2 = html.br()
        f_a_3 = html.a('Example 3: edit a Foo', attrs__href="form_example_3/")
        f_b_3 = html.br()
        f_a_4 = html.a('Example 4: custom buttons', attrs__href="form_example_4/")
        f_b_4 = html.br()
        f_a_5 = html.a('Example 5: automatic AJAX endpoint', attrs__href="form_example_5/")
        f_b_5 = html.br()
        f_a_k = html.a('Kitchen sink', attrs__href="form_kitchen/")

        table_header = html.h2('Table examples')

        # ...or just throw a big chunk of html in here
        table_links = mark_safe("""
        <a href="table_readme_example_1/">Example 1 from the README</a><br>
        <a href="table_readme_example_2/">Example 2 from the README</a><br>
        <a href="table_kitchen_sink/">Kitchen sink</a><br>
        <a href="table_as_view/">Table.as_view() example</a><br>
        """)

        page_header = html.h2('Page examples')

        page_links = mark_safe("""
        <a href="page_busy/">A busy page with lots of stuff</a><br>
        <a href="all_field_sorts">Show different type of form field types</a><br>
        <a href="all_column_sorts">Show different type of table column types</a>
        """)

        menu_examples = mark_safe("""
        <h2>Menu examples</h2>
        
        <a href="menu_test/">A menu example</a><br>
        """)

        # You can also nest pages
        admin = AdminPage()

        select_style = StyleSelector()

    return IndexPage()


def form_example_1(request):
    class MyForm(Form):
        foo = Field()
        bar = Field()

    form = MyForm()
    form = form.bind(request=request)

    message = mark_safe("\n".join(
        format_html(
            "{}: {}",
            name,
            bound_field.value
        )
        for name, bound_field in form.fields.items())
    )

    return HttpResponse(
        Template("""
            {% extends "base.html" %} 
            {% block content %}
                {{ form }} 
                {{ message }} 
            {% endblock %}
        """).render(
            context=RequestContext(
                request,
                dict(title='Example 1', form=form, message=message)
            )
        ),
    )


def form_example_2(request):
    # NOTE: See urls.py for example 2b! This example is equivalent to this view, but is defined fully in views.py
    return Form.create(auto__model=Foo)


def form_example_3(request):
    ensure_objects()
    return Form.edit(auto__instance=Foo.objects.all().first())


def form_example_4(request):
    ensure_objects()
    return Form.edit(
        auto__instance=Foo.objects.all().first(),
        actions=dict(
            foo=Action.submit(attrs__value='Foo'),
            bar=Action.submit(attrs__value='Bar'),
            back=Action(display_name='Back to index', attrs__href='/'),
        )
    )


def form_example_3(request):
    ensure_objects()
    return Form.edit(
        auto__instance=Track.objects.all().first(),
        fields__foo__attr='album__artist',
    )


def form_example_5(request):
    ensure_objects()
    return Form.create(
        auto__model=Bar,
        fields__b__input__template='iommi/form/choice_select2.html',
        actions=dict(
            foo=Action.submit(attrs__value='Foo'),
            bar=Action.submit(attrs__value='Bar'),
            back=Action(display_name='Back to index', attrs__href='/'),
        )
    )


class KitchenForm(Form):
    class Meta:
        _name = 'kitchen'

    kitchen_foo = Field()

    fisk = Field.multi_choice(
        choices=[1, 2, 3, 4],
        parse=choice_parse,
        initial=[1, 2],
        editable=False
    )

    textarea = Field.textarea(initial='initial value')

    radio = Field.radio(choices=['foo!!_"', 'bar', 'baz'])


class SinkForm(Form):
    class Meta:
        _name = 'sink'

    foo = Field()


def form_kitchen(request):
    ensure_objects()

    def kitchen_form_post_handler(form, **_):
        values = form.apply(Struct())
        return HttpResponse(format_html("Kitchen values was {}", values))

    def sink_form_post_handler(form, **_):
        values = form.apply(Struct())
        return HttpResponse(format_html("Sink values from form {} was {}", form._name, values))

    class KitchenPage(Page):
        kitchen_form = KitchenForm(actions__submit__post_handler=kitchen_form_post_handler)
        sink_form = SinkForm(actions__submit__post_handler=sink_form_post_handler)
        sink_form2 = SinkForm(fields__foo__display_name='foo2', actions__submit__post_handler=sink_form_post_handler)

    return KitchenPage()


def table_readme_example_1(request):
    # Say I have a class...
    class Foo(object):
        def __init__(self, i):
            self.a = i
            self.b = 'foo %s' % (i % 3)
            self.c = (i, 1, 2, 3, 4)

    # and a list of them
    foos = [Foo(i) for i in range(4)]

    # I can declare a table:
    class FooTable(Table):
        a = Column.number()  # This is a shortcut that results in the css class "rj" (for right justified) being added to the header and cell
        b = Column()
        c = Column(cell__format=lambda value, **_: value[-1])  # Display the last value of the tuple
        sum_c = Column(cell__value=lambda row, **_: sum(row.c), sortable=False)  # Calculate a value not present in Foo

    # now to get an HTML table:
    return FooTable(rows=foos)


def fill_dummy_data():
    if not TBar.objects.all():
        # Fill in some dummy data if none exists
        for i in range(200):
            f = TFoo.objects.create(a=i, name='Foo: %s' % i)
            TBar.objects.create(b=f, c='foo%s' % (i % 3))


def table_readme_example_2(request):
    fill_dummy_data()

    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        b__a = Column.number(  # Show "a" from "b". This works for plain old objects too.
            filter__include=True,  # put this field into the query language
        )
        c = Column(
            bulk__include=True,  # Enable bulk editing for this field
            filter__include=True,
        )

    return BarTable(rows=TBar.objects.all(), page_size=20)


def table_kitchen_sink(request):
    fill_dummy_data()

    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        b__a = Column.number()  # Show "a" from "b". This works for plain old objects too.

        b = Column.from_model(
            model=TBar,
            field_name='b',
            bulk__include=True,
            filter__include=True,
        )
        c = Column(bulk__include=True)  # The form is created automatically

        d = Column(
            display_name='Display name',
            attr__class__css_class=True,
            header__url='https://docs.iommi.rocks',
            sortable=False,
            group='Foo',
            auto_rowspan=True,
            filter__include=True,
            cell__value=lambda row, **_: row.b.a // 3,
            cell__format=lambda value, **_: '- %s -' % value,
            cell__attrs__class={'text-center': True},
            cell__attrs__title='cell title',
            cell__url='url',
            cell__url_title='cell url title',
        )
        e = Column(group='Foo', cell__value='explicit value', sortable=False)
        f = Column(include=False, sortable=False)
        g = Column(attr='c', sortable=False)
        django_templates_for_cells = Column(
            sortable=False,
            cell__value=None,
            cell__template='kitchen_sink_cell_template.html',
            group='Bar',
        )

        class Meta:
            _name = 'bar'
            page_size = 20

    return BarTable(rows=TBar.objects.all())


def page_busy(request):
    class BusyPage(Page):
        tfoo = Table(auto__model=TFoo, page_size=5, columns__name__filter=dict(include=True, field__include=True))
        tbar = Table(auto__model=TBar, page_size=5, columns__b__filter=dict(include=True, field__include=True))
        create_tbar = Form.create(auto__model=TBar)

    return BusyPage()


def all_field_sorts(request):
    some_choices = ['Foo', 'Bar', 'Baz']
    return Page(parts=dict(
        header=html.h2('All sorts of fields'),
        form=Form(
            actions__submit__include=False,
            fields__field_of_type_radio__choices=some_choices,
            fields__field_of_type_choice__choices=some_choices,
            fields__field_of_type_choice_queryset__choices=TFoo.objects.all(),
            fields__field_of_type_multi_choice__choices=some_choices,
            fields__field_of_type_multi_choice_queryset__choices=TBar.objects.all(),
            fields__field_of_type_info__value="This is some information",
            **{
                f'fields__field_of_type_{t}__call_target__attribute': t
                for t in get_members(
                    cls=Field,
                    member_class=Shortcut,
                    is_member=is_shortcut
                ).keys()
                if t not in [
                    # These only work if we have an instance
                    'foreign_key',
                    'many_to_many']
            })
    ))


class DummyRow:
    def __init__(self, idx):
        self.idx = idx

    def __getattr__(self, attr):
        _, _, shortcut = attr.partition('column_of_type_')
        s = f'{shortcut} #{self.idx}'
        if shortcut == 'link':
            return Struct(
                get_absolute_url=lambda: '#',
            )
        return s

    @staticmethod
    def get_absolute_url():
        return '#'


class ShortcutSelectorForm(Form):
    class Meta:
        attrs__method = 'get'

    shortcut = Field.multi_choice(
        choices=[
            t
            for t in get_members(
                cls=Column,
                member_class=Shortcut,
                is_member=is_shortcut
            ).keys()
            if t not in [
                'icon',
                'foreign_key',
                'many_to_many',
                'choice_queryset',
                'multi_choice_queryset',
            ]
        ]
    )


def all_column_sorts(request):
    selected_shortcuts = ShortcutSelectorForm().bind(request=request).fields.shortcut.value or []

    type_specifics = Namespace(
        choice__choices=['Foo', 'Bar', 'Baz'],
        multi_choice__choices=['Foo', 'Bar', 'Baz'],
    )

    return Page(parts=dict(
        header=html.h2('All sorts of columns'),
        form=ShortcutSelectorForm(),
        table=Table(
            rows=[DummyRow(i) for i in range(10)],
            **{
                f'columns__column_of_type_{t}': dict(
                    type_specifics.get(t, {}),
                    call_target__attribute=t,
                )
                for t in selected_shortcuts
            })
    ))


BASE_TEMPLATE_BY_STYLE = defaultdict(lambda: 'base.html')
BASE_TEMPLATE_BY_STYLE['semantic_ui'] = 'base_semantic_ui.html'


def select_style_post_handler(form, **_):
    style = form.fields.style.value
    iommi.style.DEFAULT_STYLE = style
    iommi.part.DEFAULT_BASE_TEMPLATE = BASE_TEMPLATE_BY_STYLE[style]


class StyleSelector(Form):
    class Meta:
        actions__submit__post_handler = select_style_post_handler

    style = Field.choice(
        choices=[
            'bootstrap',
            'semantic_ui',
        ],
        initial=lambda form, field, **_: iommi.style.DEFAULT_STYLE,
    )


def menu_test(request):
    class FooPage(Page):
        menu = Menu(
            sub_menu=dict(
                root=MenuItem(url='/'),

                menu_test=MenuItem(),

                f_a_1=MenuItem(display_name='Example 1: echo submitted data', url="form_example_1/"),
                f_a_2=MenuItem(display_name='Example 2: create a Foo', url="form_example_2/"),
                f_a_3=MenuItem(display_name='Example 3: edit a Foo', url="form_example_3/"),
                f_a_4=MenuItem(display_name='Example 4: custom buttons', url="form_example_4/"),
                f_a_5=MenuItem(display_name='Example 5: automatic AJAX endpoint', url="form_example_5/"),
                f_a_k=MenuItem(display_name='Kitchen sink', url="form_kitchen/"),
            ),
        )

    return FooPage()
