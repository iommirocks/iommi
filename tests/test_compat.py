import pytest
from tri.struct import merged

from tri.form.compat import render_to_string, RequestFactory, format_html, field_defaults_factory


@pytest.mark.flask
def test_render_to_string():
    from jinja2 import Markup

    assert render_to_string(
        template_name='tri_form/non_editable.html',
        request=RequestFactory().get('/'),
        context=dict(
            field=dict(
                id=Markup('<a b c><d><e>'),
                rendered_value=Markup('<a b c><d><e>'),
            ),
        )
    ) == '<span id="<a b c><d><e>"><a b c><d><e></span>'


def test_format_html():
    assert format_html('<{a}>{b}{c}', a='a', b=format_html('<b>'), c='<c>') == '<a><b>&lt;c&gt;'


@pytest.mark.django
def test_field_defaults_factory():
    from django.db import models
    base = dict(parse_empty_string_as_none=True, required=True, display_name=None)

    assert field_defaults_factory(models.CharField(verbose_name='foo')) == merged(base, dict(display_name='Foo'))

    assert field_defaults_factory(models.CharField()) == base

    assert field_defaults_factory(models.CharField(null=False, blank=False)) == base
    assert field_defaults_factory(models.CharField(null=False, blank=True)) == merged(base, dict(parse_empty_string_as_none=False, required=False))

    assert field_defaults_factory(models.CharField(null=True, blank=False)) == merged(base, dict(required=False))
    assert field_defaults_factory(models.CharField(null=True, blank=True)) == merged(base, dict(parse_empty_string_as_none=False, required=False))


@pytest.mark.django
def test_field_defaults_factory_boolean():
    from django.db import models
    base = dict(parse_empty_string_as_none=True, display_name=None)

    assert field_defaults_factory(models.BooleanField(verbose_name='foo')) == merged(base, dict(display_name='Foo'))

    assert field_defaults_factory(models.BooleanField()) == base

    assert field_defaults_factory(models.BooleanField(null=False, blank=False)) == base
    assert field_defaults_factory(models.BooleanField(null=False, blank=True)) == merged(base, dict(parse_empty_string_as_none=False))

    assert field_defaults_factory(models.BooleanField(null=True, blank=False)) == base
    assert field_defaults_factory(models.BooleanField(null=True, blank=True)) == merged(base, dict(parse_empty_string_as_none=False))
