import json
from collections import defaultdict

import django
import pytest
from django.db.models import QuerySet
from django.http import HttpResponse
from django.test import override_settings
from django.utils.safestring import mark_safe
from tri_declarative import (
    class_shortcut,
    get_members,
    get_shortcuts_by_name,
    getattr_path,
    is_shortcut,
    Namespace,
    Shortcut,
)

from iommi import (
    Action,
    Page,
)
from iommi._web_compat import Template
from iommi.endpoint import (
    find_target,
    InvalidEndpointPathException,
    perform_ajax_dispatch,
)
from iommi.form import (
    Field,
    Form,
)
from iommi.from_model import register_name_field
from iommi.query import (
    Query,
    Variable,
)
from iommi.table import (
    Column,
    register_cell_formatter,
    SELECT_DISPLAY_NAME,
    Struct,
    Table,
    yes_no_formatter,
)
from tests.helpers import (
    req,
    request_with_middleware,
    verify_table_html,
)
from tests.models import (
    BooleanFromModelTestModel,
    CSVExportTestModel,
    FromModelWithInheritanceTest,
    QueryFromIndexesTestModel,
    TBar,
    TBaz,
    TFoo,
)

register_name_field(model=TFoo, name_field='b', allow_non_unique=True)


def get_rows():
    return [
        Struct(foo="Hello", bar=17),
        Struct(foo="<evil/> &", bar=42)
    ]


def explicit_table():
    columns = dict(
        foo=Column(),
        bar=Column.number(),
    )

    return Table(rows=get_rows(), columns=columns, attrs__class__another_class=True, attrs__id='table_id')


def declarative_table():
    class TestTable(Table):
        class Meta:
            attrs__class__another_class = lambda table, **_: True
            attrs__id = lambda table, **_: 'table_id'

        foo = Column()
        bar = Column.number()

    return TestTable(rows=get_rows())


@pytest.mark.parametrize('table_builder', [
    explicit_table,
    declarative_table
])
def test_render_impl(table_builder):
    table = table_builder()
    verify_table_html(table=table, expected_html="""
        <table class="another_class table" data-endpoint="/tbody" id="table_id">
            <thead>
                <tr>
                    <th class="first_column subheader">
                        <a href="?order=foo"> Foo </a>
                    </th>
                    <th class="first_column subheader">
                        <a href="?order=bar"> Bar </a>
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td> Hello </td>
                    <td class="rj"> 17 </td>
                </tr>
                <tr>
                    <td> &lt;evil/&gt; &amp; </td>
                    <td class="rj"> 42 </td>
                </tr>
            </tbody>
        </table>""")


def test_declaration_merge():
    class MyTable(Table):
        class Meta:
            columns__name = Column()

        bar = Column()

    assert {'name', 'bar'} == set(MyTable(rows=[]).bind(request=None).columns.keys())


def test_kwarg_column_config_injection():
    class MyTable(Table):
        foo = Column()

    table = MyTable(rows=[], columns__foo__extra__stuff="baz")
    table = table.bind(request=None)
    assert 'baz' == table.columns['foo'].extra.stuff


def test_bad_arg():
    with pytest.raises(TypeError) as e:
        Table(rows=[], columns__foo=Column(), foo=None)
    assert 'foo' in str(e.value)


def test_column_ordering():
    class MyTable(Table):
        foo = Column(after='bar')
        bar = Column()

    assert ['bar', 'foo'] == list(MyTable(rows=[]).bind(request=None).columns.keys())


def test_column_with_meta():
    class MyColumn(Column):
        class Meta:
            sortable = False

    class MyTable(Table):
        foo = MyColumn()
        bar = MyColumn.icon('history')

    table = MyTable(rows=[])
    table = table.bind(request=None)
    assert not table.columns['foo'].sortable
    assert not table.columns['bar'].sortable


@pytest.mark.django_db
def test_django_table():
    f1 = TFoo.objects.create(a=17, b="Hej")
    f2 = TFoo.objects.create(a=42, b="Hopp")

    TBar(foo=f1, c=True).save()
    TBar(foo=f2, c=False).save()

    class TestTable(Table):
        foo__a = Column.number()
        foo__b = Column()
        foo = Column.choice_queryset(model=TFoo, choices=lambda table, **_: TFoo.objects.all(), query__include=True, bulk__include=True, query__form__include=True)

    t = TestTable(rows=TBar.objects.all().order_by('pk'))
    t = t.bind(request=req('get'))

    assert list(t.columns['foo'].choices) == list(TFoo.objects.all())

    assert t.bulk_form._is_bound
    assert list(t.bulk_form.fields['foo'].choices) == list(TFoo.objects.all())

    assert t.query.form._is_bound
    assert list(t.query.form.fields['foo'].choices) == list(TFoo.objects.all())

    verify_table_html(table=t, expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr>
                    <th class="first_column subheader">
                        <a href="?order=foo__a"> A </a>
                    </th>
                    <th class="first_column subheader">
                        <a href="?order=foo__b"> B </a>
                    </th>
                    <th class="first_column subheader">
                        <a href="?order=foo"> Foo </a>
                    </th>
                </tr>
            </thead>
            <tbody>
                <tr data-pk="1">
                    <td class="rj"> 17 </td>
                    <td> Hej </td>
                    <td> Foo(17, Hej) </td>

                </tr>
                <tr data-pk="2">
                    <td class="rj"> 42 </td>
                    <td> Hopp </td>
                    <td> Foo(42, Hopp) </td>
                </tr>
            </tbody>
        </table>""")


def test_inheritance():
    class FooTable(Table):
        foo = Column()

    class BarTable(Table):
        bar = Column()

    class TestTable(FooTable, BarTable):
        another = Column()

    t = TestTable(rows=[]).bind(request=None)
    assert list(t.columns.keys()) == ['foo', 'bar', 'another']


def test_output():
    class TestTable(Table):
        class Meta:
            attrs__class__foo = True
            attrs__id = 'table_id'

        foo = Column()
        bar = Column.number()
        icon = Column.icon('history', group="group")
        edit = Column.edit(group="group")
        delete = Column.delete()

    rows = [
        Struct(foo="Hello räksmörgås ><&>",
               bar=17,
               get_absolute_url=lambda: '/somewhere/'),
    ]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="foo table" data-endpoint="/tbody" id="table_id">
            <thead>
                <tr>
                    <th class="superheader" colspan="1"> </th>
                    <th class="superheader" colspan="1"> </th>
                    <th class="superheader" colspan="2"> group </th>
                    <th class="superheader" colspan="1"> </th>
                </tr>
                <tr>
                    <th class="first_column subheader">
                        <a href="?order=foo"> Foo </a>
                    </th>
                    <th class="first_column subheader">
                        <a href="?order=bar"> Bar </a>
                    </th>
                    <th class="first_column subheader"> </th>
                    <th class="subheader"> Edit </th>
                    <th class="first_column subheader"> Delete </th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td> Hello räksmörgås &gt;&lt;&amp;&gt; </td>
                    <td class="rj"> 17 </td>
                    <td> <i class="fa fa-history fa-lg"> </i> </td>
                    <td> <a href="/somewhere/edit/"> <i class="fa fa-lg fa-pencil-square-o"> </i> Edit </a> </td>
                    <td> <a href="/somewhere/delete/"> <i class="fa fa-lg fa-trash-o"> </i> Delete </a> </td>
                </tr>
            </tbody>
        </table>
        """)


