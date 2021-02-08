import pytest
from django.template import RequestContext
from django.utils.safestring import (
    mark_safe,
    SafeText,
)
from tri_struct import Struct

from iommi import MISSING
from iommi._web_compat import Template
from iommi.base import (
    build_as_view_wrapper,
    capitalize,
    get_display_name,
    model_and_rows,
    UnknownMissingValueException,
)
from tests.helpers import req
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


def test_capitalize_safetext():
    capitalized = capitalize(mark_safe('xFooBarBaz Foo oOOOo'))
    assert str(capitalized) == 'XFooBarBaz Foo oOOOo'
    assert isinstance(capitalized, SafeText)


@pytest.mark.django_db
def test_model_and_rows():
    # Model only defaults to all()
    model, rows = model_and_rows(model=Foo, rows=None)
    assert model is Foo and str(rows.query) == str(Foo.objects.all().query)

    # rows is preserved and model is returned
    orig_rows = Foo.objects.filter(foo=2)
    model, rows = model_and_rows(model=None, rows=orig_rows)
    assert model is Foo and rows is orig_rows


def test_get_display_name():
    mock = Struct(_name='foo_bar_TLA')
    assert get_display_name(mock) == 'Foo bar TLA'

    mock.model_field = Struct()
    assert get_display_name(mock) == 'Foo bar TLA'

    mock.model_field.verbose_name = None
    assert get_display_name(mock) == 'Foo bar TLA'

    mock.model_field.verbose_name = 'some other THING'
    assert get_display_name(mock) == 'Some other THING'


def test_crash_in_templates():
    # We should crash in template rendering during tests if we try to render non-existent stuff
    with pytest.raises(AssertionError) as e:
        Template('{{ foo }}').render(context=RequestContext(req('get')))

    assert str(e.value) == 'Tried to render non-existent variable foo'

    # ...but inside if it's fine
    assert Template('{% if foo %}foo{% endif %}').render(context=RequestContext(req('get'))) == ''
