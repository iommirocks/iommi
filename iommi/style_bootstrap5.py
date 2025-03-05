from textwrap import dedent

from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from iommi.asset import Asset
from iommi.style import (
    Style,
)
from iommi.style_base import (
    base,
    select2_enhanced_forms,
)
from iommi.style_bootstrap_icons import bootstrap_icons

bootstrap5_base = Style(
    base,
    sub_styles__horizontal=dict(
        Field=dict(
            shortcuts=dict(
                boolean__label__attrs__class={
                    'col-form-label': True,
                },
            ),
            attrs__class={
                'mb-3': False,
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
                href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
                integrity="sha256-PI8n5gCcz9cQqQXm3PEtDuPG8qx9oFsFctPg0S5zb8g=",
                crossorigin="anonymous",
            ),
        ),
        popper_js=Asset.js(
            attrs=dict(
                src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.10.2/dist/umd/popper.min.js",
                integrity="sha384-7+zCNj/IqJ95wo16oMtfsKbZ9ccEh31eOz1HGyDuCQ6wgnyJNSYdrPa03rtR1zdB",
                crossorigin="anonymous",
            )
        ),
        js=Asset.js(
            attrs=dict(
                src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
                integrity="sha256-CDOy6cOibCWEdsRiZuaHf8dSGGJRYuBGC+mjoJimHGw=",
                crossorigin="anonymous",
            )
        ),
        auto_darkmode=Asset.js(
            children__source=mark_safe(dedent('''
                function updateTheme() {
                    document.querySelector("html").setAttribute("data-bs-theme", window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
                }
                window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateTheme)
                updateTheme()             
            '''))
        ),
        select2_dark_mode=Asset(
            tag='style',
            children__source=dedent('''
            [data-bs-theme=dark] .select2-container--default .select2-selection--single,
            [data-bs-theme=dark] .select2-container--default .select2-results__option,
            [data-bs-theme=dark] .select2-container--default .select2-selection--multiple {
                color: white;
                background: var(--bs-body-bg);;
            }
            [data-bs-theme=dark]  .select2-container--default .select2-selection--multiple .select2-selection__choice {
                color: white;
                background: #444;
            }
            ''')
        )
    ),
    Container=dict(
        tag='div',
        attrs__class={
            'container': True,
            'mt-5': True,
        },
    ),
    Field=dict(
        shortcuts=dict(
            boolean=dict(
                input__attrs__class={'form-check-input': True, 'form-control': False},
                attrs__class={'form-check': True},
                label__attrs__class={'form-label': True},
            ),
            radio=dict(
                attrs__class={
                    'mb-3': False,
                    'form-check': True,
                },
                input__attrs__class={
                    'form-check-input': True,
                    'form-control': False,
                },
            ),
            choice__input__attrs__class={'form-select': True},
        ),
        attrs__class={
            'mb-3': True,
            'col': lambda field, **_: field.group is not None,
        },
        input__attrs__class={
            'form-control': True,
            'is-invalid': lambda field, **_: bool(field.errors),
        },
        help__attrs__class={
            'form-text': True,
            'text-muted': True,
        },
        label__attrs__class={'form-label': True},
        label__attrs__class__form_label=True,  # need this to make class render
    ),
    FieldGroup=dict(
        tag='div',
        attrs__class={'row': True},
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
                'row': True,
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
            'bg-secondary': True,
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
bootstrap5 = Style(
    bootstrap5_base,
    bootstrap_icons,
    select2_enhanced_forms,
)
