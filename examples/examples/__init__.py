from functools import partial

from django.urls import reverse

from iommi import (
    Action,
    Fragment,
    html,
)


def add_example(examples, description):
    def decorator(f):
        f.description = description
        examples.append(f)
        return f

    return decorator


def example_adding_decorator(examples):
    return partial(add_example, examples)


def example_links(urlpatterns):
    children = {}

    for i, path in enumerate(urlpatterns):
        example_view = path.callback
        example_definition = example_view.__iommi_target
        n = i + 1
        children[f'example_{n}'] = html.p(
            Action(
                display_name=f'Example {n}: {example_definition.iommi_namepace["title"]}',
                attrs__href=lambda example=example_view, **_: reverse(example),
            ),
            html.br(),
        )

    return Fragment(children=children)
