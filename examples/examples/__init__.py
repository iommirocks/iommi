from functools import partial

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


def example_links(examples):
    children = {}

    for i, example in enumerate(examples):
        n = i + 1
        children[f'example_{n}'] = html.p(
            Action(
                display_name=f'Example {n}: {example.description}',
                attrs__href=f'example_{n}',
            ),
            html.br(),
        )

    return Fragment(children=children)

