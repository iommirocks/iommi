from iommi.asset import Asset
from iommi.style import Style
from iommi.style_base import base


patternfly6 = Style(
    base,
    root__assets=dict(
        css=Asset.css(
            # TODO: Final version etc…
            attrs__href="https://cdn.jsdelivr.net/npm/@patternfly/patternfly@6.0.0-prerelease.15/patternfly.min.css",
        ),
        css_addons=Asset.css(
            attrs__href='https://cdn.jsdelivr.net/npm/@patternfly/patternfly@6.0.0-prerelease.13/patternfly-addons.css',
        )
    ),
    sub_styles__horizontal=dict(
        # TODO, used by the query for nice display
    ),
    Header__attrs__class={
        "pf-v6-c-title": lambda fragment, **_: fragment.tag[0] == "h"
        and fragment.tag[1] in "123456",
        "pf-m-h1": lambda fragment, **_: fragment.tag == "h1",
        "pf-m-h2": lambda fragment, **_: fragment.tag == "h2",
        "pf-m-h3": lambda fragment, **_: fragment.tag == "h3",
        "pf-m-h4": lambda fragment, **_: fragment.tag == "h4",
        "pf-m-h5": lambda fragment, **_: fragment.tag == "h5",
        "pf-m-h6": lambda fragment, **_: fragment.tag == "h6",
    },
    Form=dict(
        attrs__class={
            "pf-v6-c-form": True,
            "pf-m-horizontal": True,
        }
    ),
    Field=dict(
        shortcuts=dict(
            attrs__class={'pf-v6-c-form-control': False},
            boolean__input__attrs__class={'pf-v6-c-check__input': True},
        ),
        template="iommi/form/patternfly6/field.html",
        attrs__class={
            "pf-v6-c-form__group": True,
        },
        input__attrs__class={},
        help__attrs__class={},
        label__attrs__class={"pf-v6-c-form__label": True},
    ),
    Table=dict(
        attrs__class={"pf-v6-c-table": True},
        header__template="iommi/table/patternfly6/table_header_rows.html",
        tbody__attrs__class={"pf-v6-c-table__tbody": True},
        row__attrs__class={"pf-v6-c-table__tr": True},
        cell__attrs__class={"pf-v6-c-table__td": True},
    ),
    Column=dict(
        header__attrs__class={
            "pf-v6-c-table__th": True,
            "pf-v6-c-table__sort": lambda column, **_: column.sortable,
        },
        header__template="iommi/table/patternfly6/header.html",
        shortcuts=dict(
            select=dict(
                header__template="iommi/table/patternfly6/select_column_header.html",
                header__attrs__class={"pf-v6-c-table__check": True},
                cell__attrs__class={"pf-v6-c-table__check": True},
            )
        ),
    ),
    Menu=dict(
        template="iommi/menu/patternfly6/menu.html",
        attrs__class={"pf-v6-c-nav": True, "pf-m-horizontal": True},
        items_container__attrs__class={"pf-v6-c-nav__list": True},
        items_container__tag="ul",
    ),
    MenuItem=dict(
        tag="li",
        a__attrs__class={"pf-v6-c-nav__link": True},
        attrs__class={"pf-v6-c-nav__item": True},
    ),
    DebugMenu=dict(
        template=None,
    ),
    Paginator=dict(
        template="iommi/table/patternfly6/paginator.html",
    ),
    Action=dict(
        shortcuts=dict(
            button__attrs__class={
                "pf-v6-c-button": True,
                "pf-m-secondary": True,
            },
            primary__attrs__class={
                "pf-m-primary": True,
                "pf-m-secondary": False,
            },
            delete__attrs__class={
                "pf-m-warning": True,
                "pf-m-secondary": False,
            },
        ),
    ),
    Container=dict(
        tag='div',
        attrs__class={'pf-v6-u-p-lg': True},
    )
)
