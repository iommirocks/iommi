from iommi import html
from iommi.error import Errors


def test_errors_rendering():
    errors = Errors(parent=None, errors={'foo', 'bar'})
    assert errors
    assert errors.__html__() == '<ul><li>bar</li><li>foo</li></ul>'


def test_errors_empty_rendering():
    errors = Errors(parent=None, errors=set())
    assert not errors
    assert errors.__html__() == ''


def test_error_render_in_debug(settings):
    settings.DEBUG = True
    parent = html.p('foo').bind()
    errors = Errors(parent=parent, errors={'foo', 'bar'})
    assert errors
    assert errors.__html__() == (
        '<ul data-iommi-path="error" data-iommi-type="Fragment">'
        '<li data-iommi-path="error__children__error_0" data-iommi-type="Fragment">bar</li>'
        '<li data-iommi-path="error__children__error_1" data-iommi-type="Fragment">foo</li>'
        '</ul>'
    )
