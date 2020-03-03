import pytest
from tri_struct import Struct

from iommi.admin import Admin
from .helpers import req


@pytest.mark.django_db
def test_bulk_edit_for_non_unique():
    request = req('get')
    request.user = Struct(is_staff=True)
    p = Admin.list(request=request, app_name='tests', model_name='adminunique')
    p = p.bind(request=request)
    assert [x._name for x in p.parts.list_tests_adminunique.columns.values() if x.bulk.include] == ['foo']
