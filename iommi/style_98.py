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

w98_base = Style(
    base,
    base_template='iommi/style_98_base.html', 
    sub_styles__horizontal=dict(
        Field=dict(
            shortcuts=dict(
                boolean__label__attrs__class={
                    'col-form-label': True,
                },
            ),
            attrs__class={
                'form-group': False,
                'col-sm-3': True,
                'my-1': True,
            },
        ),
        Form__attrs__class={
            'align-items-center': True,
        },
    ),
    root__assets=dict(
        css=Asset.css(
            attrs=dict(
                href='https://unpkg.com/98.css',
                crossorigin='anonymous',
            ),
        ),
        popper_js=Asset.js(
            attrs=dict(
                src='https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js',
                integrity='sha384-Q6E9RHvbIyZFJoft+2mJbHaEWldlvI9IOYy5n3zV9zzTtmI3UksdQRVvoxMfooAo',
                crossorigin='anonymous',
            )
        ),
        js=Asset.js(
            attrs=dict(
                src='https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/js/bootstrap.min.js',
                integrity='sha384-wfSDF2E50Y2D1uUdj0O3uMBJnjuUD4Ih7YwaYd1iqfktj0Uod8GCExl3Og8ifwB6',
                crossorigin='anonymous',
            )
        ),
    ),
    Container=dict(
        tag='div',
    ),
    Field=dict(
        shortcuts=dict(
            boolean=dict(
                input__attrs__class={'form-check-input': True, 'form-control': False},
                attrs__class={'form-check': True},
                label__attrs__class={'form-check-label': True},
            ),
            radio=dict(
                attrs__class={
                    'form-group': False,
                    'form-check': True,
                },
                input__attrs__class={
                    'form-check-input': True,
                    'form-control': False,
                },
            ),
            checkboxes=dict(
                attrs__class={
                    'form-group': False,
                    'form-check': True,
                },
                input__attrs__class={
                    'form-check-input': True,
                    'form-control': False,
                },
            ),
            number__input__attrs__class={'text-right': True},
        ),
        attrs__class={
            'form-group': True,
        },
        input__attrs__class={
            'form-control': True,
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
            # In bootstrap one must choose a button style (secondary, success, ...)
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
        container__attrs__class={'sunken-panel': True},
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
        tag='nav',
        attrs__class={
            'navbar': True,
            'navbar-expand-lg': True,
            'navbar-dark': True,
            'bg-primary': True,
        },
        items_container__attrs__class={'navbar-nav': True},
        items_container__tag='ul',
    ),
    MenuItem=dict(
        tag='li',
        a__attrs__class={'nav-link': True},
        attrs__class={'nav-item': True},
    ),
    Paginator=dict(
        template='iommi/table/bootstrap/paginator.html',
        container__attrs__class__pagination=True,
        active_item__attrs__class={'page-item': True, 'active': True},
        link__attrs__class={'page-link': True},
        item__attrs__class={'page-item': True},
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
w98 = Style(
    w98_base,
    font_awesome_4,
    select2_enhanced_forms,
)
