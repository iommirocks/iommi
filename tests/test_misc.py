import pytest

from tri_declarative import (
    assert_kwargs_empty,
    full_function_name,
    setattr_path,
)


def test_assert_kwargs_empty():
    assert_kwargs_empty({})

    with pytest.raises(TypeError) as e:
        assert_kwargs_empty(dict(foo=1, bar=2, baz=3))

    assert str(e.value) == "test_assert_kwargs_empty() got unexpected keyword arguments 'bar', 'baz', 'foo'"


def test_full_function_name():
    assert full_function_name(setattr_path) == 'tri_declarative.namespace.setattr_path'