def test_name_traversal():
    class TestTable(Table):
        foo__bar = Column(sortable=False)

    rows = [Struct(foo=Struct(bar="bar"))]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr>
                    <th class="first_column subheader"> Bar </th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td> bar </td>
                </tr>
            </tbody>
        </table>""")


# def test_tuple_data():
#     class TestTable(Table):
#
#         class Meta:
#             sortable = False
#
#         a = Column()
#         b = Column()
#         c = Column()
#
#     rows = [('a', 'b', 'c')]
#
#     verify_table_html(TestTable(rows=rows), """
#         <table class="table" data-endpoint="/tbody">
#             <thead>
#                 <tr>
#                     <th class="first_column subheader"> A </th>
#                     <th class="first_column subheader"> B </th>
#                     <th class="first_column subheader"> C </th>
#                 </tr>
#             </thead>
#             <tbody>
#                 <tr>
#                     <td> a </td>
#                     <td> b </td>
#                     <td> c </td>
#                 </tr>
#             </tbody>
#         </table>""")


# def test_dict_data():
#     class TestTable(Table):
#         class Meta:
#             sortable = False
#         a = Column()
#         b = Column()
#         c = Column()
#
#     rows = [{'a': 'a', 'b': 'b', 'c': 'c'}]
#
#     verify_table_html(TestTable(rows=rows), """
#         <table class="table" data-endpoint="/tbody">
#              <thead>
#                  <tr>
#                      <th class="first_column subheader"> A </th>
#                      <th class="first_column subheader"> B </th>
#                      <th class="first_column subheader"> C </th>
#                  </tr>
#              </thead>
#              <tbody>
#                  <tr>
#                      <td> a </td>
#                      <td> b </td>
#                      <td> c </td>
#                  </tr>
#              </tbody>
#          </table>""")

# noinspection PyPep8Naming
@pytest.fixture
def NoSortTable():
    class NoSortTable(Table):
        class Meta:
            sortable = False
    return NoSortTable


def test_display_name(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(display_name="Bar")

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr>
                    <th class="first_column subheader"> Bar </th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td> foo </td>
                </tr>
            </tbody>
        </table>""")


def test_link(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column.link(cell__url='https://whereever', cell__url_title="whatever")
        bar = Column.link(cell__value='bar', cell__url_title=lambda value, **_: "url_title_goes_here")

    rows = [Struct(foo='foo', bar=Struct(get_absolute_url=lambda: '/get/absolute/url/result'))]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr>
                    <th class="first_column subheader"> Foo </th>
                    <th class="first_column subheader"> Bar </th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td> <a href="https://whereever" title="whatever"> foo </a> </td>
                    <td> <a href="/get/absolute/url/result" title="url_title_goes_here"> bar </a> </td>
                </tr>
            </tbody>
        </table>""")



def test_cell__url_with_attr(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(cell__url='https://whereever', cell__url_title="whatever", cell__link__attrs__class__custom='custom')

    rows = [Struct(foo='foo', bar=Struct(get_absolute_url=lambda: '/get/absolute/url/result'))]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr>
                    <th class="first_column subheader"> Foo </th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td> <a class="custom" href="https://whereever" title="whatever"> foo </a> </td>
                </tr>
            </tbody>
        </table>""")


def test_css_class(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(
            header__attrs__class__some_class=True,
            cell__attrs__class__bar=True
        )

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
    <table class="table" data-endpoint="/tbody">
        <thead>
            <tr>
                <th class="first_column some_class subheader"> Foo </th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="bar"> foo </td>
            </tr>
        </tbody>
    </table>""")


def test_header_url(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(header__url="/some/url")

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
    <table class="table" data-endpoint="/tbody">
        <thead>
            <tr><th class="first_column subheader">
                <a href="/some/url"> Foo </a>
            </th></tr>
        </thead>
        <tbody>
            <tr>
                <td> foo </td>
            </tr>
        </tbody>
    </table>""")


def test_include(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column(include=False)

    rows = [Struct(foo="foo", bar="bar")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
    <table class="table" data-endpoint="/tbody">
        <thead>
            <tr><th class="first_column subheader"> Foo </th></tr>
        </thead>
        <tbody>
            <tr>
                <td> foo </td>
            </tr>
        </tbody>
    </table>""")


def test_include_lambda(NoSortTable):
    def include_callable(table, column):
        assert isinstance(table, TestTable)
        assert column._name == 'bar'
        return False

    class TestTable(NoSortTable):
        foo = Column()
        bar = Column.icon('foo', include=include_callable)

    rows = [Struct(foo="foo", bar="bar")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
    <table class="table" data-endpoint="/tbody">
        <thead>
            <tr><th class="first_column subheader"> Foo </th></tr>
        </thead>
        <tbody>
            <tr>
                <td> foo </td>
            </tr>
        </tbody>
    </table>""")


def test_attr(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column(attr='foo')

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
    <table class="table" data-endpoint="/tbody">
        <thead>
            <tr>
                <th class="first_column subheader"> Foo </th>
                <th class="first_column subheader"> Bar </th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td> foo </td>
                <td> foo </td>
            </tr>
        </tbody>
    </table>""")


def test_attrs(NoSortTable):
    class TestTable(NoSortTable):
        class Meta:
            attrs__class__classy = True
            attrs__foo = lambda table, **_: 'bar'
            row__attrs__class__classier = True
            row__attrs__foo = lambda table, row, **_: "barier"

        yada = Column()

    verify_table_html(table=TestTable(rows=[Struct(yada=1), Struct(yada=2)]), expected_html="""
        <table class="classy table" data-endpoint="/tbody" foo="bar">
            <thead>
                <tr>
                  <th class="first_column subheader"> Yada </th>
                </tr>
            </thead>
            <tbody>
                <tr class="classier" foo="barier">
                    <td> 1 </td>
                </tr>
                <tr class="classier" foo="barier">
                    <td> 2 </td>
                </tr>
            </tbody>
        </table>""")


def test_attrs_new_syntax(NoSortTable):
    class TestTable(NoSortTable):
        class Meta:
            attrs__class__classy = True
            attrs__foo = lambda table, **_: 'bar'

            row__attrs__class__classier = True
            row__attrs__foo = lambda table, **_: "barier"

        yada = Column()

    verify_table_html(table=TestTable(rows=[Struct(yada=1), Struct(yada=2)]), expected_html="""
        <table class="classy table" data-endpoint="/tbody" foo="bar">
            <thead>
                <tr>
                  <th class="first_column subheader"> Yada </th>
                </tr>
            </thead>
            <tbody>
                <tr class="classier" foo="barier">
                    <td> 1 </td>
                </tr>
                <tr class="classier" foo="barier">
                    <td> 2 </td>
                </tr>
            </tbody>
        </table>""")


