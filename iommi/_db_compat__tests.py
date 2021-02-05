import pytest
from tri_struct import merged

from iommi._db_compat import field_defaults_factory


@pytest.mark.django
def test_field_defaults_factory():
    from django.db import models

    base = dict(parse_empty_string_as_none=True, required=True, display_name=None)

    assert field_defaults_factory(models.CharField(null=False, blank=False)) == merged(
        base, dict(parse_empty_string_as_none=False)
    )
    assert field_defaults_factory(models.CharField(null=False, blank=True)) == merged(
        base, dict(parse_empty_string_as_none=False, required=False)
    )

    assert field_defaults_factory(models.CharField(null=True, blank=False)) == merged(base, dict(required=False))
    assert field_defaults_factory(models.CharField(null=True, blank=True)) == merged(base, dict(required=False))


@pytest.mark.django
def test_field_defaults_factory_boolean():
    from django.db import models

    django_null_default = not models.BooleanField().null

    base = dict(parse_empty_string_as_none=django_null_default, display_name=None)

    assert field_defaults_factory(models.BooleanField(null=False, blank=False)) == merged(
        base, dict(parse_empty_string_as_none=False)
    )
    assert field_defaults_factory(models.BooleanField(null=False, blank=True)) == merged(
        base, dict(parse_empty_string_as_none=False)
    )

    assert field_defaults_factory(models.BooleanField(null=True, blank=False)) == base
    assert field_defaults_factory(models.BooleanField(null=True, blank=True)) == base
