from django.template import Template
from django.urls import path
from django.utils.translation import gettext

from examples import (
    example_adding_decorator,
    example_links,
)
from examples.models import (
    Album,
    Artist,
)
from examples.views import ExamplesPage
from iommi import (
    Form,
    html,
    Page,
    Table,
)

examples = []

example = example_adding_decorator(examples)


@example(gettext('Hello world'))
class HelloWorldPage(Page):
    h1 = html.h1('Hello world!')
    p = html.p('This is an iommi page!')


@example(gettext('Further specializing an already defined page'))
class HelloWorldNextLevelPage(HelloWorldPage):
    class Meta:
        extra_params = lambda **_: dict(
            math_result=1 + 1,
        )

    result = html.pre(Template("Math result: 1+1={{ params.math_result }}"))


@example(gettext('Combine with other iommi components'))
class BusyPage(Page):
    artists = Table(auto__model=Artist, page_size=5, columns__name__filter=dict(include=True, field__include=True))
    albums = Table(auto__model=Album, page_size=5, columns__artist__filter=dict(include=True, field__include=True))
    create_album = Form.create(auto__model=Album)


class IndexPage(ExamplesPage):
    header = html.h1('Page examples')
    description = html.p('Some examples of iommi Page')

    examples = example_links(examples)


urlpatterns = [
    path('', IndexPage().as_view()),
    path('example_1/', HelloWorldPage().as_view()),
    path('example_2/', HelloWorldNextLevelPage().as_view()),
    path('example_3/', BusyPage().as_view()),
]
