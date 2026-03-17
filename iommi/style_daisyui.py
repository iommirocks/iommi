from textwrap import dedent

from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from iommi.asset import Asset
from iommi.fragment import html
from iommi.style import Style
from iommi.style_base import (
    base,
    select2_enhanced_forms,
)
from iommi.style_font_awesome_6 import font_awesome_5_icon_formatter

font_awesome_6_icons = Style(
    internal=True,
    root__assets__fa6_icons=html.link(
        attrs__rel='stylesheet',
        attrs__href='https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.2/css/all.min.css',
    ),
    icon_formatter=font_awesome_5_icon_formatter,
    Column__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'fa-solid': True},
            icon_prefix='fa-',
        ),
        edit__extra__icon='pen-to-square',
        delete__extra__icon='trash',
        download__extra__icon='download',
        boolean__cell__format=lambda value, **_: mark_safe(
            f'<i class="fa-solid fa-check" title="{gettext_lazy("Yes")}"></i>'
        )
        if value
        else '',
        select=dict(
            extra__icon='fa-regular fa-square-check',
        ),
    ),
    Action__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'fa-solid': True},
            icon_prefix='fa-',
        ),
    ),
)

daisyui_base = Style(
    base,
    sub_styles__horizontal=dict(
        Field=dict(
            attrs__class={
                'mb-3': False,
                'flex-row': True,
                'items-center': True,
                'gap-4': True,
            },
            label__attrs__class={
                'label': False,
                'w-32': True,
                'shrink-0': True,
            },
        ),
        Form__attrs__class={
            'items-end': True,
        },
    ),
    root__assets=dict(
        daisyui_css=Asset.css(
            attrs=dict(
                href='https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css',
            ),
        ),
        tailwind_js=Asset.js(
            attrs=dict(
                src='https://cdn.tailwindcss.com',
            ),
        ),
        auto_darkmode=Asset.js(
            children__source=mark_safe(
                dedent('''
                function updateTheme() {
                    document.documentElement.setAttribute("data-theme",
                        window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
                }
                window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateTheme)
                updateTheme()
            ''')
            )
        ),
    ),
    # Tailwind's Preflight CSS reset strips browser default heading styles
    # (size, weight, margin). Restore Bootstrap-like heading hierarchy here.
    Header__attrs__class={
        'font-bold': True,
        'mb-2': True,
        'text-4xl': lambda fragment, **_: fragment.tag == 'h1',
        'text-3xl': lambda fragment, **_: fragment.tag == 'h2',
        'text-2xl': lambda fragment, **_: fragment.tag == 'h3',
        'text-xl': lambda fragment, **_: fragment.tag == 'h4',
        'text-lg': lambda fragment, **_: fragment.tag == 'h5',
        # h6 stays at base size but still gets font-bold and mb-2 above
    },
    Container=dict(
        tag='div',
        attrs__class={
            'container': True,
            'mx-auto': True,
            'mt-8': True,
            'px-4': True,
        },
    ),
    Field=dict(
        shortcuts=dict(
            boolean=dict(
                input__attrs__class={
                    'checkbox': True,
                    'input': False,
                    'input-bordered': False,
                    'w-full': False,
                },
                attrs__class={
                    'form-control': False,
                    'flex-row': True,
                    'items-center': True,
                    'gap-3': True,
                },
                label__attrs__class={'label': False, 'cursor-pointer': True},
            ),
            radio=dict(
                input__template='iommi/form/daisyui/radio.html',
                input__attrs__class={
                    'radio': True,
                    'input': False,
                    'input-bordered': False,
                    'select': False,
                    'select-bordered': False,
                    'w-full': False,
                },
            ),
            choice__input__attrs__class={
                'select': True,
                'select-bordered': True,
                'input': False,
                'input-bordered': False,
            },
            textarea=dict(
                input__attrs__class={
                    'textarea': True,
                    'textarea-bordered': True,
                    'input': False,
                    'input-bordered': False,
                },
            ),
        ),
        template='iommi/form/daisyui/field.html',
        attrs__class={
            'form-control': True,
            'mb-3': True,
        },
        input__attrs__class={
            'input': True,
            'input-bordered': True,
            'w-full': True,
            'input-error': lambda field, **_: bool(field.errors),
        },
        help__attrs__class={
            'label-text-alt': True,
            'opacity-70': True,
            'mt-1': True,
        },
        label__attrs__class={'label': True},
    ),
    FieldGroup=dict(
        tag='div',
        attrs__class={'flex': True, 'flex-row': True, 'gap-4': True, 'flex-wrap': True},
    ),
    Action=dict(
        # Default (non-button) actions render as <a> links; Tailwind's reset strips
        # color and underline, so restore them with DaisyUI's link classes.
        attrs__class={
            'link': True,
            'link-primary': True,
        },
        shortcuts=dict(
            button__attrs__class={
                'btn': True,
                'btn-secondary': True,
                'link': False,
                'link-primary': False,
            },
            primary__attrs__class={
                'btn-primary': True,
                'btn-secondary': False,
                'link': False,
                'link-primary': False,
            },
            delete__attrs__class={
                'btn-error': True,
                'btn-secondary': False,
                'link': False,
                'link-primary': False,
            },
        ),
    ),
    Table=dict(
        attrs__class={
            'table': True,
            'table-zebra': True,
        },
    ),
    Column=dict(
        header__attrs__class={'whitespace-nowrap': True},
        # Table cell links lose color/underline from Tailwind reset
        cell__link__attrs__class={'link': True, 'link-primary': True},
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
                cell__link__attrs__class={'link-error': True, 'link-primary': False},
            ),
        ),
    ),
    Query=dict(
        advanced__template='iommi/query/daisyui/advanced.html',
        form__iommi_style='horizontal',
        form_container=dict(
            tag='span',
            attrs__class={
                'flex': True,
                'flex-row': True,
                'flex-wrap': True,
                'gap-4': True,
                'items-end': True,
            },
        ),
    ),
    Menu=dict(
        tag='nav',
        attrs__class={
            'navbar': True,
            'bg-base-100': True,
            'shadow-sm': True,
        },
        items_container__attrs__class={'menu': True, 'menu-horizontal': True, 'px-1': True},
        items_container__tag='ul',
    ),
    MenuItem=dict(
        tag='li',
        a__attrs__class={},
        attrs__class={},
    ),
    Paginator=dict(
        template='iommi/table/daisyui/paginator.html',
    ),
    Errors=dict(
        # Errors renders as <ul><li>; Tailwind resets list-style and padding
        attrs__class={'text-error': True, 'text-sm': True, 'mt-1': True, 'list-disc': True, 'list-inside': True},
    ),
    DebugMenu=dict(
        attrs__class={
            'bg-base-300': True,
        },
        items_container__attrs__class={
            'text-xs': True,
        },
    ),
    Calendar=dict(
        attrs__class={'table': True},
    ),
)

daisyui = Style(
    daisyui_base,
    font_awesome_6_icons,
    select2_enhanced_forms,
)
