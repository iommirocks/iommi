from iommi.style import (
    Style,
)
from iommi.style_font_awesome_4 import font_awesome_4
from iommi.style_base import base

django_admin_base = Style(
    base,
    font_awesome_4,
    Table__attrs__id='changelist',
    Query__form__iommi_style='django_admin_horizontal',
)

django_admin = Style(
    django_admin_base,
    Field__attrs__class={'form-row': True},
    Form__attrs__class=dict(
        aligned=True,
    ),
    Table__actions__attrs__class={'object-tools': True},
    Admin__parts__header__attrs__id='header',
)


django_admin_horizontal = Style(
    django_admin_base,
    Field__attrs__class={'compact-form-row': True},
)
