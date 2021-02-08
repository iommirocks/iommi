from iommi.asset import Asset
from iommi.style import (
    Style,
)
from iommi.style_base import base
from iommi.style_font_awesome_4 import font_awesome_4

foundation_base = Style(
    base,
    font_awesome_4,
    root__assets=dict(
        css=Asset.css(
            attrs=dict(
                href='https://cdn.jsdelivr.net/npm/foundation-sites@6.6.3/dist/css/foundation.min.css',
                integrity='sha256-ogmFxjqiTMnZhxCqVmcqTvjfe1Y/ec4WaRj/aQPvn+I=',
                crossorigin='anonymous',
            ),
        ),
        js=Asset.js(attrs__src='https://cdn.jsdelivr.net/npm/foundation-sites@6.6.3/dist/js/foundation.min.js'),
    ),
    Container=dict(
        tag='div',
        attrs__class={
            'grid-container': True,
        },
    ),
    Action=dict(
        shortcuts=dict(
            button__attrs__class__button=True,
            button__attrs__class__secondary=True,
            primary__attrs__class__primary=True,
            primary__attrs__class__secondary=False,
            delete__attrs__class__alert=True,
            delete__attrs__class__secondary=False,
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
            delete__cell__link__attrs__class=dict(
                alert=True,
                button=True,
            )
        ),
    ),
    Query=dict(
        form__iommi_style='foundation_horizontal',
        form_container=dict(
            tag='span',
            attrs__class={
                'grid-x': True,
                'grid-padding-x': True,
            },
        ),
    ),
    Paginator=dict(
        template='iommi/table/bootstrap/paginator.html',
        container__attrs__class__pagination=True,
        active_item__attrs__class={'current': True},
    ),
    Errors=dict(
        attrs__class=dict(callout=True, alert=True),
    ),
)


foundation = Style(
    foundation_base,
)

foundation_horizontal = Style(
    foundation_base,
    internal=True,
    Form__attrs__class={},
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
