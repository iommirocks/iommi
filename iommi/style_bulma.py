from iommi.style import (
    Style,
)
from iommi.style_font_awesome_4 import font_awesome_4
from iommi.style_base import base
from iommi.fragment import html
from django.utils.safestring import mark_safe


_js = html.script(
    children__text=mark_safe(r"""
    $(document).ready(function() {
          // Check for click events on the navbar burger icon
          $(".navbar-burger").click(function() {

              // Toggle the "is-active" class on both the "navbar-burger" and the "navbar-menu"
              $(".navbar-burger").toggleClass("is-active");
              $(".navbar-menu").toggleClass("is-active");

          });
    });
    """)
)

bulma_base = Style(
    base,
    assets=dict(
        css=html.link(
            attrs__rel='stylesheet',
            attrs__href='https://cdn.jsdelivr.net/npm/bulma@0.9.1/css/bulma.min.css',
        ),
        js=_js,
    ),
    Header__attrs__class={
        'title': True,
        'is-1': lambda fragment, **_: fragment.tag == 'h1',
        'is-2': lambda fragment, **_: fragment.tag == 'h2',
        'is-3': lambda fragment, **_: fragment.tag == 'h3',
        'is-4': lambda fragment, **_: fragment.tag == 'h4',
        'is-5': lambda fragment, **_: fragment.tag == 'h5',
        'is-6': lambda fragment, **_: fragment.tag == 'h6',
    },
    Container=dict(
        tag='div',
        attrs__class={
            'main': True,
            'container': True,
        },
    ),
    Field=dict(
        shortcuts=dict(
            boolean=dict(
                input__attrs__class__input=False,
                label__attrs__class__checkbox=True,
                label__attrs__class__label=False,
            ),
            textarea=dict(
                input__attrs__class__input=False,
                input__attrs__class__textarea=True,
            ),
            radio=dict(
                input__attrs__class__input=False,
            ),
        ),
        attrs__class__field=True,
        template='iommi/form/bulma/field.html',
        label__attrs__class__label=True,
        input__attrs__class__input=True,
        help__attrs__class=dict(
            help=True,
        )
    ),
    Action=dict(
        shortcuts=dict(
            button__attrs__class={
                'button': True,
            },
            delete__attrs__class={
                'button': True,
                'is-danger': True,
            },
        ),
    ),
    Table={
        'attrs__class__table': True,
        'attrs__class__is-fullwidth': True,
        'attrs__class__is-hoverable': True,
    },
    Column=dict(
        shortcuts=dict(
            select=dict(
                header__attrs__title='Select all',
            ),
            number=dict(
                cell__attrs__class={
                    'has-text-right': True,
                },
                header__attrs__class={
                    'has-text-right': True,
                },
            ),
        ),
    ),
    Query__form=dict(
        iommi_style='bulma_horizontal',
        attrs__class__content=True,
    ),
    Query__form_container=dict(
        tag='span',
        attrs__class={
            'is-horizontal': True,
            'field': True,
        },
    ),
    Menu=dict(
        attrs__class__navbar=True,
        tag='nav',
    ),
    MenuItem__a__attrs__class={'navbar-item': True},
    MenuItem__active_class='is-active',
    DebugMenu=dict(
        tag='aside',
        attrs__class={
            'navbar': False,
            'menu': True,
        },
    ),
    Paginator=dict(
        template='iommi/table/bulma/paginator.html',
    ),
    Errors__attrs__class={
        'help': True,
        'is-danger': True,
    },
)
bulma = Style(
    bulma_base,
    font_awesome_4,
)

bulma_horizontal = Style(
    bulma,
    Field=dict(
        attrs__class={
            'is-horizontal': True,
            'mr-4': True,
        },
        label__attrs__class={
            'mt-2': True,
            'mr-1': True,
        },
    ),
)
