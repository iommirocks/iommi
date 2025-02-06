from iommi.style import Style
from iommi.style_base import (
    base,
    select2_enhanced_forms,
)
from iommi.style_font_awesome_4 import font_awesome_4

test = Style(
    base,
    font_awesome_4,
    select2_enhanced_forms,
    internal=True,
    root__assets=None,
    root__endpoints=None,
    Field=dict(
        shortcuts=dict(),
    ),
    FieldGroup=dict(
        tag='div',
        attrs__class__form_group=True,
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
    Menu=dict(tag='nav', items_container__tag='ul'),
    MenuItem=dict(
        tag='li',
        a__attrs__class={'link': True},
    ),
)
