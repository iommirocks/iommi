from textwrap import dedent

from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy

from iommi._web_compat import format_html
from iommi.asset import Asset
from iommi.style import Style
from iommi.style_base import (
    base,
    select2_enhanced_forms,
)

PATTERNFLY_VERSION = '6.7.0'


def patternfly6_icon_formatter(icon, **_):
    # PatternFly bundles the Font Awesome 5 solid icon set
    if icon == 'external':
        icon = 'external-link-alt'
    return format_html('<i class="fas fa-{}" aria-hidden="true"></i> ', icon)


# PatternFly ships with the Font Awesome 5 solid icons (only the solid font is bundled)
patternfly6_icons = Style(
    internal=True,
    icon_formatter=patternfly6_icon_formatter,
    Column__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'fas': True},
            icon_prefix='fa-',
        ),
        edit__extra__icon='pencil-alt',
        delete__extra__icon='trash',
        download__extra__icon='download',
        boolean__cell__format=lambda value, **_: (
            mark_safe(f'<i class="fas fa-check" title="{gettext_lazy("Yes")}"></i>') if value else ''
        ),
    ),
    Action__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'fas': True},
            icon_prefix='fa-',
        ),
    ),
)

patternfly6_base = Style(
    base,
    root__assets=dict(
        css=Asset.css(
            attrs__href=f'https://cdn.jsdelivr.net/npm/@patternfly/patternfly@{PATTERNFLY_VERSION}/patternfly.min.css',
        ),
        css_addons=Asset.css(
            attrs__href=f'https://cdn.jsdelivr.net/npm/@patternfly/patternfly@{PATTERNFLY_VERSION}/patternfly-addons.css',
        ),
        auto_darkmode=Asset.js(
            children__source=mark_safe(
                dedent('''
                function updateTheme() {
                    document.documentElement.classList.toggle("pf-v6-theme-dark", window.matchMedia("(prefers-color-scheme: dark)").matches)
                }
                window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateTheme)
                updateTheme()
            ''')
            )
        ),
        # Make select2 follow the PatternFly colors, so it works in dark mode
        select2_theme=Asset(
            tag='style',
            children__source=dedent('''
            .select2-container--default .select2-selection--single,
            .select2-container--default .select2-selection--multiple,
            .select2-container--default .select2-search--dropdown .select2-search__field,
            .select2-dropdown {
                color: var(--pf-t--global--text--color--regular);
                background: var(--pf-t--global--background--color--primary--default);
                border-color: var(--pf-t--global--border--color--default);
            }
            .select2-container--default .select2-selection--single .select2-selection__rendered {
                color: var(--pf-t--global--text--color--regular);
            }
            .select2-container--default .select2-results__option[aria-selected=true],
            .select2-container--default .select2-selection--multiple .select2-selection__choice {
                background: var(--pf-t--global--background--color--secondary--default);
                border-color: var(--pf-t--global--border--color--default);
            }
            '''),
        ),
    ),
    sub_styles__horizontal=dict(
        # Used by the query form: fields in a row, labels above the inputs
        Form__attrs__class={
            'pf-v6-l-flex': True,
            'pf-m-wrap': True,
            'pf-m-gap-md': True,
            'pf-m-align-items-flex-end': True,
        },
    ),
    Header__attrs__class={
        'pf-v6-c-title': True,
        'pf-m-h1': lambda fragment, **_: fragment.tag == 'h1',
        'pf-m-h2': lambda fragment, **_: fragment.tag == 'h2',
        'pf-m-h3': lambda fragment, **_: fragment.tag == 'h3',
        'pf-m-h4': lambda fragment, **_: fragment.tag == 'h4',
        'pf-m-h5': lambda fragment, **_: fragment.tag == 'h5',
        'pf-m-h6': lambda fragment, **_: fragment.tag == 'h6',
        'pf-v6-u-mb-md': True,
    },
    Container=dict(
        tag='div',
        attrs__class={'pf-v6-u-p-lg': True},
    ),
    Form=dict(
        attrs__class={'pf-v6-c-form': True, 'pf-v6-u-mb-lg': True},
        errors__template='iommi/form/patternfly6/errors.html',
        errors__attrs__class={'pf-v6-c-helper-text': True},
    ),
    Field=dict(
        template='iommi/form/patternfly6/field.html',
        shortcuts=dict(
            boolean=dict(
                template='iommi/form/patternfly6/boolean.html',
                input__attrs__class={'pf-v6-c-check__input': True},
                label__attrs__class={'pf-v6-c-check__label': True, 'pf-v6-c-form__label': False},
                help__tag='span',
                help__attrs__class={
                    'pf-v6-c-check__description': True,
                    'pf-v6-c-helper-text__item': False,
                    'pf-v6-c-helper-text__item-text': False,
                },
            ),
            choice__input__template='iommi/form/patternfly6/choice.html',
            # select2 sizes itself from the width in the style attribute
            multi_choice__input__attrs__style__width='100%',
            choice_queryset__input__attrs__style__width='100%',
            choice_searchable__input__attrs__style__width='100%',
            radio=dict(
                input__template='iommi/form/patternfly6/radio.html',
                input__attrs__class={'pf-v6-c-radio__input': True},
            ),
            checkboxes=dict(
                input__template='iommi/form/patternfly6/checkboxes.html',
                input__attrs__style__width=None,
                input__attrs__class={'pf-v6-c-check__input': True},
            ),
        ),
        attrs__class={'pf-v6-c-form__group': True},
        label__attrs__class={'pf-v6-c-form__label': True},
        help__attrs__class={
            'helptext': False,
            'pf-v6-c-helper-text__item': True,
            'pf-v6-c-helper-text__item-text': True,
        },
        errors__template='iommi/form/patternfly6/errors.html',
        errors__attrs__class={'pf-v6-c-helper-text': True},
    ),
    FieldGroup=dict(
        tag='div',
        attrs__class={
            'pf-v6-l-flex': True,
            'pf-m-wrap': True,
            'pf-m-gap-md': True,
        },
    ),
    Actions=dict(
        tag='div',
        attrs__class={'pf-v6-c-form__actions': True, 'links': False},
    ),
    Action=dict(
        shortcuts=dict(
            button__attrs__class={
                'pf-v6-c-button': True,
                'pf-m-secondary': True,
            },
            primary__attrs__class={
                'pf-m-primary': True,
                'pf-m-secondary': False,
            },
            delete__attrs__class={
                'pf-m-danger': True,
                'pf-m-secondary': False,
            },
        ),
    ),
    Table=dict(
        attrs__class={'pf-v6-c-table': True, 'pf-m-compact': True},
        header__template='iommi/table/patternfly6/table_header_rows.html',
        tbody__attrs__class={'pf-v6-c-table__tbody': True},
        row__attrs__class={'pf-v6-c-table__tr': True},
        cell__attrs__class={'pf-v6-c-table__td': True},
    ),
    Column=dict(
        header__attrs__class={
            'pf-v6-c-table__th': True,
            'pf-v6-c-table__sort': lambda header, **_: header.url is not None,
            'pf-m-selected': lambda column, **_: bool(column.is_sorting),
        },
        header__attrs={'aria-sort': lambda column, **_: column.sort_direction if column.is_sorting else None},
        header__template='iommi/table/patternfly6/header.html',
        shortcuts=dict(
            select=dict(
                header__template='iommi/table/patternfly6/select_column_header.html',
                header__attrs__class={'pf-v6-c-table__check': True},
                cell__attrs__class={'pf-v6-c-table__check': True},
            ),
            number=dict(
                cell__attrs__class={'pf-v6-u-text-align-end': True},
                header__attrs__class={'pf-v6-u-text-align-end': True},
            ),
            boolean=dict(
                cell__attrs__class={'pf-v6-u-text-align-center': True},
                header__attrs__class={'pf-v6-u-text-align-center': True},
            ),
        ),
    ),
    Query=dict(
        form__iommi_style='horizontal',
        form_container=dict(
            tag='span',
            attrs__class={
                'pf-v6-l-flex': True,
                'pf-m-wrap': True,
                'pf-m-gap-md': True,
                'pf-m-align-items-flex-end': True,
            },
        ),
        advanced__template='iommi/query/patternfly6/advanced.html',
    ),
    Menu=dict(
        template='iommi/menu/patternfly6/menu.html',
        tag='nav',
        attrs__class={'pf-v6-c-nav': True, 'pf-m-horizontal': True},
        items_container__attrs__class={'pf-v6-c-nav__list': True},
        items_container__tag='ul',
    ),
    MenuItem=dict(
        tag='li',
        a__attrs__class={'pf-v6-c-nav__link': True},
        attrs__class={'pf-v6-c-nav__item': True},
        active_class='pf-m-current',
    ),
    DebugMenu=dict(
        # Don't wrap the debug menu in the masthead of the Menu template
        template=None,
        attrs__style={
            'background': 'var(--pf-t--global--background--color--primary--default)',
            'border-color': 'var(--pf-t--global--border--color--default)',
        },
    ),
    Paginator=dict(
        template='iommi/table/patternfly6/paginator.html',
        tag='div',
        attrs__class={'pf-v6-c-pagination': True, 'pf-m-bottom': True},
        link__attrs__class={'pf-v6-c-button': True, 'pf-m-plain': True},
    ),
    Calendar=dict(
        attrs__class={'pf-v6-c-table': True, 'pf-m-compact': True},
    ),
)

patternfly6 = Style(
    patternfly6_base,
    patternfly6_icons,
    select2_enhanced_forms,
)
