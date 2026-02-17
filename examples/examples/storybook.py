from django.conf import settings

import iommi.style
from iommi import (
    Page,
    html,
)
from iommi.live_edit import style_showcase

from examples.views import StyleSelector


def storybook(request):
    current_style = getattr(settings, 'IOMMI_DEFAULT_STYLE', iommi.style.DEFAULT_STYLE)

    return Page(
        parts=dict(
            header=html.h1(f'Storybook: {current_style}'),
            style_selector=StyleSelector(),
            showcase=style_showcase(request, style=current_style),
        ),
    )
