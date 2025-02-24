import pytest
from django.http import HttpResponse
from django.template import RequestContext
from django.test import override_settings
from django.utils import translation
from django.utils.safestring import (
    SafeText,
    mark_safe,
)
from django.utils.translation import gettext_lazy
from django.views.decorators.csrf import csrf_exempt

from iommi import (
    MISSING,
    Fragment,
    Page,
)
from iommi._web_compat import Template
from iommi.base import (
    UnknownMissingValueException,
    build_as_view_wrapper,
    capitalize,
    get_display_name,
    get_wrapped_view,
    model_and_rows,
)
from iommi.struct import Struct
from tests.helpers import req
from tests.models import Foo


def test_missing():
    assert str(MISSING) == 'MISSING'
    assert repr(MISSING) == 'MISSING'

    with pytest.raises(UnknownMissingValueException) as e:
        if MISSING:
            pass  # pragma: no cover

    assert str(e.value) == 'MISSING is neither True nor False, it is unknown'


def test_build_as_view_wrapper():
    class Foo(Fragment):
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


def test_capitalize_lazy():
    translation.activate('en')
    capitalized = capitalize(gettext_lazy('edit'))
    assert str(capitalized) == 'Edit'
    translation.activate('sv')
    assert str(capitalized) == 'Ändra'
    translation.activate('en')
    assert str(capitalized) == 'Edit'


@pytest.mark.django_db
def test_model_and_rows():
    # Model only defaults to all()
    model, rows = model_and_rows(model=Foo, rows=None)
    assert model is Foo and str(rows.query) == str(Foo.objects.all().query)

    # rows is preserved and model is returned
    orig_rows = Foo.objects.filter(foo=2)
    model, rows = model_and_rows(model=None, rows=orig_rows)
    assert model is Foo and rows is orig_rows

    assert model_and_rows(None, None) == (None, None)


def test_get_display_name():
    mock = Struct(_name='foo_bar_TLA')
    assert get_display_name(mock) == 'Foo bar TLA'

    mock.model_field = Struct()
    assert get_display_name(mock) == 'Foo bar TLA'

    mock.model_field.verbose_name = None
    assert get_display_name(mock) == 'Foo bar TLA'

    mock.model_field.verbose_name = 'some other THING'
    assert get_display_name(mock) == 'Some other THING'


def function_based_view(request):
    return HttpResponse('hello!')  # pragma: no cover


class PartBasedViewPage(Page):
    hello = 'hello!'


with override_settings(DEBUG=True):
    part_based_view = PartBasedViewPage().as_view()


def test_get_wrapped_view_function():
    view = function_based_view
    assert get_wrapped_view(view) is view
    assert get_wrapped_view(csrf_exempt(view)) is view


def test_get_wrapped_part_view_wrapped():
    view = part_based_view
    assert get_wrapped_view(view) is view.__iommi_target__
    assert get_wrapped_view(csrf_exempt(view)) is view.__iommi_target__
    assert isinstance(view.__iommi_target__, PartBasedViewPage)


@pytest.mark.parametrize('optimize', [False, True])
def test_refine_done_optimization(optimize):
    with override_settings(IOMMI_REFINE_DONE_OPTIMIZATION=optimize):
        view = PartBasedViewPage().as_view()
        assert not view.__iommi_target__.is_refine_done

        view(req('get'))

        if optimize:
            assert view.__iommi_target__.is_refine_done
        else:
            assert not view.__iommi_target__.is_refine_done


def test_not_bound_yet_error():
    with pytest.raises(AssertionError) as e:
        Page().iommi_dunder_path

    assert (
        str(e.value)
        == 'This object is not bound. You need to call `.bind(request=request)` before you can call this function.'
    )
