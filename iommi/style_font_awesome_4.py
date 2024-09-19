from django.utils.translation import gettext

from iommi._web_compat import mark_safe
from iommi.fragment import html
from iommi.style import Style

font_awesome_4 = Style(
    root__assets__icons=html.link(
        attrs__rel="stylesheet",
        attrs__href="https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css",
    ),
    Column__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'fa': True, 'fa-lg': True},
            icon_prefix='fa-',
        ),
        edit__extra__icon='pencil-square-o',
        delete__extra__icon='trash-o',
        download__extra__icon='download',
        boolean__cell__format=lambda value, **_: mark_safe(f'<i class="fa fa-check" title="{gettext("Yes")}"></i>')
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
