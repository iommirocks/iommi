from iommi import (
    Asset,
    Style,
)
from iommi.style_bootstrap5 import bootstrap5

bootstrap_docs = Style(
    bootstrap5,
    root__assets__doc_style=Asset.css(attrs__href='https://docs.iommi.rocks/en/latest/_static/iframe_custom.css'),
    root__assets__iommi_js=Asset.js(attrs=dict(src='https://docs.iommi.rocks/en/latest/_static/js/iommi.js')),
    root__assets__iommi_css=Asset.css(attrs__href='https://docs.iommi.rocks/en/latest/_static/css/iommi.css'),
    root__assets__iommi_scroll_js=Asset.js(attrs__src='https://docs.iommi.rocks/en/latest/_static/js/iommi-scroll.js'),
    root__assets__iommi_menu_css=Asset.css(attrs__href='https://docs.iommi.rocks/en/latest/_static/css/iommi_main_menu.css'),
    internal=True,
    Container=dict(
        attrs__class={
            'container': False,
            'mt-5': False,
        },
        attrs__style__padding='1rem',
    ),
    Admin__parts__table__h_tag__attrs__style={'margin-top': '3rem'},
)
