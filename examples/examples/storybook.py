from django.conf import settings

import iommi.style
from iommi import (
    Action,
    Page,
    html,
)
from iommi.base import items
from iommi.live_edit import style_showcase


def storybook(request):
    selected_style = request.GET.get('style')

    style_links = {
        name: Action(
            display_name=name,
            attrs__href=f'?style={name}',
        )
        for name, style in items(iommi.style._styles)
        if not style.internal
    }

    if selected_style:
        return Page(
            parts=dict(
                header=html.h1(f'Storybook: {selected_style}'),
                back=html.p(Action(display_name='Back to style list', attrs__href='?')),
                showcase=style_showcase(request, style=selected_style),
            ),
        )

    return Page(
        parts=dict(
            header=html.h1('Storybook'),
            description=html.p('Select a style to preview:'),
            styles=html.div(
                children=style_links,
            ),
        ),
    )
