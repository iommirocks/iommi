import pytest
from tri.table.templatetags.tri_table import paginator
from tri.struct import merged

expected_base = dict(extra='', page_numbers=[1, 2, 3], show_first=False, show_last=True)


@pytest.fixture
def context():
    return dict(page=1, pages=4, results_per_page=3, hits=11, next=1, previous=None, has_next=True, has_previous=False, show_hits=True, hit_label='hits')


def test_paginator_basic(context):
    actual = paginator(context=context, adjacent_pages=1)
    expected = merged(context, **expected_base)
    assert actual == expected
