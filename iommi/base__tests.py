import pytest

from iommi import MISSING
from iommi.base import (
    UnknownMissingValueException,
    build_as_view_wrapper,
    capitalize,
    model_and_rows,
)
from tests.models import Foo


def test_missing():
    assert str(MISSING) == 'MISSING'
    assert repr(MISSING) == 'MISSING'

    with pytest.raises(UnknownMissingValueException) as e:
        if MISSING:
            pass  # pragma: no cover

    assert str(e.value) == 'MISSING is neither True nor False, is is unknown'


def test_build_as_view_wrapper():
    class Foo:
        """
        docs
        """
        pass
    vw = build_as_view_wrapper(Foo())
    assert vw.__doc__ == Foo.__doc__
    assert vw.__name__ == 'Foo.as_view'


def test_capitalize():
    assert capitalize('xFooBarBaz Foo oOOOo') == 'XFooBarBaz Foo oOOOo'


@pytest.mark.django_db
def test_model_and_rows():
    # Model only defaults to all()
    model, rows = model_and_rows(model=Foo, rows=None)
    assert model is Foo and str(rows.query) == str(Foo.objects.all().query)

    # rows is preserved and model is returned
    orig_rows = Foo.objects.filter(foo=2)
    model, rows = model_and_rows(model=None, rows=orig_rows)
    assert model is Foo and rows is orig_rows
