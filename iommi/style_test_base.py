from iommi.style import Style
from iommi.style_base import base
from iommi.style_font_awesome_4 import font_awesome_4

test = Style(
    base,
    font_awesome_4,
    Field=dict(
        shortcuts=dict(
        ),
    ),
    Table=dict(
        attrs__class__table=True,
    ),
    Column=dict(
        shortcuts__number__cell__attrs__class__rj=True,
    ),
    Paginator=dict(
        template='iommi/table/bootstrap/paginator.html',
    ),
    Menu=dict(
        tag='nav',
        items_container__tag='ul'
    ),
    MenuItem=dict(
        tag='li',
        a__attrs__class={'link': True},
    ),
)
