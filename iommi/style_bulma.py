from django.utils.safestring import mark_safe

from iommi import Fragment
from iommi.asset import Asset
from iommi.style import (
    Style,
)
from iommi.style_base import base
from iommi.style_font_awesome_4 import font_awesome_4

navbar_burger_click_js = Fragment(
    mark_safe(
        """\
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
"""
    )
)

bulma_base = Style(
    base,
    root__assets=dict(
        css=Asset.css(
            attrs__href='https://cdn.jsdelivr.net/npm/bulma@0.9.1/css/bulma.min.css',
        ),
        navbar_burger_click_js=navbar_burger_click_js,
    ),
    sub_styles__horizontal=dict(
        Field=dict(
                attrs__class={
                    'mr-4': True,
                },
                label__attrs__class={
                    'mt-2': True,
                    'mr-1': True,
                },
            ),
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
        input__attrs__class={
            'is-danger': lambda field, **_: bool(field.errors),
        },
        errors__attrs__class={
            'is-danger': True,
            'help': True,
        },
        help__attrs__class=dict(
            help=True,
        ),
    ),
    Actions=dict(
        tag="div",
        attrs__class=dict(links=False, buttons=True),
    ),
    Action=dict(
        shortcuts=dict(
            # In bulma the most neutral button styling is button, which
            # gets you a button that's just an outline.
            button__attrs__class={
                'button': True,
            },
            delete__attrs__class={
                'is-danger': True,
            },
            primary__attrs__class={
                'is-primary': True,
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


