import json
from datetime import (
    date,
    datetime,
)
from pathlib import Path

import iommi.part
import iommi.style
import iommi.traversable
from django.conf import settings
from django.contrib.auth.models import User
from django.db import OperationalError
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
    Header,
    html,
    Page,
    Table,
)
from iommi.base import (
    items,
    keys,
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
    Album,
    Artist,
    Bar,
    Foo,
    TBar,
    TFoo,
    Track,
)

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

        for artist_name, albums in items(artists):
            artist, _ = Artist.objects.get_or_create(name=artist_name)
            for album_name, album_data in items(albums):
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
        admin_header = Header('Admin example')

        admin_a = html.p(
            html.a(
                'Admin',
                attrs__href="iommi-admin/",
            ),
        )

        log_in = html.a(
            'Log in',
            attrs__href='/iommi-admin/login/?next=/',
            include=lambda request, **_: not request.user.is_authenticated,
        )

        log_out = html.a(
            'Log out',
            attrs__href='/iommi-admin/logout/',
            include=lambda request, **_: request.user.is_authenticated,
        )

    class IndexPage(Page):
        header = Header('iommi examples')

        form_header = Header('Form examples')

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

        table_header = Header('Table examples')

        # ...or just throw a big chunk of html in here
        table_links = mark_safe("""
        <a href="table_readme_example_1/">Example 1 from the README</a><br>
        <a href="table_readme_example_2/">Example 2 from the README</a><br>
        <a href="table_auto_example_1/">Example 1 of auto table</a><br>
        <a href="table_auto_example_2/">Example 2 of auto table</a><br>
        <a href="table_kitchen_sink/">Kitchen sink</a><br>
        <a href="table_as_view/">Table.as_view() example</a><br>
        """)

        page_header = Header('Page examples')

        page_links = mark_safe("""
        <a href="page_busy/">A busy page with lots of stuff</a><br>
        <a href="all_field_sorts">Show different type of form field types</a><br>
        <a href="all_column_sorts">Show different type of table column types</a>
        """)

        menu_header = Header('Menu examples')

        menu_examples = mark_safe("""
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
            {% extends "iommi/base_test.html" %} 
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
            a=Action.submit(attrs__value='Foo', group='x'),
            b=Action.submit(attrs__value='Bar', group='x'),
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

    checkbox = Field.boolean()


class SinkForm(Form):
    class Meta:
        _name = 'sink'

    foo = Field()


def form_kitchen(request):
    ensure_objects()

    def kitchen_form_post_handler(form, **_):
        if not form.is_valid():
            return

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


def table_auto_example_1(request):
    return Table(
        auto__model=Foo,
    )


def table_auto_example_2(request):
    return Table(
        auto__model=Foo,
        rows=lambda table, **_: Foo.objects.all(),
    )


def table_kitchen_sink(request):
    fill_dummy_data()

    class BarTable(Table):
        select = Column.select()  # Shortcut for creating checkboxes to select rows
        b__a = Column.number()  # Show "a" from "b". This works for plain old objects too.

        b = Column.from_model(
            model=TBar,
            model_field_name='b',
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
            title = 'Kitchen sink'
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
        header=Header('All sorts of fields'),
        form=Form(
            fields={
                f'{t}__call_target__attribute': t
                for t in keys(get_members(
                    cls=Field,
                    member_class=Shortcut,
                    is_member=is_shortcut
                ))
                if t not in [
                    # These only work if we have an instance
                    'foreign_key',
                    'many_to_many']
            },
            fields__radio__choices=some_choices,
            fields__choice__choices=some_choices,
            fields__choice_queryset__choices=TFoo.objects.all(),
            fields__multi_choice__choices=some_choices,
            fields__multi_choice_queryset__choices=TBar.objects.all(),
            fields__info__value="This is some information",
            fields__text__initial='Text',
            fields__textarea__initial='text area\nsecond row',
            fields__integer__initial=3,
            fields__float__initial=3.14,
            fields__password__initial='abc123',
            fields__boolean__initial=True,
            fields__datetime__initial=datetime.now(),
            fields__date__initial=date.today(),
            fields__time__initial=datetime.now().time(),
            fields__decimal__initial=3.14,
            fields__url__initial='http://iommi.rocks',
            fields__email__initial='example@example.com',
            fields__phone_number__initial='+1 555 555',

            actions__submit__include=False,
        )
    ))


class DummyRow:
    def __init__(self, idx):
        self.idx = idx

    def __getattr__(self, attr):
        _, _, shortcut = attr.partition('column_of_type_')
        s = f'{shortcut} #{self.idx}'
        if shortcut == 'link':
            class Link:
                def get_absolute_url(self):
                    return '#'

                def __str__(self):
                    return 'title'
            return Link()
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
            for t in keys(get_members(
                cls=Column,
                member_class=Shortcut,
                is_member=is_shortcut
            ))
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
        header=Header('All sorts of columns'),
        form=ShortcutSelectorForm(),
        table=Table(
            columns={
                f'column_of_type_{t}': dict(
                    type_specifics.get(t, {}),
                    call_target__attribute=t,
                )
                for t in selected_shortcuts
            },
            rows=[DummyRow(i) for i in range(10)],
        )
    ))


def select_style_post_handler(form, **_):
    style = form.fields.style.value
    settings.IOMMI_DEFAULT_STYLE = style
    return HttpResponseRedirect('/')


class StyleSelector(Form):
    class Meta:
        actions__submit__post_handler = select_style_post_handler

    style = Field.choice(
        choices=[
            k for k in
            keys(iommi.style._styles)
            if k not in ('test', 'base', 'bootstrap_horizontal')
        ],
        initial=lambda form, field, **_: getattr(settings, 'IOMMI_DEFAULT_STYLE', iommi.style.DEFAULT_STYLE),
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