def test_column_presets(NoSortTable):
    class TestTable(NoSortTable):
        icon = Column.icon('some-icon')
        edit = Column.edit()
        delete = Column.delete()
        download = Column.download()
        run = Column.run()
        select = Column.select()
        boolean = Column.boolean()
        link = Column.link(cell__format="Yadahada name")
        number = Column.number()

    rows = [
        Struct(
            pk=123,
            get_absolute_url=lambda: "http://yada/",
            boolean=lambda: True,
            link=Struct(get_absolute_url=lambda: "http://yadahada/"),
            number=123
        )
    ]
    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr>
                    <th class="first_column subheader" />
                    <th class="first_column subheader">Edit </th>
                    <th class="first_column subheader">Delete </th>
                    <th class="first_column subheader">Download </th>
                    <th class="first_column subheader">Run </th>
                    <th class="first_column subheader" title="Select all">
                        {}
                    </th>
                    <th class="first_column subheader"> Boolean </th>
                    <th class="first_column subheader"> Link </th>
                    <th class="first_column subheader"> Number </th>
                </tr>
            </thead>
            <tbody>
                <tr data-pk="123">
                    <td> <i class="fa fa-lg fa-some-icon" /> </td>
                    <td> <a href="http://yada/edit/"> <i class="fa fa-lg fa-pencil-square-o"/> Edit </a> </td>
                    <td> <a href="http://yada/delete/"> <i class="fa fa-lg fa-trash-o"/> Delete </a> </td>
                    <td> <a href="http://yada/download/"> <i class="fa fa-download fa-lg"/> Download </a> </td>
                    <td> <a href="http://yada/run/"> Run </a> </td>
                    <td> <input class="checkbox" name="pk_123" type="checkbox"/> </td> <td> <i class="fa fa-check" title="Yes" /> </td>
                    <td> <a href="http://yadahada/"> Yadahada name </a> </td>
                    <td class="rj"> 123 </td>
                </tr>
            </tbody>
        </table>""".format(SELECT_DISPLAY_NAME))


@pytest.mark.django_db
def test_django_table_pagination():
    for x in range(30):
        TFoo(a=x, b="foo").save()

    class TestTable(Table):
        a = Column.number(sortable=False)  # turn off sorting to not get the link with random query params
        b = Column(include=False)  # should still be able to filter on this though!

    verify_table_html(table=TestTable(rows=TFoo.objects.all().order_by('pk')),
                      query=dict(page_size=2, page=2, query='b="foo"'),
                      expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr>
                    <th class="first_column subheader"> A </th>
                </tr>
            </thead>
            <tbody>
                <tr data-pk="3">
                    <td class="rj"> 2 </td>
                </tr>
                <tr data-pk="4">
                    <td class="rj"> 3 </td>
                </tr>
            </tbody>
        </table>""")


