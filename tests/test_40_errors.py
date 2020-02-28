from iommi.error import Errors


def test_errors_rendering():
    errors = Errors(parent=None, errors={'foo', 'bar'})
    assert errors
    assert errors.__html__() == '<ul><li>bar</li><li>foo</li></ul>'


def test_errors_empty_rendering():
    errors = Errors(parent=None, errors=set())
    assert not errors
    assert errors.__html__() == ''
