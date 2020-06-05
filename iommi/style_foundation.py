from iommi.style import (
    Style,
)
from iommi.style_font_awesome_4 import font_awesome_4
from iommi.style_base import base

foundation = Style(
    base,
    font_awesome_4,
    Action=dict(
        shortcuts=dict(
            button__attrs__class__button=True,
            delete__attrs__class__alert=True,
        ),
    ),
    Menu=dict(
        tag='nav',
        items_container__attrs__class={'menu': True},
        items_container__tag='ul'
    ),
    MenuItem=dict(
        tag='li',
    ),
)
