import pytest

from iommi.declarative.util import strip_prefix


@pytest.mark.parametrize(
    'input, expected',
    [
        ('', ''),
        ('prefix', ''),
        ('prefixsuffix', 'suffix'),
        ('something prefix', 'something prefix'),
    ]
)
def test_strip_prefix(input, expected):
    assert strip_prefix(input, prefix='prefix') == expected
