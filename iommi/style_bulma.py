from iommi.style import (
    Style,
)
from iommi.style_font_awesome_4 import font_awesome_4
from iommi.style_base import base

bulma_base = Style(
    base,
    base_template='iommi/base_bulma.html',
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
        template='iommi/form/bulma/row.html',
        label__attrs__class__label=True,
        input__attrs__class__input=True,
        errors__template='iommi/form/bulma/errors.html',
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
