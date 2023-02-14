
from iommi.style import Style
from iommi.style_base import base
from iommi.asset import Asset

uikit = Style(
    base,
    root__assets__css=Asset.css(
        attrs=dict(
            href='https://cdn.jsdelivr.net/npm/uikit@3.6.8/dist/css/uikit.min.css',
            crossorigin='anonymous',
        ),
    ),
    Container=dict(
        tag='div',
        attrs__class={
            'uk-container': True,
        },
    ),
    Menu=dict(
        items_container=dict(
            tag='ul',
            attrs__class={'uk-nav': True, 'uk-nav-default': True},
        ),
    ),
    MenuItem=dict(
        tag='li',
        active_class_on_item=True,
        active_class='uk-active',
    ),
    Form__attrs__class={'uk-form-stacked': True},
    Field=dict(
        shortcuts=dict(
            boolean=dict(
                template='iommi/form/uikit/row_checkbox.html',
                input__attrs__class={'uk-input': False},
            ),
            radio=dict(
                input__attrs__class={'uk-input': False},
            ),
        ),
        label__attrs__class={'uk-form-label': True},
        input__attrs__class={'uk-input': True},
    ),
    Table=dict(
        attrs__class={'uk-table': True},
    ),
    Action=dict(
        shortcuts=dict(
            button__attrs__class={
                'uk-button': True,
                'uk-button-default': True,
            },
            primary__attrs__class={'uk-button-primary': True},
            delete__attrs__class={'uk-button-danger': True},
        )
    ),
    Paginator=dict(
        container__tag='ul',
        item__tag='li',
        active_item=dict(
            tag='li',
            attrs__class={'uk-active': True},
        ),
        container__attrs__class={'uk-pagination': True},
    )
)
