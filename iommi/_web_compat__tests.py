from django.template import RequestContext

from iommi._web_compat import (
    format_html,
    render_template,
    Template,
)
from iommi.form import (
    Field,
    Form,
)
from tests.compat import SafeText
from tests.helpers import req


def test_simple_render_to_string():
    t = Template('{{ field }}')
    assert t.render(context=RequestContext(req('get'), dict(field='foo'))).strip() == 'foo'


def test_render_to_string():
    t = Template('<span id="{{ field.input.attrs.id }}">{{ field.rendered_value }}</span>')
    assert (
        t.render(
            context=RequestContext(
                req('get'),
                dict(
                    field=dict(
                        input=dict(
                            attrs=dict(
                                id=SafeText('<a b c><d><e>'),
                            ),
                        ),
                        rendered_value=SafeText('<a b c><d><e>'),
                    ),
                ),
            )
        ).strip()
        == '<span id="<a b c><d><e>"><a b c><d><e></span>'
    )


def test_format_html():
    assert format_html('<{a}>{b}{c}', a='a', b=format_html('<b>'), c='<c>') == '<a><b>&lt;c&gt;'


def test_format_html2():
    assert (
        render_template(req('get'), Template('{{foo}}'), dict(foo=format_html('<a href="foo">foo</a>')))
        == '<a href="foo">foo</a>'
    )


def test_format_html3():
    assert (
        render_template(
            req('get'), Template('{{foo}}'), dict(foo=format_html('{}', format_html('<a href="foo">foo</a>')))
        )
        == '<a href="foo">foo</a>'
    )


def test_format_html4():
    form = Form(fields=dict(foo=Field()))
    form = form.bind(request=req('get'))
    actual = render_template(
        req('get'),
        Template('{{form}}'),
        dict(
            form=form,
        ),
    )
    assert '<input id="id_foo" name="foo" type="text" value="">' in actual


def test_format_html5():
    actual = (
        Form(
            fields__foo=Field(),
        )
        .bind(
            request=req('get'),
        )
        .__html__()
    )
    assert '<form' in actual
    assert '<input' in actual
    assert type(actual) == SafeText


def test_format_html6():
    form = Form(fields__foo=Field()).bind(request=req('get'))
    actual = form.fields.foo.__html__()
    assert '<input' in actual
    assert type(actual) == SafeText


def test_format_html7():
    form = Form(fields__foo=Field()).bind(request=req('get'))
    actual = str(form.fields.foo)
    assert '<input' in actual
    assert type(actual) == SafeText


def test_render_template():
    actual = render_template(req('get'), Template('{{foo}}'), dict(foo=1))
    assert type(actual) == SafeText
