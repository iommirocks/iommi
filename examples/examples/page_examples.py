from django.urls import path
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext
from django.views.decorators.csrf import csrf_exempt

from examples import (
    example_adding_decorator,
    example_links,
)
from examples.models import (
    TBar,
    TFoo,
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


@example(gettext('Standard example'))
class HelloWorldPage(Page):
    h1 = html.h1('Hello world!')
    p = html.p('This is an iommi page!')


@example(gettext('View with some calculation to do before making the page'))
def page_view_example_2(request):
    math_result = 1 + 1

    class MathPage(HelloWorldPage):
        result = html.pre(format_html("Math result: 1+1={}", math_result))

    return MathPage()


@example(gettext('Further specializing an already defined page'))
def page_view_example_3(request):
    math_result = 1 + 1

    return HelloWorldPage(
        parts__result=html.pre(format_html("Math result: 1+1={}", math_result)),
    )


@example(gettext('Busy page with different components'))
def page_view_example_4(request):
    class BusyPage(Page):
        tfoo = Table(auto__model=TFoo, page_size=5, columns__name__filter=dict(include=True, field__include=True))
        tbar = Table(auto__model=TBar, page_size=5, columns__b__filter=dict(include=True, field__include=True))
        create_tbar = Form.create(auto__model=TBar)

    return BusyPage()


class IndexPage(ExamplesPage):
    header = html.h1('Page examples')
    description = html.p('Some examples of iommi Page')

    class Meta:
        parts = example_links(examples)


@csrf_exempt
def page_live(request):
    return Page(
        parts__foo='Test',
        parts__circle=mark_safe('<svg><circle cx=50 cy=50 r=40 stroke=green fill=yellow stroke-width=4></svg>'),
        parts__bar=Table(auto__model=TFoo, page_size=2)
    )


urlpatterns = [
    path('', IndexPage().as_view()),
    path('example_1/', HelloWorldPage().as_view()),
    path('example_2/', page_view_example_2),
    path('example_3/', page_view_example_3),
    path('example_4/', page_view_example_4),
    path('live/', page_live),
]
