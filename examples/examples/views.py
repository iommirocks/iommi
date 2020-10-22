import json
from datetime import (
    date,
    datetime,
)
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.db import OperationalError
from django.urls import (
    include,
    path,
    reverse,
)
from tri_declarative import (
    get_members,
    is_shortcut,
    LAST,
    Namespace,
    Shortcut,
)

import iommi.part
import iommi.style
import iommi.traversable
from iommi import (
    Column,
    Fragment,
    Header,
    html,
    Page,
    Table,
)
from iommi.admin import (
    Admin,
    Auth,
)
from iommi.base import (
    items,
    keys,
)
from iommi.form import (
    Field,
    Form,
)
from iommi.menu import (
    Menu,
    MenuItem,
)
from iommi.style import validate_styles
from .models import (
    Album,
    Artist,
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

    if not TBar.objects.all():
        # Fill in some dummy data if none exists
        for i in range(200):
            f = TFoo.objects.create(a=i, name='Foo: %s' % i)
            TBar.objects.create(b=f, c='foo%s' % (i % 3))

    # Get some artist and album data

    if not Path(settings.STATIC_ROOT).joinpath('album_art').exists():
        try:
            from scrape_data import scrape_data
            scrape_data()
        except ImportError as e:
            print("!!! Unable to scrape artist and track data.")
            print(e)

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


class StyleSelector(Form):
    class Meta:
        @staticmethod
        def actions__submit__post_handler(request, form, **_):
            style = form.fields.style.value
            settings.IOMMI_DEFAULT_STYLE = style

    style = Field.choice(
        choices=[
            k for k in
            keys(iommi.style._styles)
            if k not in ('test', 'base') and not k.endswith('_horizontal')
        ],
        initial=lambda form, field, **_: getattr(settings, 'IOMMI_DEFAULT_STYLE', iommi.style.DEFAULT_STYLE),
    )


menu = Menu(
    sub_menu=dict(
        root=MenuItem(url='/'),
        page_examples=MenuItem(url='/page'),
        form_examples=MenuItem(url='/form'),
        table_examples=MenuItem(url='/table'),
        menu_examples=MenuItem(url='/menu'),
        supernaut=MenuItem(url='/supernaut'),
        admin=MenuItem(url='/iommi-admin'),
        login=MenuItem(
            display_name='Log in',
            url='/iommi-admin/login/?next=/',
            include=lambda request, **_: not request.user.is_authenticated,
        ),
        log_out=MenuItem(
            display_name='Log out',
            url='/iommi-admin/logout/',
            include=lambda request, **_: request.user.is_authenticated,
        )
    )
)


class ExamplesPage(Page):
    menu = menu

    footer = html.div(
        html.hr(),
        html.a('iommi rocks!', attrs__href='http://iommi.rocks/'),
        StyleSelector(),
        after=LAST,
    )


class IndexPage(ExamplesPage):
    header = html.h1('Welcome to iommi examples application')
    logo = html.img(
        attrs__src='https://docs.iommi.rocks/en/latest/_static/logo.svg',
        attrs__style__width='30%',
    )


def all_field_sorts(request):
    some_choices = ['Foo', 'Bar', 'Baz']
    return ExamplesPage(parts=dict(
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
            fields__choice_queryset__choices=Artist.objects.all(),
            fields__multi_choice__choices=some_choices,
            fields__multi_choice_queryset__choices=Track.objects.all(),
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

    return ExamplesPage(parts=dict(
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


class ExampleAdmin(Admin):
    class Meta:
        iommi_style = None
        parts__menu__sub_menu = dict(
            home=MenuItem(url='/'),
            admin=MenuItem(url=lambda **_: reverse(ExampleAdmin.all_models)),
            change_password=MenuItem(url=lambda **_: reverse(Auth.change_password)),
            logout=MenuItem(url=lambda **_: reverse(Auth.logout)),
        )

        parts__footer = Fragment(
            after=LAST,
            children=dict(
                hr=html.hr(),
                style=StyleSelector(title='Change iommi style'),
            )
        )


urlpatterns = [
    path('', IndexPage().as_view()),
    path('iommi-admin/', include(ExampleAdmin.urls())),
]
