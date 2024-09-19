from django.utils.safestring import mark_safe
from django.utils.translation import gettext

from iommi import (
    Style,
    html,
)

font_awesome_6 = Style(
    root__assets__icons=html.link(
        attrs__rel="stylesheet",
        attrs__href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.2/css/all.min.css",
    ),
    Column__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'fa': True, 'fa-lg': True},
            icon_prefix='fa-',
        ),
        edit__extra__icon='pencil-square',
        delete__extra__icon='trash',
        download__extra__icon='download',
        boolean__cell__format=lambda value, **_: (
            mark_safe(f'<i class="fa fa-check" title="{gettext("Yes")}"></i>') if value else ''
        ),
        select=dict(
            extra__icon='fa-regular fa-square-check',
        ),
    ),
    Action__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'fa': True},
            icon_prefix='fa-',
        ),
    ),
)
