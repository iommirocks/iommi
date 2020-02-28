from iommi.error import Errors


def test_errors_rendering():
    errors = Errors(parent=None, errors={'foo', 'bar'})
    assert errors.__html__() == '<ul><li>bar</li><li>foo</li></ul>'
