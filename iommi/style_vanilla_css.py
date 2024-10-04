from django.utils.translation import gettext_lazy

from iommi.asset import Asset
from iommi.style import (
    Style,
)
from iommi.style_base import (
    base,
    select2_enhanced_forms,
)
from iommi.style_font_awesome_4 import font_awesome_4

vanilla_css_base = Style(
    base,
    sub_styles__horizontal=dict(
        Field=dict(
            attrs__style={
                'display': 'inline-block',
            },
        ),
        Form__attrs__class={
            'p-form--inline': True,
        },
    ),
    root__assets=dict(
        css=Asset.css(
            attrs=dict(
                href='https://assets.ubuntu.com/v1/vanilla-framework-version-4.16.0.min.css',
            ),
        ),
    ),
    Container=dict(
        tag='div',
        attrs__class={
            
        },
        attrs__style__margin='1rem',
    ),
    Form=dict(
        attrs__class={'p-form': True},
    ),
    Field=dict(
        shortcuts=dict(
            number__input__attrs__class={'u-align--right': True},
        ),
        attrs__class={
        },
        input__attrs__class={
            'is-invalid': lambda field, **_: bool(field.errors),
        },
        help__attrs__class={
            'form-text': True,
            'text-muted': True,
        },
    ),
    FieldGroup=dict(
        tag='div',
        attrs__class={'form-row': True},
        assets__field_group_select2_css=Asset(
            '''
        .form-group .select2-container {
            display: block;
        }
        ''',
            tag='style',
        ),
    ),
    Action=dict(
        shortcuts=dict(
            # In vanilla_css one must choose a button style (secondary, success, ...)
            # otherwise the styling is roughly identical to text.
            button__attrs__class={
                'btn': True,
                'btn-secondary': True,
            },
            primary__attrs__class={
                'btn-primary': True,
                'btn-secondary': False,
            },
            delete__attrs__class={
                'btn-danger': True,
                'btn-secondary': False,
            },
        ),
    ),
    Table=dict(
        attrs__class__table=True,
        attrs__class={'table-sm': True},
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
        form_container=dict(
            tag='span',
            attrs__class={
                'form-row': True,
                'align-items-center': True,
            },
        ),
    ),
    Menu=dict(
        tag='header',
        attrs__class={
            'p-navigation__banner': True,
        },
        items_container__attrs__class={
            'p-navigation__items': True,
        },
        items_container__tag='ul',
    ),
    MenuItem=dict(
        tag='li',
        a__attrs__class={'p-navigation__link': True},
        attrs__class={'p-navigation__item': True},
        active_class='is-selected',
    ),
    Paginator=dict(
        container__attrs__class={'p-pagination': True},
        active_item__attrs__class={'p-pagination__item': True},
        link__attrs__class={'p-pagination__link': True},
        active_link__attrs__class={'p-pagination__link': True, 'is-active': True},
        item__attrs__class={'p-pagination__item': True},
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
vanilla_css = Style(
    vanilla_css_base,
    font_awesome_4,
    select2_enhanced_forms,
)
