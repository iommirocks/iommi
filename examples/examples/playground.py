from iommi import (
    Header,
    html,
)
from examples.iommi import (
    Field,
    Form,
    Page,
    Table,
)

from examples.models import Album


class PlaygroundPage(Page):
    header = Header('Playground')

    description = html.p(
        'This is a blank page for experimentation. '
        'Use the live edit toolbar (click the pencil icon in the bottom right) '
        'to modify this page in real time.'
    )

    sample_form = Form(
        title='Sample form',
        fields=dict(
            name=Field(),
            year=Field.integer(),
        ),
        actions__submit__post_handler=lambda **_: None,
    )

    sample_table = Table(
        title='Sample table',
        auto__model=Album,
        page_size=5,
        columns__name__filter__include=True,
    )
