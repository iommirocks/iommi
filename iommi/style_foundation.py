from iommi.style import (
    Style,
)
from iommi.style_font_awesome_4 import font_awesome_4
from iommi.style_base import base

foundation_base = Style(
    base,
    font_awesome_4,
    base_template='iommi/base_foundation.html',
    Container=dict(
        tag='div',
        attrs__class={
            'grid-container': True,
        },
    ),
    Action=dict(
        shortcuts=dict(
            button__attrs__class__button=True,
            delete__attrs__class__alert=True,
        ),
    ),
    Menu=dict(
        tag='nav',
        items_container__attrs__class={'menu': True},
        items_container__tag='ul',
        attrs__class={'top-bar': True},
    ),
    MenuItem=dict(
        tag='li',
    ),
    Column=dict(
        shortcuts=dict(
            delete__cell__link__attrs__class=dict(alert=True, button=True,)
        ),
    ),
    Query__form__iommi_style='foundation_horizontal',
    Paginator=dict(
        template='iommi/table/bootstrap/paginator.html',
        container__attrs__class__pagination=True,
        active_item__attrs__class={'current': True},
    ),
)


foundation = Style(
    foundation_base,
)

foundation_horizontal = Style(
    foundation_base,
    Form__attrs__class={
    },
    Field=dict(
        shortcuts=dict(
            boolean__attrs__class={'medium-2': True, 'medium-4': False},
            boolean_tristate__attrs__class={'medium-2': True, 'medium-4': False},
        ),
        attrs__class={
            'medium-4': True,
            'cell': True,
        },
    ),
)
