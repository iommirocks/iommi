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
    root__assets=dict(
        jquery=None,
        select2_js=None,
        select2_css=None,
        icons=None,
        iommi_js=None,
        iommi_js_init=None,
        iommi_scroll_js=None,
        meta=None,
    ),
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
