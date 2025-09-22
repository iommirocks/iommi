import pytest

from tests.helpers import extract_form_data


@pytest.mark.parametrize(
    'content, expected',
    [
        ('<input name="foo" value="bar">', dict(foo='bar')),
        ('<button name="foo">', dict(foo='')),
        ('<select name="foo"></select>', dict(foo='')),
        ('<select name="foo"><option value="bar" selected="selected"></select>', dict(foo='bar')),
        ('<textarea name="foo">bar</textarea>', dict(foo='bar')),
        ('<textarea name="foo">bar\nbaz</textarea>', dict(foo='bar\nbaz')),
    ]
)
def test_extract_form_data(content, expected):
    assert extract_form_data(content) == expected