@pytest.mark.skipif(django.VERSION[0] < 2, reason='This requires the new paginator API in django 2.0+')
@pytest.mark.django_db
def test_django_table_pagination_custom_paginator():
    for x in range(30):
        TFoo(a=x, b="foo").save()

    class TestTable(Table):
        a = Column.number(sortable=False)  # turn off sorting to not get the link with random query params
        b = Column(include=False)  # should still be able to filter on this though!

    from django.core.paginator import Paginator

    class CustomPaginator(Paginator):
        def __init__(self, object_list, *_, **__):
            super(CustomPaginator, self).__init__(object_list=object_list, per_page=2)

        def get_page(self, number):
            del number
            return self.page(2)

    rows = TFoo.objects.all().order_by('pk')
    verify_table_html(
        table=TestTable(
            rows=rows,
            paginator=CustomPaginator,
        ),
        expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr>
                    <th class="first_column subheader"> A </th>
                </tr>
            </thead>
            <tbody>
                <tr data-pk="3">
                    <td class="rj"> 2 </td>
                </tr>
                <tr data-pk="4">
                    <td class="rj"> 3 </td>
                </tr>
            </tbody>
        </table>""")


def test_actions(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(header__attrs__title="Some title")

        class Meta:
            actions = dict(
                a=Action(display_name='Foo', attrs__href='/foo/', include=lambda table, **_: table.rows is not rows),
                b=Action(display_name='Bar', attrs__href='/bar/', include=lambda table, **_: table.rows is rows),
                c=Action(display_name='Baz', attrs__href='/bar/', group='Other'),
                d=dict(display_name='Qux', attrs__href='/bar/', group='Other'),
                e=Action.icon('icon_foo', display_name='Icon foo', attrs__href='/icon_foo/'),
                f=Action.icon('icon_bar', icon_classes=['lg'], display_name='Icon bar', attrs__href='/icon_bar/'),
                g=Action.icon('icon_baz', icon_classes=['one', 'two'], display_name='Icon baz', attrs__href='/icon_baz/'),
            )

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows),
                      find=dict(class_='links'),
                      expected_html="""
        <div class="links">
            <div class="dropdown">
                <a class="button button-primary" data-target="#" data-toggle="dropdown" href="/page.html" id="id_dropdown_other" role="button">
                    Other <i class="fa fa-lg fa-caret-down" />
                </a>
                <ul aria-labelledby="id_dropdown_Other" class="dropdown-menu" role="menu">
                    <li role="presentation">
                        <a href="/bar/" role="menuitem"> Baz </a>
                    </li>
                    <li role="presentation">
                        <a href="/bar/" role="menuitem"> Qux </a>
                    </li>
                </ul>
            </div>

            <a href="/bar/"> Bar </a>

            <a href="/icon_foo/"> <i class="fa fa-icon_foo " /> Icon foo </a>
            <a href="/icon_bar/"> <i class="fa fa-icon_bar fa-lg" /> Icon bar </a>
            <a href="/icon_baz/"> <i class="fa fa-icon_baz fa-one fa-two" /> Icon baz </a>
        </div>""")


@pytest.mark.django_db
def test_bulk_edit():
    assert TFoo.objects.all().count() == 0

    foos = [
        TFoo.objects.create(a=1, b=""),
        TFoo.objects.create(a=2, b=""),
        TFoo.objects.create(a=3, b=""),
        TFoo.objects.create(a=4, b=""),
    ]

    assert [x.pk for x in foos] == [1, 2, 3, 4]

    class TestTable(Table):
        a = Column.integer(sortable=False, bulk__include=True)  # turn off sorting to not get the link with random query params
        b = Column(bulk__include=True)

    result = TestTable(
        rows=TFoo.objects.all(),
    ).bind(
        request=req('get'),
    ).__html__()
    assert '<form action="" enctype="multipart/form-data" method="post">' in result, result
    assert '<input accesskey="s" name="-bulk/submit" type="submit" value="Bulk change">' in result, result

    def post_bulk_edit(table, queryset, updates, **_):
        assert isinstance(table, TestTable)
        assert isinstance(queryset, QuerySet)
        assert {x.pk for x in queryset} == {1, 2}
        assert updates == dict(a=0, b='changed')

    t = TestTable(
        rows=TFoo.objects.all().order_by('pk'),
        post_bulk_edit=post_bulk_edit,
    ).bind(
        request=req('post', pk_1='', pk_2='', **{'bulk/a': '0', 'bulk/b': 'changed', '-bulk/submit': ''}),
    )
    assert t._is_bound
    assert t.bulk_form._name == 'bulk'
    t.render_to_response()

    assert [(x.pk, x.a, x.b) for x in TFoo.objects.all()] == [
        (1, 0, u'changed'),
        (2, 0, u'changed'),
        (3, 3, u''),
        (4, 4, u''),
    ]

    # Test that empty field means "no change"
    TestTable(
        rows=TFoo.objects.all()
    ).bind(
        request=req('post', pk_1='', pk_2='', **{'bulk/a': '', 'bulk/b': ''}),
    ).render_to_response()
    assert [(x.pk, x.a, x.b) for x in TFoo.objects.all()] == [
        (1, 0, u'changed'),
        (2, 0, u'changed'),
        (3, 3, u''),
        (4, 4, u''),
    ]

    # Test edit all feature
    TestTable(
        rows=TFoo.objects.all()
    ).bind(
        request=req('post', _all_pks_='1', **{'bulk/a': '11', 'bulk/b': 'changed2', '-bulk/submit': ''}),
    ).render_to_response()

    assert [(x.pk, x.a, x.b) for x in TFoo.objects.all()] == [
        (1, 11, u'changed2'),
        (2, 11, u'changed2'),
        (3, 11, u'changed2'),
        (4, 11, u'changed2'),
    ]


@pytest.mark.django_db
def test_bulk_edit_from_model_has_tristate_for_booleans():
    t = Table(
        auto__model=BooleanFromModelTestModel,
        columns__b__bulk__include=True,
    ).bind(request=req('get'))
    assert t.bulk_form.fields.b.__tri_declarative_shortcut_stack[0] == 'boolean_tristate'


@pytest.mark.django_db
def test_bulk_edit_for_m2m_relations():
    f1 = TFoo.objects.create(a=1, b='a')
    f2 = TFoo.objects.create(a=2, b='b')
    baz = TBaz.objects.create()
    baz.foo.set([f1, f2])

    t = Table(
        auto__model=TBaz,
        columns__foo__bulk__include=True,
    ).bind(request=req('post', _all_pks_='1', **{'bulk/foo': [f1.pk], '-bulk/submit': ''}))
    t.render_to_response()
    baz.refresh_from_db()
    assert list(baz.foo.all()) == [f1]


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_bulk_delete():
    TFoo.objects.create(a=1, b='a')
    TFoo.objects.create(a=2, b='b')
    t = Table(
        auto__model=TFoo,
        bulk__actions__delete__include=True,
    ).bind(request=req('post', _all_pks_='1', **{'-delete': ''}))
    assert 'Are you sure you want to delete these' in t.render_to_response().content.decode()

    t = Table(
        auto__model=TFoo,
        bulk__actions__delete__include=True,
    ).bind(request=req('post', _all_pks_='1', **{'-delete': '', 'confirmed': 'confirmed'}))
    response = t.render_to_response()
    assert response.status_code == 302, response.content.decode()

    assert TFoo.objects.count() == 0


@pytest.mark.django_db
def test_invalid_syntax_query():
    class TestTable(Table):
        a = Column.number(sortable=False, query__include=True)

    adv_query_param = TestTable(model=TFoo).bind(request=req('get')).query.get_advanced_query_param()

    verify_table_html(query={adv_query_param: '!!!'}, table=TestTable(rows=TFoo.objects.all().order_by('pk')), find=dict(class_='iommi_query_error'), expected_html='<div class="iommi_query_error">Invalid syntax for query</div>')


@pytest.mark.django_db
def test_query():
    assert TFoo.objects.all().count() == 0

    TFoo(a=1, b="foo").save()
    TFoo(a=2, b="foo").save()
    TFoo(a=3, b="bar").save()
    TFoo(a=4, b="bar").save()

    class TestTable(Table):
        a = Column.number(sortable=False, query__include=True, query__form__include=True)  # turn off sorting to not get the link with random query params
        b = Column.substring(query__include=True, query__form__include=True)

        class Meta:
            sortable = False

    t = TestTable(rows=TFoo.objects.all().order_by('pk'))
    t = t.bind(request=req('get'))
    assert t.query.variables.a.iommi_path == 'query/a'
    assert t.query.form.fields.a.iommi_path == 'a'

    rows = TFoo.objects.all().order_by('pk')

    verify_table_html(
        query=dict(a='1'),
        table=TestTable(rows=rows),
        find=dict(name='tbody'),
        expected_html="""
    <tbody>
        <tr data-pk="1">
            <td class="rj">
                1
            </td>
            <td>
                foo
            </td>
        </tr>
    </table>
    """)
    verify_table_html(
        query=dict(b='bar'),
        table=TestTable(rows=rows),
        find=dict(name='tbody'),
        expected_html="""
    <tbody>
        <tr data-pk="3">
            <td class="rj">
                3
            </td>
            <td>
                bar
            </td>
        </tr>
        <tr data-pk="4">
            <td class="rj">
                4
            </td>
            <td>
                bar
            </td>
        </tr>
    </tbody>
    """)
    verify_table_html(
        query={t.query.get_advanced_query_param(): 'b="bar"'},
        table=TestTable(rows=rows),
        find=dict(name='tbody'),
        expected_html="""
    <tbody>
        <tr data-pk="3">
            <td class="rj">
                3
            </td>
            <td>
                bar
            </td>
        </tr>
        <tr data-pk="4">
            <td class="rj">
                4
            </td>
            <td>
                bar
            </td>
        </tr>
    </tbody>
    """)
    verify_table_html(
        query=dict(b='fo'),
        table=TestTable(rows=rows),
        find=dict(name='tbody'),
        expected_html="""
    <tbody>
        <tr data-pk="1">
            <td class="rj">
                1
            </td>
            <td>
                foo
            </td>
        </tr>
        <tr data-pk="2">
            <td class="rj">
                2
            </td>
            <td>
                foo
            </td>
        </tr>
    </table>
    """)


def test_cell_template(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(cell__template='test_cell_template.html')

    rows = [Struct(foo="sentinel")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr><th class="first_column subheader"> Foo </th></tr>
            </thead>
            <tbody>
                <tr>
                    Custom rendered: sentinel
                </tr>
            </tbody>
        </table>""")


def test_cell_format_escape(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(cell__format=lambda value, **_: '<foo>')

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
            <table class="table" data-endpoint="/tbody">
                <thead>
                    <tr><th class="first_column subheader"> Foo </th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td>
                            &lt;foo&gt;
                        </td>
                    </tr>
                </tbody>
            </table>""")


def test_cell_format_no_escape(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(cell__format=lambda value, **_: mark_safe('<foo/>'))

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
            <table class="table" data-endpoint="/tbody">
                <thead>
                    <tr><th class="first_column subheader"> Foo </th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td>
                            <foo/>
                        </td>
                    </tr>
                </tbody>
            </table>""")


@pytest.mark.django_db
def test_template_string(NoSortTable):
    TFoo.objects.create(a=1)

    class TestTable(NoSortTable):
        class Meta:
            model = TFoo
            actions_template = Template('What links')
            header__template = Template('What headers')
            query__template = Template('What filters')

            row__template = Template('Oh, rows: {% for cell in bound_row %}{{ cell }}{% endfor %}')

        a = Column(
            cell__template=Template('Custom cell: {{ row.a }}'),
            query__include=True,
            query__form__include=True,
        )

    verify_table_html(
        table=TestTable(
            actions__foo=Action(display_name='foo', attrs__href='bar'),
        ),
        expected_html="""
        What filters
        <div class="table-container">
            <form action="." method="post">
                <table class="table" data-endpoint="/tbody">
                    What headers
                    <tbody>
                        Oh, rows: Custom cell: 1
                    </tbody>
                </table>
                What links
            </form>
        </div>""")


