from tri_declarative import (
    dispatch,
    EMPTY,
    Namespace,
)

from iommi._web_compat import format_html
from iommi.attrs import render_attrs
from iommi.style import Style
from iommi.fragment import html


@dispatch(
    attrs=EMPTY,
)
def icon_formatter(name, attrs, **_):
    attrs.setdefault('class', {}).setdefault('fa', True)
    return format_html('<i{}></i>', render_attrs(Namespace(attrs, **{'class__fa-'+name: True})))


font_awesome_4 = Style(
    icon_formatter=icon_formatter,
    root__assets__icons=html.link(
        attrs__rel="stylesheet",
        attrs__href="https://maxcdn.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.min.css",
    ),
    Column__shortcuts=dict(
        edit__extra__icon='pencil-square-o',
        delete__extra__icon='trash-o',
        download__extra__icon='download',
        icon__extra__icon_attrs__class={'fa-lg': True},
    ),
)
