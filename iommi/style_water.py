from iommi.style import Style
from iommi.style_base import base
from iommi.asset import Asset

water = Style(
    base,
    root__assets__css=Asset.css(
        attrs=dict(
            href='https://cdn.jsdelivr.net/gh/kognise/water.css@latest/dist/dark.min.css',
        ),
    ),
)
