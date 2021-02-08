from django.urls import path
from django.utils.translation import gettext

from examples import (
    example_adding_decorator,
    example_links,
)
from examples.views import ExamplesPage
from iommi import (
    html,
    Menu,
    MenuItem,
    Page,
)

examples = []
example = example_adding_decorator(examples)


@example(gettext("A sample menu"))
def menu_test(request):
    class FooPage(Page):
        menu = Menu(
            sub_menu=dict(
                root=MenuItem(url='/'),
                menu_test=MenuItem(),
                f_a_1=MenuItem(display_name='Example 1: echo submitted data', url="form_example_1/"),
                f_a_2=MenuItem(display_name='Example 2: create a Foo', url="form_example_2/"),
                f_a_3=MenuItem(display_name='Example 3: edit a Foo', url="form_example_3/"),
                f_a_4=MenuItem(display_name='Example 4: custom buttons', url="form_example_4/"),
                f_a_5=MenuItem(display_name='Example 5: automatic AJAX endpoint', url="form_example_5/"),
                f_a_k=MenuItem(display_name='Kitchen sink', url="form_kitchen/"),
            ),
        )

    return FooPage()


class IndexPage(ExamplesPage):
    header = html.h1('Form examples')
    description = html.p('Some examples of iommi Forms')

    examples = example_links(examples)


urlpatterns = [
    path('', IndexPage().as_view()),
    path('example_1/', menu_test, name='menu_test'),
]
