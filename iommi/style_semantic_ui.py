from iommi.style import (
    Style,
)
from iommi.style_font_awesome_4 import font_awesome_4
from iommi.style_base import base

semantic_ui_base = Style(
    base,
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
            radio__input__template='iommi/form/semantic_ui/radio.html',
            radio__attrs__class={'grouped fields': True},
        ),
        attrs__class__field=True,
        template='iommi/form/semantic_ui/row.html',
        errors__template='iommi/form/semantic_ui/errors.html',
    ),
    Action=dict(
        shortcuts=dict(
            button__attrs__class={
                'ui': True,
                'button': True,
            },
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
    Query__form__attrs__class__fields=True,
    Menu=dict(
        attrs__class=dict(ui=True, menu=True, vertical=True),
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
        )
    ),
)
semantic_ui = Style(
    semantic_ui_base,
    font_awesome_4,
)
