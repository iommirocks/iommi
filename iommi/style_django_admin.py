from iommi import html
from iommi.style import (
    Style,
)
from iommi.style_base import base
from iommi.style_font_awesome_4 import font_awesome_4

django_admin = Style(
    base,
    font_awesome_4,
    sub_styles__horizontal=dict(
        Field__attrs__class={'compact-form-row': True},
    ),
    root__assets=dict(
        css_base=html.link(attrs=dict(rel="stylesheet", type="text/css", href="/static/admin/css/base.css")),
        css_login=html.link(attrs=dict(rel="stylesheet", type="text/css", href="/static/admin/css/login.css")),
        css_forms=html.link(attrs=dict(rel="stylesheet", type="text/css", href="/static/admin/css/forms.css")),
        meta=html.meta(
            attrs=dict(
                name="viewport", content="user-scalable=no, width=device-width, initial-scale=1.0, maximum-scale=1.0"
            )
        ),
        css_responsive=html.link(
            attrs=dict(rel="stylesheet", type="text/css", href="/static/admin/css/responsive.css")
        ),
        css_extra=html.style(
            """
            .compact-form-row {
                display: inline-block;
            }

            .compact-form-row .helptext {
                display: none;
            }
        """
        ),
    ),
    Container=dict(
        tag='div',
        attrs__class={
            'container': True,
        },
    ),
    Table__attrs__id='changelist',
    Query__form__iommi_style='django_admin_horizontal',
    Field__attrs__class={'form-row': True},
    Form__attrs__class=dict(
        aligned=True,
    ),
    Form__attrs__id='content',
    # Table__actions__attrs__class={'object-tools': True},
    Table__outer__tag='div',
    Table__outer__attrs__id='content',
    Table__bulk__attrs__id=None,
    # Admin__parts__menu__attrs__id='header',
    Menu__tag='nav',
)
