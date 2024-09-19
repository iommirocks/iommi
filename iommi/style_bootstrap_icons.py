from django.utils.translation import gettext

from iommi._web_compat import mark_safe
from iommi.fragment import html
from iommi.style import Style

bootstrap_icons = Style(
    root__assets__icons=html.link(
        attrs__rel="stylesheet",
        attrs__href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.1/font/bootstrap-icons.css",
    ),
    Column__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'bi': True},
            icon_prefix='bi-',
        ),
        edit__extra__icon='pencil-square',
        delete__extra__icon='trash',
        download__extra__icon='download',
        boolean__cell__format=lambda value, **_: mark_safe(
            f'<i class="bi bi-check-lg fs-3" title="{gettext("Yes")}"></i>'
        )
        if value
        else '',
        select=dict(
            extra__icon='bi bi-check2-square',
        ),
    ),
    Action__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'bi': True},
            icon_prefix='bi-',
        ),
    ),
)
