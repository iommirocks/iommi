import pytest

from iommi.admin import Admin
from .helpers import req


@pytest.mark.django_db
def test_bulk_edit_for_non_unique():
    p = Admin.list(request=None, app_name='tests', model_name='adminunique')
    p = p.bind(request=req('get'))
    assert [x._name for x in p.parts.table.children.text.columns.values() if x.bulk.include] == ['foo']
