from iommi.style import (
    Style,
)
from iommi.style_font_awesome_4 import font_awesome_4
from iommi.style_base import base

django_admin_base = Style(
    base,
    font_awesome_4,
    Container=dict(
        tag='div',
        attrs__class={
            'container': True,
        },
    ),
    base_template='iommi/base_django_admin.html',
    Table__attrs__id='changelist',
    Query__form__iommi_style='django_admin_horizontal',
)

django_admin = Style(
    django_admin_base,
    Field__attrs__class={'form-row': True},
    Form__attrs__class=dict(
        aligned=True,
    ),
    Form__attrs__id='content',
    Table__actions__attrs__class={'object-tools': True},
    Table__outer__tag='div',
    Table__outer__attrs__id='content',
    Table__bulk__attrs__id=None,
    Admin__parts__header__attrs__id='header',
)


django_admin_horizontal = Style(
    django_admin_base,
    Field__attrs__class={'compact-form-row': True},
)
