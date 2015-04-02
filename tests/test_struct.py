import pytest
from tri.tables import Struct


def test_struct():
    s = Struct(a=1, b=2)
    s.c = 3
    s['d'] = 4
    assert s.a == 1
    assert s.b == 2
    assert s['c'] == 3
    assert s['d'] == 4

    del s['d']
    del s.c
    with pytest.raises(KeyError):
        del s['d']

    with pytest.raises(AttributeError):
        del s.d

    assert type(s.copy()) == Struct

    assert repr(s) == unicode(s) == 'Struct(a=1, b=2)'
