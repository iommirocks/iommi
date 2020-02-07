import pytest
from iommi.admin import list_model
from .models import AdminUnique
from .helpers import req


@pytest.mark.django_db
def test_bulk_edit_for_non_unique():
    p = list_model(model=AdminUnique)
    p.bind(request=req('get'))
    assert [x.name for x in p.parts.table.columns.values() if x.bulk.include] == ['foo']
