from iommi import html
from iommi.style import Style
from iommi.style_base import base

water = Style(
    base,
    assets__css=html.link(
        attrs=dict(
            rel='stylesheet',
            href='https://cdn.jsdelivr.net/gh/kognise/water.css@latest/dist/dark.min.css',
        ),
    ),
)
