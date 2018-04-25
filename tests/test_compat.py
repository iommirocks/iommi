import pytest

from tri.form.compat import render_to_string, RequestFactory, format_html


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
