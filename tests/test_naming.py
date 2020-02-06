from django.test import RequestFactory
from iommi import (
    Column,
    Field,
    Form,
    Table,
)
from iommi.base import (
    build_long_path_by_path,
)
from iommi.page import (
    Fragment,
    Page,
)
from tri_declarative import Namespace
from tri_struct import Struct

from tests.helpers import StubTraversable


def test_traverse():
    baz = Struct(name='baz', declared_members={})
    buzz = Struct(name='buzz', declared_members={})
    bar = Struct(
        name='bar',
        declared_members=Struct(
            baz=baz,
            buzz=buzz,
        ),
    )
    foo = Struct(
        name='foo',
        declared_members=Struct(
            bar=bar,
        ),
    )
    root = StubTraversable(
        name='root',
        children=Struct(
            foo=foo
        ),
    )

    expected = {
        '': '',
        'foo': 'foo',
        'bar': 'foo/bar',
        'baz': 'foo/bar/baz',
        'buzz': 'foo/bar/buzz',
    }
    actual = build_long_path_by_path(root)
    assert actual.items() == expected.items()
    assert len(actual.keys()) == len(set(actual.keys()))


def test_traverse_on_iommi():
    class MyPage(Page):
        header = Fragment()
        some_form = Form(fields=Namespace(
            fisk=Field(),
        ))
        some_other_form = Form(fields=Namespace(
            fjomp=Field(),
            fisk=Field(),
        ))
        a_table = Table(columns=Namespace(
            columns=Column(),
            fusk=Column(query__include=True, query__form__include=True),
        ))

    page = MyPage(name='root')

    actual = build_long_path_by_path(page)
    for k, v in actual.items():
        print(repr(k), repr(v))

    assert len(actual.keys()) == len(set(actual.keys()))
    page = page.bind(request=RequestFactory().get('/'))

    assert page.path() == ''
    assert page.parts.header.path() == 'header'
    assert page.parts.some_form.fields.fisk.path() == 'fisk'
    assert page.parts.some_other_form.fields.fisk.path() == 'some_other_form/fisk'
    assert page.parts.a_table.columns.fusk.path() == 'fusk'
    # assert page.parts.a_table.query.form.path() == ''
