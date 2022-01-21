from iommi import Style
from iommi.style_bootstrap import bootstrap

bootstrap_docs = Style(
    bootstrap,
    internal=True,
    Container=dict(
        attrs__class={
            'container': False,
            'mt-5': False,
            'pt-5': False,
        },
        attrs__style__padding='1rem',
    ),
)
