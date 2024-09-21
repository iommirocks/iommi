from django.utils.translation import gettext_lazy

from iommi import html
from iommi.asset import Asset
from iommi.style import (
    Style,
)
from iommi.style_base import (
    base,
    select2_enhanced_forms,
)
from iommi.style_font_awesome_4 import font_awesome_4

us_web_design_system_base = Style(
    base,
    sub_styles__horizontal=dict(
        Field=dict(
            shortcuts=dict(
              choice_queryset__input__attrs__style__width='100%',
            ),
            attrs__class={
                'display-inline-block': True,
            },
        ),

    ),
    root__assets=dict(
        css=Asset.css(
            attrs=dict(
                href='https://cdnjs.cloudflare.com/ajax/libs/uswds/3.8.2/css/uswds.min.css',
                integrity='sha512-c54cBXlMCHyctBarSG5INC3euZr4UvbldzM8bm0d3K0mKW7Whi4SN+tf7RuRhTQXdztpfyeIgcdVPSEc1PdaTQ==',
                crossorigin='anonymous',
            ),
        ),
        js_init=Asset.js(
            attrs=dict(
                src='https://cdnjs.cloudflare.com/ajax/libs/uswds/3.8.2/js/uswds-init.min.js',
                integrity='sha512-JfvuOYD20WEe+MHjxs94+e381uz0xByQuxAL5eeImmu7ApiFc7nQllnBh+wSznY+bDOZ0GFhIdBzMVl3FosWiw==',
                crossorigin='anonymous',
            )
        ),
        js=Asset.js(
            attrs=dict(
                src='https://cdnjs.cloudflare.com/ajax/libs/uswds/3.8.2/js/uswds.min.js',
                integrity='sha512-iEkS/2oGQisJgioadYOkqiscJz4DULhifYSSBuV5Yu3W9BQc4N9B2vUfpqFwiivapuAx9w13Ke4sN/ghmx7UeQ==',
                crossorigin='anonymous',
            ),
            in_body=True,
        ),
        css_select2_fix=html.style(
            children__text='''
            .select2-results__options {
                width: 100%;
            }
            '''
        ),
    ),
    Container=dict(
        tag='div',
        attrs__class={'margin-1': True},
    ),
    Field=dict(
        shortcuts=dict(
            boolean=dict(
                input__attrs__class={'usa-checkbox__input': True},
                attrs__class={'usa-checkbox': True},
                label__attrs__class={'usa-checkbox__label': True},
            ),
            radio=dict(
                attrs__class={
                    'usa-radio': True,
                },
                input__attrs__class={
                    'usa-radio__input': True,
                },
                input__template='iommi/form/us_web_design_system/radio.html',
            ),
            checkboxes=dict(
                attrs__class={'usa-checkbox': False},
                input__attrs__class={'usa-checkbox__input': True},
                label__attrs__class={'usa-checkbox__label': True},
            ),
            number__input__attrs__class={'text-right': True},
            text=dict(
                input__attrs__class={'usa-input__input': True},
                label__attrs__class={'usa-label': True},
            ),
            textarea=dict(
                input__attrs__class={'usa-textarea': True},
                label__attrs__class={'usa-label': True},
            ),
        ),
        attrs__class={
        },
        input__attrs__class={
            'is-invalid': lambda field, **_: bool(field.errors),
        },
        label__attrs__class={'usa-label': True},
    ),
    FieldGroup=dict(
        tag='fieldset',
        attrs__class={'usa-fieldset': True},
        assets__field_group_select2_css=Asset(
            '''
        .form-group .select2-container {
            display: block;
        }
        ''',
            tag='style',
        ),
    ),
    Actions__attrs__class={'margin-1': True},
    Action=dict(
        shortcuts=dict(
            # In us_web_design_system one must choose a button style (secondary, success, ...)
            # otherwise the styling is roughly identical to text.
            button__attrs__class={
                'usa-button': True,
                'btn-secondary': True,
            },
            primary__attrs__class={
                'btn-primary': True,
                'usa-button--secondary': False,
            },
            delete__attrs__class={
                'btn-danger': True,
                'btn-secondary': False,
            },
        ),
    ),
    Table=dict(
        attrs__class={'usa-table': True},
    ),
    Column=dict(
        header__attrs__class={'text-nowrap': True},
        shortcuts=dict(
            select=dict(
                header__attrs__title=gettext_lazy('Select all'),
                header__attrs__class={'text-center': True},
                cell__attrs__class={'text-center': True},
                extra__icon='fa fa-check-square-o',
            ),
            number=dict(
                cell__attrs__class={'text-right': True},
                header__attrs__class={'text-right': True},
            ),
            boolean__cell__attrs__class={'text-center': True},
            delete=dict(
                cell__link__attrs__class={'text-danger': True},
            ),
        ),
    ),
    Query=dict(
        form__iommi_style='horizontal',
    ),
    Menu=dict(
        tag='header',
        attrs__class={'usa-header': True, 'usa-header--basic': True},
        items_container__attrs__class={'usa-nav__primary': True, 'usa-accordion': True},
        items_container__tag='ul',
    ),
    MenuItem=dict(
        tag='li',
        a__attrs__class={},
        attrs__class={'usa-nav__primary-item': True},
        active_class='usa-current',
    ),
    Paginator=dict(
        tag='nav', # TODO: implement this in other styles, maybe even remove templates!
        attrs__class={'usa-pagination': True},
        container__attrs__class={'usa-pagination__list': True},
        container__tag='ul',
        active_item__tag='li',
        active_item__attrs__class={
            'usa-pagination__item': True,
            'usa-pagination__page-no': True,
        },
        active_link__attrs__class={'usa-current': True},
        link__attrs__class={
            'usa-pagination__button': True,
        },
        item__tag='li',
        item__attrs__class={
            'usa-pagination__item': True,
            'usa-pagination__page-no': True,
        },
    ),
    Errors=dict(
        attrs__class={'text-danger': True},
    ),
    DebugMenu=dict(
        attrs__class={
            'bg-primary': False,
            'navbar': False,
            'navbar-dark': False,
        },
        items_container__attrs__class={
            'pl-0': True,
            'mb-0': True,
            'small': True,
        },
    ),
    Admin=dict(
        parts__menu=dict(
            # tag='foo',   # TODO: This styling is ignored. We should be able to do this.
            attrs__class={
                'fixed-top': True,
            },
        ),
    ),
    Errors__attrs__class={'with-errors': True},
)
us_web_design_system = Style(
    us_web_design_system_base,
    font_awesome_4,
    select2_enhanced_forms,
)