def test_cell_template_string(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(
            cell__template=Template('Custom renderedXXXX: {{ row.foo }}'),
        )

    rows = [Struct(foo="sentinel")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr><th class="first_column subheader"> Foo </th></tr>
            </thead>
            <tbody>
                <tr>
                    Custom renderedXXXX: sentinel
                </tr>
            </tbody>
        </table>""")


def test_no_header_template(NoSortTable):
    class TestTable(NoSortTable):
        class Meta:
            header__template = None

        foo = Column()

    rows = [Struct(foo="bar")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <tbody>
                <tr>
                    <td>
                        bar
                    </td>
                </tr>
            </tbody>
        </table>""")


def test_row_template(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column()

        class Meta:
            row__template = lambda table, **_: 'test_table_row.html'

    rows = [Struct(foo="sentinel", bar="schmentinel")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr>
                  <th class="first_column subheader"> Foo </th>
                  <th class="first_column subheader"> Bar </th>
                </tr>
            </thead>
            <tbody>

             All columns:
             <td> sentinel </td>
             <td> schmentinel </td>

             One by name:
              <td> sentinel </td>
            </tbody>
        </table>""")


def test_cell_lambda(NoSortTable):
    class TestTable(NoSortTable):
        sentinel1 = 'sentinel1'

        sentinel2 = Column(cell__value=lambda table, column, row, **_: '%s %s %s' % (table.sentinel1, column._name, row.sentinel3))

    rows = [Struct(sentinel3="sentinel3")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr><th class="first_column subheader"> Sentinel2 </th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        sentinel1 sentinel2 sentinel3
                    </td>
                </tr>
            </tbody>
        </table>""")


def test_auto_rowspan_and_render_twice(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(auto_rowspan=True)

    rows = [
        Struct(foo=1),
        Struct(foo=1),
        Struct(foo=2),
        Struct(foo=2),
    ]

    expected = """
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr><th class="first_column subheader"> Foo </th></tr>
            </thead>
            <tbody>
                <tr>
                    <td rowspan="2"> 1 </td>
                </tr>
                <tr>
                    <td style="display: none"> 1 </td>
                </tr>
                <tr>
                    <td rowspan="2"> 2 </td>
                </tr>
                <tr>
                    <td style="display: none"> 2 </td>
                </tr>
            </tbody>
        </table>"""

    t = TestTable(rows=rows)
    t = t.bind(request=req('get'))
    verify_table_html(table=t, expected_html=expected)
    verify_table_html(table=t, expected_html=expected)


def test_render_table(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(display_name="TBar")

    rows = [Struct(foo="foo")]

    response = TestTable(rows=rows).bind(request=req('get')).render_to_response()
    assert isinstance(response, HttpResponse)
    assert b'<table' in response.content


@pytest.mark.django_db
def test_default_formatters(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column()

    class SomeType(object):
        def __str__(self):
            return 'this should not end up in the table'

    register_cell_formatter(SomeType, lambda value, **_: 'sentinel')

    assert TFoo.objects.all().count() == 0

    TFoo(a=1, b="3").save()
    TFoo(a=2, b="5").save()

    rows = [
        Struct(foo=1),
        Struct(foo=True),
        Struct(foo=False),
        Struct(foo=[1, 2, 3]),
        Struct(foo=SomeType()),
        Struct(foo=TFoo.objects.all()),
        Struct(foo=None),
    ]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="table" data-endpoint="/tbody">
            <thead>
                <tr><th class="first_column subheader"> Foo </th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        1
                    </td>
                </tr>
                <tr>
                    <td>
                        Yes
                    </td>
                </tr>
                <tr>
                    <td>
                        No
                    </td>
                </tr>
                <tr>
                    <td>
                        1, 2, 3
                    </td>
                </tr>
                <tr>
                    <td>
                        sentinel
                    </td>
                </tr>
                <tr>
                    <td>
                        Foo(1, 3), Foo(2, 5)
                    </td>
                </tr>
                <tr>
                    <td>
                    </td>
                </tr>
            </tbody>
        </table>""")


@pytest.mark.django_db
def test_choice_queryset():
    assert TFoo.objects.all().count() == 0

    TFoo.objects.create(a=1)
    TFoo.objects.create(a=2)

    class FooTable(Table):
        foo = Column.choice_queryset(query__include=True, query__form__include=True, bulk__include=True, choices=lambda table, **_: TFoo.objects.filter(a=1))

        class Meta:
            model = TFoo

    foo_table = FooTable(
        rows=TFoo.objects.all(),
    ).bind(
        request=req('get'),
    )

    assert repr(foo_table.columns['foo'].choices) == repr(TFoo.objects.filter(a=1))
    assert repr(foo_table.bulk_form.fields['foo'].choices) == repr(TFoo.objects.filter(a=1))
    assert repr(foo_table.query.form.fields['foo'].choices) == repr(TFoo.objects.filter(a=1))


@pytest.mark.django_db
def test_multi_choice_queryset():
    assert TFoo.objects.all().count() == 0

    TFoo.objects.create(a=1)
    TFoo.objects.create(a=2)
    TFoo.objects.create(a=3)
    TFoo.objects.create(a=4)

    class FooTable(Table):
        foo = Column.multi_choice_queryset(query__include=True, query__form__include=True, bulk__include=True, choices=lambda table, **_: TFoo.objects.exclude(a=3).exclude(a=4))

        class Meta:
            model = TFoo

    table = FooTable(rows=TFoo.objects.all())
    table = table.bind(request=req('get'))

    assert repr(table.columns['foo'].choices) == repr(TFoo.objects.exclude(a=3).exclude(a=4))
    assert repr(table.bulk_form.fields['foo'].choices) == repr(TFoo.objects.exclude(a=3).exclude(a=4))
    assert repr(table.query.form.fields['foo'].choices) == repr(TFoo.objects.exclude(a=3).exclude(a=4))


@pytest.mark.django_db
def test_query_namespace_inject():
    class FooException(Exception):
        pass

    def post_validation(form):
        del form
        raise FooException()

    with pytest.raises(FooException):
        Table(
            rows=[],
            model=TFoo,
            columns__a=Column(_name='a', query__include=True, query__form__include=True),
            query__form__post_validation=post_validation,
        ).bind(
            request=Struct(method='POST', POST={'-': '-'}, GET=Struct(urlencode=lambda: '')),
        )


def test_float():
    x = Column.float()
    assert getattr_path(x, 'query__call_target__attribute') == 'float'
    assert getattr_path(x, 'bulk__call_target__attribute') == 'float'


def test_integer():
    x = Column.integer()
    assert getattr_path(x, 'query__call_target__attribute') == 'integer'
    assert getattr_path(x, 'bulk__call_target__attribute') == 'integer'


def test_date():
    x = Column.date()
    assert getattr_path(x, 'query__call_target__attribute') == 'date'
    assert getattr_path(x, 'bulk__call_target__attribute') == 'date'


def test_datetime():
    x = Column.datetime()
    assert getattr_path(x, 'query__call_target__attribute') == 'datetime'
    assert getattr_path(x, 'bulk__call_target__attribute') == 'datetime'


def test_email():
    x = Column.email()
    assert getattr_path(x, 'query__call_target__attribute') == 'email'
    assert getattr_path(x, 'bulk__call_target__attribute') == 'email'


def test_extra():
    class TestTable(Table):
        foo = Column(extra__foo=1, extra__bar=2)

    assert TestTable(rows=[]).bind(request=None).columns.foo.extra.foo == 1
    assert TestTable(rows=[]).bind(request=None).columns.foo.extra.bar == 2


def test_row_extra():
    class TestTable(Table):
        result = Column(cell__value=lambda bound_row, **_: bound_row.extra_evaluated.foo)

        class Meta:
            row__extra__foo = 7
            row__extra_evaluated__foo = lambda table, row, **_: row.a + row.b

    table = TestTable(
        rows=[Struct(a=5, b=7)]
    ).bind(
        request=req('get'),
    )
    bound_row = list(table.bound_rows())[0]

    assert bound_row.extra.foo == 7
    assert bound_row.extra_evaluated.foo == 5 + 7
    assert bound_row['result'].value == 5 + 7


def test_row_extra_evaluated():
    def some_callable(table, row, **_):
        return row.a + row.b

    class TestTable(Table):
        result = Column(cell__value=lambda bound_row, **_: bound_row.extra_evaluated.foo)

        class Meta:
            row__extra__foo = some_callable
            row__extra_evaluated__foo = some_callable

    table = TestTable(
        rows=[Struct(a=5, b=7)],
    ).bind(
        request=req('get'),
    )
    bound_row = list(table.bound_rows())[0]
    assert bound_row.extra.foo is some_callable
    assert bound_row.extra_evaluated.foo == 5 + 7
    assert bound_row['result'].value == 5 + 7


def test_from_model():
    t = Table(
        auto__model=TFoo,
        columns__a__display_name='Some a',
        columns__a__extra__stuff='Some stuff',
    )
    t = t.bind(request=None)
    assert list(t._declared_members.columns.keys()) == ['id', 'a', 'b', 'select']
    assert list(t.columns.keys()) == ['a', 'b']
    assert 'Some a' == t.columns['a'].display_name
    assert 'Some stuff' == t.columns['a'].extra.stuff


def test_from_model_foreign_key():
    t = Table(
        auto__model=TBar,
    ).bind(request=None)
    assert list(t._declared_members.columns.keys()) == ['id', 'foo', 'c', 'select']
    assert list(t.columns.keys()) == ['foo', 'c']


def test_select_ordering():
    t = Table(
        auto__model=TBar,
        columns__select__include=True,
    ).bind(request=None)
    assert list(t._declared_members.columns.keys()) == ['id', 'foo', 'c', 'select']
    assert list(t.columns.keys()) == ['select', 'foo', 'c']


@pytest.mark.django_db
def test_explicit_table_does_not_use_from_model():
    class TestTable(Table):
        foo = Column.choice_queryset(
            model=TFoo,
            choices=lambda table, **_: TFoo.objects.all(),
            query__form__extra__endpoint_attr='b',
            query__include=True,
            query__form__include=True,
            bulk__include=True,
        )

    t = TestTable().bind(request=None)
    assert list(t._declared_members.columns.keys()) == ['foo']


@pytest.mark.django_db
def test_from_model_implicit():
    class TestTable(Table):
        pass

    t = TestTable(auto__rows=TBar.objects.all()).bind(request=None)
    assert list(t._declared_members.columns.keys()) == ['id', 'foo', 'c', 'select']


@override_settings(DEBUG=True)
@pytest.mark.django_db
def test_ajax_endpoint():
    f1 = TFoo.objects.create(a=17, b="Hej")
    f2 = TFoo.objects.create(a=42, b="Hopp")

    TBar(foo=f1, c=True).save()
    TBar(foo=f2, c=False).save()

    class TestTable(Table):
        foo = Column.choice_queryset(
            model=TFoo,
            choices=lambda table, **_: TFoo.objects.all(),
            query__form__extra__endpoint_attr='b',
            query__include=True,
            query__form__include=True,
            bulk__include=True,
        )

    # This test could also have been made with perform_ajax_dispatch directly, but it's nice to have a test that tests more of the code path
    result = request_with_middleware(
        response=Page(
            parts__table=TestTable(
                rows=TBar.objects.all()
            ),
        ),
        data={'/parts/table/query/form/fields/foo/endpoints/choices': 'hopp'},
    )
    assert json.loads(result.content) == {
        'results': [
            {'id': 2, 'text': 'Foo(42, Hopp)'},
        ],
        'pagination': {'more': False},
        'page': 1,
    }


@pytest.mark.django_db
def test_ajax_endpoint_empty_response():
    class TestTable(Table):
        class Meta:
            endpoints__foo__func = lambda **_: []

        bar = Column()

    actual = perform_ajax_dispatch(root=TestTable(rows=[]).bind(request=req('get')), path='/foo', value='')
    assert actual == []


def test_ajax_data_endpoint():
    class TestTable(Table):
        class Meta:
            endpoints__data__func = lambda table, **_: [{cell.column._name: cell.value for cell in bound_row} for bound_row in table.bound_rows()]

        foo = Column()
        bar = Column()

    table = TestTable(rows=[
        Struct(foo=1, bar=2),
        Struct(foo=3, bar=4),
    ])
    table = table.bind(request=req('get'))

    actual = perform_ajax_dispatch(root=table, path='/data', value='')
    expected = [dict(foo=1, bar=2), dict(foo=3, bar=4)]
    assert actual == expected


def test_ajax_endpoint_namespacing():
    class TestTable(Table):
        class Meta:
            endpoints__bar__func = lambda **_: 17

        baz = Column()

    with pytest.raises(InvalidEndpointPathException):
        perform_ajax_dispatch(root=TestTable(rows=[]).bind(request=req('get')), path='/baz', value='')

    actual = perform_ajax_dispatch(root=TestTable(rows=[]).bind(request=req('get')), path='/bar', value='')
    assert 17 == actual


def test_table_iteration():
    class TestTable(Table):
        class Meta:
            rows = [
                Struct(foo='a', bar=1),
                Struct(foo='b', bar=2)
            ]

        foo = Column()
        bar = Column(cell__value=lambda row, **_: row['bar'] + 1)

    table = TestTable().bind(request=req('get'))

    assert [
        {
            bound_cell.column._name: bound_cell.value
            for bound_cell in bound_row
        }
        for bound_row in table.bound_rows()
    ] == [
        dict(foo='a', bar=2),
        dict(foo='b', bar=3),
    ]


def test_ajax_custom_endpoint():
    class TestTable(Table):
        class Meta:
            endpoints__foo__func = lambda value, **_: dict(baz=value)

        spam = Column()

    actual = perform_ajax_dispatch(root=TestTable(rows=[]).bind(request=req('get')), path='/foo', value='bar')
    assert actual == dict(baz='bar')


def test_table_extra_namespace():
    class TestTable(Table):
        class Meta:
            extra__foo = 17

        foo = Column()

    assert TestTable(rows=[]).bind(request=req('get')).extra.foo == 17


def test_defaults():
    class TestTable(Table):
        foo = Column()

    table = TestTable()
    table = table.bind(request=None)

    col = table.columns.foo
    assert table.query is None
    assert table.bulk_form is None
    assert not col.auto_rowspan
    assert not col.sort_default_desc
    assert col.sortable
    assert col.include


def test_yes_no_formatter():
    assert yes_no_formatter(None) == ''
    assert yes_no_formatter(True) == 'Yes'
    assert yes_no_formatter(1) == 'Yes'
    assert yes_no_formatter(False) == 'No'
    assert yes_no_formatter(0) == 'No'

    with pytest.raises(AssertionError) as e:
        yes_no_formatter({})

    assert str(e.value) == 'Unable to convert {} to Yes/No'


def test_repr():
    assert repr(Column(_name='foo')) == '<iommi.table.Column foo>'


@pytest.mark.django_db
def test_ordering():
    TFoo.objects.create(a=1, b='d')
    TFoo.objects.create(a=2, b='c')
    TFoo.objects.create(a=3, b='b')
    TFoo.objects.create(a=4, b='a')

    # no ordering
    t = Table(auto__model=TFoo)
    t = t.bind(request=req('get'))
    assert not t.rows.query.order_by

    # ordering from GET parameter
    t = Table(auto__model=TFoo)
    t = t.bind(request=req('get', order='a'))
    assert list(t.rows.query.order_by) == ['a']

    # default ordering
    t = Table(auto__model=TFoo, default_sort_order='b')
    t = t.bind(request=req('get', order='b'))
    assert list(t.rows.query.order_by) == ['b']


@pytest.mark.django_db
def test_many_to_many():
    f1 = TFoo.objects.create(a=17, b="Hej")
    f2 = TFoo.objects.create(a=23, b="Hopp")

    baz = TBaz.objects.create()
    f1.tbaz_set.add(baz)
    f2.tbaz_set.add(baz)

    expected_html = """
<table class="table" data-endpoint="/tbody">
    <thead>
        <tr>
            <th class="first_column subheader">
                Foo
            </th>
        </tr>
    </thead>
    <tbody>
        <tr data-pk="1">
            <td>
                Foo(17, Hej), Foo(23, Hopp)
            </td>
        </tr>
    </tbody>
</table>
"""

    verify_table_html(expected_html=expected_html, table__auto__model=TBaz)


@pytest.mark.django_db
def test_preprocess_row():
    TFoo.objects.create(a=1, b='d')

    def preprocess(table, row, **_):
        del table
        row.some_non_existent_property = 1
        return row

    class PreprocessedTable(Table):
        some_non_existent_property = Column()

        class Meta:
            preprocess_row = preprocess
            rows = TFoo.objects.all().order_by('pk')

    expected_html = """
    <table class="table" data-endpoint="/tbody">
        <thead>
            <tr>
                <th class="first_column subheader">
                    <a href="?order=some_non_existent_property">
                        Some non existent property
                    </a>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr data-pk="1">
                <td>
                    1
                </td>
            </tr>
        </tbody>
    </table>
    """

    verify_table_html(expected_html=expected_html, table=PreprocessedTable())


@pytest.mark.django_db
def test_yield_rows():
    f = TFoo.objects.create(a=3, b='d')

    def my_preprocess_rows(rows, **kwargs):
        for row in rows:
            yield row
            yield Struct(a=row.a * 5)

    class MyTable(Table):
        a = Column()

        class Meta:
            preprocess_rows = my_preprocess_rows

    table = MyTable(rows=TFoo.objects.all())
    table = table.bind(request=None)
    results = list(table.bound_rows())
    assert len(results) == 2
    assert results[0].row == f
    assert results[1].row == Struct(a=15)


@pytest.mark.django_db
def test_error_on_invalid_variable_setup():
    class MyTable(Table):
        c = Column(attr=None, query__include=True, query__form__include=True)

        class Meta:
            model = TFoo

    table = MyTable()
    with pytest.raises(AssertionError):
        table = table.bind(request=req('get'))


@pytest.mark.django_db
def test_from_model_with_inheritance():
    was_called = defaultdict(int)

    class MyField(Field):
        @classmethod
        @class_shortcut
        def float(cls, call_target=None, **kwargs):
            was_called['MyField.float'] += 1
            return call_target(**kwargs)

    class MyForm(Form):
        class Meta:
            member_class = MyField

    class MyVariable(Variable):
        @classmethod
        @class_shortcut(
            form__call_target__attribute='float',
        )
        def float(cls, call_target=None, **kwargs):
            was_called['MyVariable.float'] += 1
            return call_target(**kwargs)

    class MyQuery(Query):
        class Meta:
            member_class = MyVariable
            form_class = MyForm

    class MyColumn(Column):
        @classmethod
        @class_shortcut(
            call_target__attribute='number',
            query__call_target__attribute='float',
            bulk__call_target__attribute='float',
        )
        def float(cls, call_target, **kwargs):
            was_called['MyColumn.float'] += 1
            return call_target(**kwargs)

    class MyTable(Table):
        class Meta:
            member_class = MyColumn
            form_class = MyForm
            query_class = MyQuery

    MyTable(
        auto__rows=FromModelWithInheritanceTest.objects.all(),
        auto__model=FromModelWithInheritanceTest,
        columns__value__query__include=True,
        columns__value__query__form__include=True,
        columns__value__bulk__include=True,
    ).bind(
        request=req('get'),
    )

    assert was_called == {
        'MyField.float': 2,
        'MyVariable.float': 1,
        'MyColumn.float': 1,
    }


def test_column_merge():
    table = Table(
        columns__foo={},
        rows=[
            Struct(foo=1),
        ]
    )
    table = table.bind(request=None)
    assert len(table.columns) == 1
    assert table.columns.foo._name == 'foo'
    for row in table.bound_rows():
        assert row['foo'].value == 1


def test_hide_named_column():
    class MyTable(Table):
        foo = Column()

    table = MyTable(columns__foo__include=False, rows=[])
    table = table.bind(request=None)
    assert len(table.columns) == 0


def test_override_doesnt_stick():
    class MyTable(Table):
        foo = Column()

    table = MyTable(columns__foo__include=False, rows=[])
    table = table.bind(request=None)
    assert len(table.columns) == 0

    table2 = MyTable(rows=[])
    table2 = table2.bind(request=None)
    assert len(table2.columns) == 1


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_new_style_ajax_dispatch():
    TFoo.objects.create(a=1, b='A')
    TFoo.objects.create(a=2, b='B')
    TFoo.objects.create(a=3, b='C')

    def get_response(request):
        del request
        return Table(auto__model=TBar, columns__foo__query=dict(include=True, form__include=True))

    from iommi import middleware
    m = middleware(get_response)
    response = m(request=req('get', **{'/query/form/fields/foo/endpoints/choices': ''}))

    assert json.loads(response.content) == {
        'results': [
            {'id': 1, 'text': 'Foo(1, A)'},
            {'id': 2, 'text': 'Foo(2, B)'},
            {'id': 3, 'text': 'Foo(3, C)'},
        ],
        'page': 1,
        'pagination': {'more': False},
    }


@override_settings(DEBUG=True)
def test_endpoint_path_of_nested_part():
    page = Table(auto__model=TBar, columns__foo__query=dict(include=True, form__include=True))
    page.bind(request=None)
    target = find_target(path='/query/form/fields/foo/endpoints/choices', root=page)
    assert target.endpoint_path == '/choices'
    assert target.iommi_dunder_path == 'query__form__fields__foo__endpoints__choices'


def test_dunder_name_for_column():
    class FooTable(Table):
        class Meta:
            model = TBar

        foo = Column(query__include=True, query__form__include=True)
        foo__a = Column(query__include=True, query__form__include=True)

    table = FooTable()
    table = table.bind(request=None)
    assert list(table.columns.keys()) == ['foo', 'foo__a']
    assert list(table.query.variables.keys()) == ['foo', 'foo__a']
    assert list(table.query.form.fields.keys()) == ['foo', 'foo__a']


def test_render_column_attribute():
    class FooTable(Table):
        a = Column()
        b = Column(render_column=False)
        c = Column(render_column=lambda column, **_: False)

    t = FooTable()
    t = t.bind(request=None)

    assert list(t.rendered_columns.keys()) == ['a']
    assert [h.display_name for h in t.header_levels[0]] == ['A']

    expected_html = """
    <table class="table" data-endpoint="/tbody">
        <thead>
            <tr>
                <th class="first_column subheader">
                    <a href="?order=a">
                        A
                    </a>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>
                    1
                </td>
            </tr>
        </tbody>
    </table>
    """

    verify_table_html(expected_html=expected_html, table=FooTable(rows=[Struct(a=1)]))


@pytest.mark.parametrize('name, shortcut', get_shortcuts_by_name(Column).items())
def test_shortcuts_map_to_form_and_query(name, shortcut):
    whitelist = {
        'icon',
        'select',
        'run',
        'link',
        'number',  # no equivalent in Field or Variable, there you have to choose integer or float
        'substring',
        'boolean_tristate',  # this is special in the bulk case where you want want a boolean_quadstate: don't change, clear, True, False. For now we'll wait for someone to report this misfeature/bug :)
    }
    if name in whitelist:
        return

    if 'call_target' in shortcut.dispatch and shortcut.dispatch.call_target.attribute in whitelist:
        # shortcuts that in turn point to whitelisted ones are also whitelisted
        return

    assert shortcut.dispatch.query.call_target.attribute == name
    assert shortcut.dispatch.bulk.call_target.attribute == name


@pytest.mark.django_db
def test_bulk_namespaces_are_merged():
    t = Table(
        auto__model=TFoo,
        bulk__fields__a__initial=3,
        columns__a__bulk=dict(
            display_name='7',
            include=True,
        ),
    )
    t = t.bind(request=req('get'))
    assert t.bulk_form.fields.a.initial == 3
    assert t.bulk_form.fields.a.display_name == '7'


@override_settings(IOMMI_DEBUG=True)
def test_data_iommi_path():
    class FooTable(Table):
        a = Column(group='foo')

    t = FooTable()
    t = t.bind(request=None)

    expected_html = """
    <table class="table" data-endpoint="/tbody" data-iommi-path="">
        <thead>
            <tr>
                <th class="superheader" colspan="1">
                    foo
                </th>
            </tr>

            <tr>
                <th class="first_column subheader" data-iommi-path="columns__a__header">
                    <a href="?order=a">
                        A
                    </a>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr data-iommi-path="row">
                <td data-iommi-path="columns__a__cell">
                    1
                </td>
            </tr>
        </tbody>
    </table>
    """

    verify_table_html(expected_html=expected_html, table=FooTable(rows=[Struct(a=1)]))


@pytest.mark.django_db
def test_csv_download_error_message_column():
    TFoo.objects.create(a=1, b='a')
    TFoo.objects.create(a=2, b='b')
    t = Table(
        auto__model=TFoo,
    ).bind(request=req('get', **{'/csv': ''}))
    with pytest.raises(AssertionError) as e:
        t.render_to_response()

    assert str(e.value) == 'To get CSV output you must specify at least one column with extra_evaluated__report_name'


@pytest.mark.django_db
def test_csv_download_error_message_filename():
    TFoo.objects.create(a=1, b='a')
    TFoo.objects.create(a=2, b='b')
    t = Table(
        auto__model=TFoo,
        columns__a__extra_evaluated__report_name='A',
    ).bind(request=req('get', **{'/csv': ''}))
    with pytest.raises(AssertionError) as e:
        t.render_to_response()

    assert str(e.value) == 'To get CSV output you must specify extra_evaluated__report_name on the table'


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_csv_download():
    CSVExportTestModel.objects.create(a=1, b='a', c=2.3)
    CSVExportTestModel.objects.create(a=2, b='b', c=5.0)
    t = Table(
        auto__model=CSVExportTestModel,
        columns__a__extra_evaluated__report_name='A',
        columns__b__extra_evaluated__report_name='B',
        columns__c__extra_evaluated__report_name='C',
        columns__d__extra_evaluated__report_name='D',
        columns__danger__extra_evaluated__report_name='DANGER',
        extra_evaluated__report_name='foo',
    ).bind(request=req('get', **{'/csv': ''}))
    response = t.render_to_response()
    assert response['Content-Type'] == 'text/csv'
    assert response['Content-Disposition'] == "attachment; filename*=UTF-8''foo.csv"
    assert response.getvalue().decode() == """
A,B,C,D,DANGER
1,a,2.3,,\t=2+5+cmd|' /C calc'!A0
2,b,5.0,,\t=2+5+cmd|' /C calc'!A0
""".lstrip().replace('\n', '\r\n')


@pytest.mark.django_db
def test_query_from_indexes():
    t = Table(
        auto__model=QueryFromIndexesTestModel,
        query_from_indexes=True,
    ).bind(request=req('get'))
    assert list(t.query.variables.keys()) == ['b', 'c']
    assert list(t.query.form.fields.keys()) == ['b', 'c']


@pytest.mark.django_db
def test_table_as_view():
    render_to_response_path = Table(
        auto__model=TFoo,
        query_from_indexes=True,
    ).bind(request=req('get')).render_to_response().content

    as_view_path = Table(auto__model=TFoo, query_from_indexes=True).as_view()(request=req('get')).content
    assert render_to_response_path == as_view_path


@pytest.mark.django_db
def test_all_column_shortcuts():
    class MyFancyColumn(Column):
        class Meta:
            extra__fancy = True

    class MyFancyTable(Table):
        class Meta:
            member_class = MyFancyColumn

    all_shortcut_names = get_members(
        cls=MyFancyColumn,
        member_class=Shortcut,
        is_member=is_shortcut,
    ).keys()

    config = {
        f'columns__column_of_type_{t}__call_target__attribute': t
        for t in all_shortcut_names
    }

    type_specifics = Namespace(
        columns__column_of_type_choice__choices=[],
        columns__column_of_type_multi_choice__choices=[],
        columns__column_of_type_choice_queryset__choices=TFoo.objects.none(),
        columns__column_of_type_multi_choice_queryset__choices=TFoo.objects.none(),
        columns__column_of_type_many_to_many__model_field=TBaz.foo.field,
        columns__column_of_type_foreign_key__model_field=TBar.foo.field,
    )

    table = MyFancyTable(
        **config,
        **type_specifics,
    ).bind(
        request=req('get'),
    )

    for name, column in table.columns.items():
        assert column.extra.get('fancy'), name


@pytest.mark.django_db
def test_paginator_rendered():
    TFoo.objects.create(a=17, b="Hej")
    TFoo.objects.create(a=42, b="Hopp")

    content = Table(
        auto__model=TFoo,
        query_from_indexes=True,
        page_size=1,
    ).bind(request=req('get')).render_to_response().content.decode()

    assert 'aria-label="Pages"' in content
