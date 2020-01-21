import pytest
from tri_struct import merged

from iommi.form import Field, Form
from iommi._db_compat import field_defaults_factory
from iommi._web_compat import render_to_string, format_html, render_template, Template
from .compat import RequestFactory, SafeText


def test_render_to_string():
    assert render_to_string(
        template_name='iommi/form/non_editable.html',
        request=RequestFactory().get('/'),
        context=dict(
            field=dict(
                id=SafeText('<a b c><d><e>'),
                rendered_value=SafeText('<a b c><d><e>'),
            ),
        )
    ).strip() == '<span id="<a b c><d><e>"><a b c><d><e></span>'


def test_format_html():
    assert format_html('<{a}>{b}{c}', a='a', b=format_html('<b>'), c='<c>') == '<a><b>&lt;c&gt;'


def test_format_html2():
    assert render_template(RequestFactory().get('/'), Template('{{foo}}'), dict(foo=format_html('<a href="foo">foo</a>'))) == '<a href="foo">foo</a>'


def test_format_html3():
    assert render_template(RequestFactory().get('/'), Template('{{foo}}'), dict(foo=format_html('{}', format_html('<a href="foo">foo</a>')))) == '<a href="foo">foo</a>'


def test_format_html4():
    actual = render_template(
        RequestFactory().get('/'),
        Template('{{foo}}'),
        dict(
            foo=Form(fields=dict(foo=Field())),
        )
    )
    print(actual)
    assert '<input type="text" value="" name="foo" id="id_foo"' in actual


def test_format_html5():
    actual = Form(
        fields__foo=Field(),
    ).bind(
        request=RequestFactory().get('/'),
    ).render_part()
    print(actual)
    assert type(actual) == SafeText


# TODO: rendering a form should work, but right now there's render_with_style.. which we should fix
def test_format_html6():
    form = Form(fields__foo=Field()).bind(request=RequestFactory().get('/'))
    actual = form.fields.foo.render_part()
    print(actual)
    assert type(actual) == SafeText


def test_render_template():
    actual = render_template(RequestFactory().get('/'), Template('{{foo}}'), dict(foo=1))
    print(actual)
    assert type(actual) == SafeText


@pytest.mark.django
def test_field_defaults_factory():
    from django.db import models
    base = dict(parse_empty_string_as_none=True, required=True, display_name=None)

    assert field_defaults_factory(models.CharField(null=False, blank=False)) == merged(base, dict(parse_empty_string_as_none=False))
    assert field_defaults_factory(models.CharField(null=False, blank=True)) == merged(base, dict(parse_empty_string_as_none=False, required=False))

    assert field_defaults_factory(models.CharField(null=True, blank=False)) == merged(base, dict(required=False))
    assert field_defaults_factory(models.CharField(null=True, blank=True)) == merged(base, dict(required=False))


@pytest.mark.django
def test_field_defaults_factory_boolean():
    from django.db import models

    django_null_default = not models.BooleanField().null

    base = dict(parse_empty_string_as_none=django_null_default, display_name=None)

    assert field_defaults_factory(models.BooleanField(null=False, blank=False)) == merged(base, dict(parse_empty_string_as_none=False))
    assert field_defaults_factory(models.BooleanField(null=False, blank=True)) == merged(base, dict(parse_empty_string_as_none=False))

    assert field_defaults_factory(models.BooleanField(null=True, blank=False)) == base
    assert field_defaults_factory(models.BooleanField(null=True, blank=True)) == base
