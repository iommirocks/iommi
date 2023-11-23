from iommi import (
    Asset,
    Style,
)
from iommi.style_bootstrap import bootstrap

bootstrap_docs = Style(
    bootstrap,
    root__assets__doc_style=Asset.css(attrs__href='https://docs.iommi.rocks/en/latest/_static/iframe_custom.css'),
    root__assets__iommi_js=Asset.js(attrs=dict(src='https://docs.iommi.rocks//en/latest/_static/iommi.js')),
    internal=True,
    Container=dict(
        attrs__class={
            'container': False,
            'mt-5': False,
            'pt-5': False,
        },
        attrs__style__padding='1rem',
    ),
    Admin__parts__table__h_tag__attrs__style={'margin-top': '3rem'},
)
