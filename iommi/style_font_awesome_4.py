from django.utils.translation import gettext_lazy

from iommi._web_compat import (
    format_html,
    mark_safe,
)
from iommi.fragment import html
from iommi.style import Style


def font_awesome_4_icon_formatter(icon, **_):
    if icon == 'external':
        icon = 'external-link'
    return format_html('<i class="fa fa-{}"></i> ', icon)


font_awesome_4 = Style(
    root__assets__icons=html.link(
        attrs__rel="stylesheet",
        attrs__href="https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css",
    ),
    icon_formatter=font_awesome_4_icon_formatter,
    Column__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'fa': True, 'fa-lg': True},
            icon_prefix='fa-',
        ),
        edit__extra__icon='pencil-square-o',
        delete__extra__icon='trash-o',
        download__extra__icon='download',
        boolean__cell__format=lambda value, **_: mark_safe(f'<i class="fa fa-check" title="{gettext_lazy("Yes")}"></i>')
        if value
        else '',
    ),
    Action__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'fa': True},
            icon_prefix='fa-',
        ),
    ),
)
