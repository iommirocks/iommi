"""
Property: style config that goes nowhere must raise.

We generate styles that put garbage config under a shortcut that a
generated member actually uses, and check that rendering fails with an
error mentioning the garbage. The same setup with the plain style must
render fine, so any exception is attributable to the garbage.

Config under excluded filters and bulk fields of a Table is only validated
in DEBUG, so this runs with DEBUG on.
"""

import pytest
from django.test import override_settings
from hypothesis import (
    HealthCheck,
    given,
    settings,
)
from hypothesis import (
    strategies as st,
)

from iommi import (
    Form,
    Query,
    Table,
)
from iommi.style import (
    Style,
    get_global_style,
)
from tests.helpers import req
from tests.models import (
    BooleanFromModelTestModel,
    ChoicesModel,
    CreateOrEditObjectTest,
    IntChoicesModel,
    TBar,
    TBaz,
    TFoo,
)

MODELS = [
    BooleanFromModelTestModel,
    ChoicesModel,
    CreateOrEditObjectTest,
    IntChoicesModel,
    TBar,
    TBaz,
    TFoo,
]

# container, members namespace, style class name of the members, sub namespaces of the members that become objects
CONTAINERS = [
    (Table, 'columns', 'Column', ['filter', 'bulk']),
    (Form, 'fields', 'Field', ['input', 'label']),
    (Query, 'filters', 'Filter', ['field']),
]

GARBAGE = 'garbage_xyz'


def render(container, model, **kwargs):
    container(auto__model=model, **kwargs).bind(request=req('get')).__html__()


@st.composite
def dead_config(draw):
    container, members_name, class_name, sub_names = draw(st.sampled_from(CONTAINERS))
    model = draw(st.sampled_from(MODELS))

    members = getattr(container(auto__model=model).bind(request=req('get')), members_name)
    member_name = draw(st.sampled_from(sorted(members.keys())))
    shortcut_name = draw(st.sampled_from(members[member_name].iommi_shortcut_stack))

    sub_name = draw(st.sampled_from([None, *sub_names]))
    kwargs = {}
    if sub_name is None:
        garbage = draw(
            st.sampled_from(
                [
                    {GARBAGE: 1},
                    {'call_target': {'attribute': GARBAGE}},
                ]
            )
        )
    else:
        if draw(st.booleans()):
            kwargs[f'{members_name}__{member_name}__{sub_name}__include'] = True
        garbage = {
            sub_name: draw(
                st.sampled_from(
                    [
                        {GARBAGE: 1},
                        {'call_target': {'attribute': GARBAGE}},
                    ]
                )
            )
        }

    return container, model, class_name, shortcut_name, garbage, kwargs


@pytest.mark.django_db
@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(dead_config())
def test_dead_style_config_raises(config):
    container, model, class_name, shortcut_name, garbage, kwargs = config

    render(container, model, **kwargs)

    style = Style(get_global_style('test'), **{class_name: dict(shortcuts={shortcut_name: garbage})})
    # Some of the validation is only done in DEBUG
    with override_settings(DEBUG=True), pytest.raises(Exception) as e:
        render(container, model, iommi_style=style, **kwargs)
    # The error must point at the garbage: either its name, or the key it was put under
    assert GARBAGE in str(e.value) or 'call_target' in str(e.value)
