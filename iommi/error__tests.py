from tri_struct import Struct

from iommi import (
    Form,
    html,
)
from iommi._web_compat import Template
from iommi.error import Errors
from tests.helpers import req


def test_errors_rendering():
    form = Form(errors__attrs__foo='foo').bind(request=req('get'))
    form.add_error('foo')
    form.add_error('bar')
    assert form.errors
    assert form.errors.__html__() == '<ul foo="foo"><li>bar</li><li>foo</li></ul>'


def test_errors_empty_rendering():
    parent = Struct(
        _errors=set(),
        _is_bound=True,
    )
    errors = Errors(parent=parent)
    assert not errors
    assert errors.__html__() == ''


def test_error_render_in_debug(settings):
    settings.DEBUG = True
    parent = html.p('foo').bind()
    parent._errors = {'foo', 'bar'}
    errors = Errors(parent=parent)
    assert errors
    assert errors.__html__() == (
        '<ul data-iommi-path="error" data-iommi-type="Errors">'
        '<li data-iommi-path="error__children__error_0" data-iommi-type="Fragment">bar</li>'
        '<li data-iommi-path="error__children__error_1" data-iommi-type="Fragment">foo</li>'
        '</ul>'
    )


def test_errors_rendering_template():
    form = Form(errors__template=Template('foo')).bind(request=req('get'))
    form.add_error('foo')
    form.add_error('bar')
    assert form.errors
    assert form.errors.__html__() == 'foo'
