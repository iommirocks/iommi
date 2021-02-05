from iommi import html
from iommi.style import (
    Style,
)
from iommi.style_base import base
from iommi.style_font_awesome_4 import font_awesome_4

semantic_ui_base = Style(
    base,
    root__assets=dict(
        css=html.link(
            attrs=dict(
                rel='stylesheet',
                href='https://cdnjs.cloudflare.com/ajax/libs/semantic-ui/2.4.1/semantic.min.css',
                integrity='sha256-9mbkOfVho3ZPXfM7W8sV2SndrGDuh7wuyLjtsWeTI1Q=',
                crossorigin='anonymous',
            ),
        ),
        js=html.script(
            attrs=dict(
                src='https://cdnjs.cloudflare.com/ajax/libs/semantic-ui/2.4.1/semantic.min.js',
                integrity='sha256-t8GepnyPmw9t+foMh3mKNvcorqNHamSKtKRxxpUEgFI=',
                crossorigin='anonymous',
            ),
        ),
    ),
    Container=dict(
        tag='div',
        attrs__class={
            'ui': True,
            'main': True,
            'container': True,
        },
    ),
    Form=dict(
        attrs__class=dict(
            ui=True,
            form=True,
            error=True,  # semantic ui hides error messages otherwise
        ),
    ),
    Field=dict(
        shortcuts=dict(
            boolean=dict(
                template='iommi/form/semantic_ui/row_checkbox.html',
            ),
            radio=dict(
                input__template='iommi/form/semantic_ui/radio.html',
                attrs__class={'grouped fields': True},
            ),
        ),
        attrs__class__field=True,
        help__attrs__class=dict(
            ui=True,
            pointing=True,
            label=True,
        ),
    ),
    Action=dict(
        shortcuts=dict(
            button__attrs__class={
                'ui': True,
                'button': True,
            },
            primary__attrs__class__primary=True,
            delete__attrs__class__negative=True,
        ),
    ),
    Table=dict(
        attrs__class__table=True,
        attrs__class__ui=True,
        attrs__class__celled=True,
        attrs__class__sortable=True,
    ),
    Column=dict(
        shortcuts=dict(
            select=dict(
                header__attrs__title='Select all',
            ),
            number=dict(
                cell__attrs__class={
                    'ui': True,
                    'container': True,
                    'fluid': True,
                    'right aligned': True,
                },
                header__attrs__class={
                    'ui': True,
                    'container': True,
                    'fluid': True,
                    'right aligned': True,
                },
            ),
        )
    ),
    Query=dict(
        form__attrs__class__fields=True,
        form_container=dict(
            tag='span',
            attrs__class={
                'ui form': True,
                'fields': True,
            },
        ),
    ),
    Menu=dict(
        attrs__class=dict(
            ui=True,
            menu=True,
        ),
        tag='div',
    ),
    MenuItem__a__attrs__class__item=True,
    Paginator=dict(
        template='iommi/table/semantic_ui/paginator.html',
        item__attrs__class__item=True,
        attrs__class=dict(
            ui=True,
            pagination=True,
            menu=True,
        ),
        active_item__attrs__class=dict(
            item=True,
            active=True,
        ),
    ),
    Errors__attrs__class=dict(
        ui=True,
        error=True,
        message=True,
    ),
)
semantic_ui = Style(
    semantic_ui_base,
    font_awesome_4,
)
