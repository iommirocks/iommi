import pytest

from iommi import MISSING
from iommi.base import (
    UnknownMissingValueException,
    build_as_view_wrapper,
)


def test_missing():
    assert str(MISSING) == 'MISSING'
    assert repr(MISSING) == 'MISSING'

    with pytest.raises(UnknownMissingValueException) as e:
        if MISSING:
            pass

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
