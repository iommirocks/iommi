import json
from collections import defaultdict
from datetime import (
    date,
    datetime,
    time,
)

import django
import pytest
from django.db.models import QuerySet
from django.http import HttpResponse
from django.test import override_settings
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
    html,
    Page,
)
from iommi._web_compat import (
    mark_safe,
    Template,
)
from iommi.base import (
    items,
    keys,
)
from iommi.endpoint import (
    find_target,
    InvalidEndpointPathException,
    perform_ajax_dispatch,
)
from iommi.form import (
    Field,
    Form,
)
from iommi.from_model import register_search_fields
from iommi.query import (
    Filter,
    Query,
)
from iommi.sql_trace import (
    set_sql_debug,
    SQL_DEBUG_LEVEL_ALL,
)
from iommi.table import (
    bulk_delete__post_handler,
    Column,
    datetime_formatter,
    ordered_by_on_list,
    register_cell_formatter,
    Struct,
    Table,
    yes_no_formatter,
)
from iommi.traversable import declared_members
from tests.helpers import (
    req,
    request_with_middleware,
    verify_table_html,
)
from tests.models import (
    AutomaticUrl,
    AutomaticUrl2,
    BooleanFromModelTestModel,
    ChoicesModel,
    CSVExportTestModel,
    FromModelWithInheritanceTest,
    QueryFromIndexesTestModel,
    SortKeyOnForeignKeyB,
    T2,
    TBar,
    TBar2,
    TBaz,
    TFoo,
)

register_search_fields(model=TFoo, search_fields=['b'], allow_non_unique=True)


def get_rows():
    return [Struct(foo="Hello", bar=17), Struct(foo="<evil/> &", bar=42)]


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


@pytest.mark.parametrize('table_builder', [explicit_table, declarative_table])
def test_render_impl(table_builder):
    table = table_builder()
    verify_table_html(
        table=table,
        expected_html="""
        <table class="another_class table" data-endpoint="/tbody" data-iommi-id="" id="table_id">
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
        </table>""",
    )


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
        foo = Column.choice_queryset(
            model=TFoo, choices=lambda table, **_: TFoo.objects.all(), filter__include=True, bulk__include=True
        )
    with pytest.deprecated_call():
        t = TestTable(rows=TBar.objects.all().order_by('pk'))
        t = t.bind(request=req('get'))

    assert list(t.columns['foo'].choices) == list(TFoo.objects.all())

    assert t.bulk._is_bound
    assert list(t.bulk.fields['foo'].choices) == list(TFoo.objects.all())

    assert t.query.form._is_bound
    assert list(t.query.form.fields['foo'].choices) == list(TFoo.objects.all())

    verify_table_html(
        table=t,
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
        </table>""",
    )


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
        Struct(foo="Hello räksmörgås ><&>", bar=17, get_absolute_url=lambda: '/somewhere/'),
    ]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="foo table" data-endpoint="/tbody" data-iommi-id="" id="table_id">
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
        """,
    )


def test_generator():
    class TestTable(Table):
        foo = Column()
        bar = Column()

    rows = (x for x in [Struct(foo="foo", bar="bar")])

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
                    <td> foo </td>
                    <td> bar </td>
                </tr>
            </tbody>
        </table>
        """,
    )


def test_name_traversal():
    class TestTable(Table):
        foo__bar = Column(sortable=False)

    rows = [Struct(foo=Struct(bar="bar"))]

    with pytest.deprecated_call():
        verify_table_html(
            table=TestTable(rows=rows),
            expected_html="""
            <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
            </table>""",
        )


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
#         <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
#         <table class="table" data-endpoint="/tbody" data-iommi-id="">
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

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
        </table>""",
    )


def test_link(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column.link(cell__url='https://whereever', cell__url_title="whatever")
        bar = Column.link(cell__value='bar', cell__url_title=lambda value, **_: "url_title_goes_here")

    rows = [Struct(foo='foo', bar=Struct(get_absolute_url=lambda: '/get/absolute/url/result'))]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
        </table>""",
    )


def test_cell__url_with_attr(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(
            cell__url='https://whereever', cell__url_title="whatever", cell__link__attrs__class__custom='custom'
        )

    rows = [Struct(foo='foo', bar=Struct(get_absolute_url=lambda: '/get/absolute/url/result'))]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
        </table>""",
    )


def test_css_class(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(header__attrs__class__some_class=True, cell__attrs__class__bar=True)

    rows = [Struct(foo="foo")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
    </table>""",
    )


def test_header_url(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(header__url="/some/url")

    rows = [Struct(foo="foo")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
    </table>""",
    )


def test_include(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column(include=False)

    rows = [Struct(foo="foo", bar="bar")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
        <thead>
            <tr><th class="first_column subheader"> Foo </th></tr>
        </thead>
        <tbody>
            <tr>
                <td> foo </td>
            </tr>
        </tbody>
    </table>""",
    )


def test_include_lambda(NoSortTable):
    def include_callable(table, column, **_):
        assert isinstance(table, TestTable)
        assert column._name == 'bar'
        return False

    class TestTable(NoSortTable):
        foo = Column()
        bar = Column.icon('foo', include=include_callable)

    rows = [Struct(foo="foo", bar="bar")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
        <thead>
            <tr><th class="first_column subheader"> Foo </th></tr>
        </thead>
        <tbody>
            <tr>
                <td> foo </td>
            </tr>
        </tbody>
    </table>""",
    )


def test_attr(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column(attr='foo')

    rows = [Struct(foo="foo")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
    </table>""",
    )


def test_attrs(NoSortTable):
    class TestTable(NoSortTable):
        class Meta:
            attrs__class__classy = True
            attrs__foo = lambda table, **_: 'bar'
            row__attrs__class__classier = True
            row__attrs__foo = lambda table, row, **_: "barier"

        yada = Column()

    verify_table_html(
        table=TestTable(rows=[Struct(yada=1), Struct(yada=2)]),
        expected_html="""
        <table class="classy table" data-endpoint="/tbody" data-iommi-id="" foo="bar">
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
        </table>""",
    )


def test_attrs_new_syntax(NoSortTable):
    class TestTable(NoSortTable):
        class Meta:
            attrs__class__classy = True
            attrs__foo = lambda table, **_: 'bar'

            row__attrs__class__classier = True
            row__attrs__foo = lambda table, **_: "barier"

        yada = Column()

    verify_table_html(
        table=TestTable(rows=[Struct(yada=1), Struct(yada=2)]),
        expected_html="""
        <table class="classy table" data-endpoint="/tbody" data-iommi-id="" foo="bar">
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
        </table>""",
    )


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
            number=123,
        )
    ]
    table = TestTable(rows=rows)

    verify_table_html(
        table=table,
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
            <thead>
                <tr>
                    <th class="first_column subheader" />
                    <th class="first_column subheader">Edit </th>
                    <th class="first_column subheader">Delete </th>
                    <th class="first_column subheader">Download </th>
                    <th class="first_column subheader">Run </th>
                    <th class="first_column subheader" title="Select all">
                        <i class="fa fa-check-square-o" onclick="iommi_table_js_select_all(this, false)"></i>
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
                    <td> <input class="checkbox" name="pk_0" type="checkbox"/> </td> <td> <i class="fa fa-check" title="Yes" /> </td>
                    <td> <a href="http://yadahada/"> Yadahada name </a> </td>
                    <td class="rj"> 123 </td>
                </tr>
            </tbody>
        </table>""",
    )


@pytest.mark.django_db
def test_django_table_pagination():
    for x in range(30):
        TFoo(a=x, b="foo").save()

    class TestTable(Table):
        a = Column.number(sortable=False)  # turn off sorting to not get the link with random query params
        b = Column(include=False)  # should still be able to filter on this though!

    verify_table_html(
        table=TestTable(rows=TFoo.objects.all().order_by('pk')),
        query=dict(page_size=2, page=1, query='b="foo"'),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
            <thead>
                <tr>
                    <th class="first_column subheader"> A </th>
                </tr>
            </thead>
            <tbody>
                <tr data-pk="1">
                    <td class="rj"> 0 </td>
                </tr>
                <tr data-pk="2">
                    <td class="rj"> 1 </td>
                </tr>
            </tbody>
        </table>""",
    )

    verify_table_html(
        table=TestTable(rows=TFoo.objects.all().order_by('pk')),
        query=dict(page_size=2, page=2, query='b="foo"'),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
        </table>""",
    )


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
        a = Column.integer(
            sortable=False, bulk__include=True
        )  # turn off sorting to not get the link with random query params
        b = Column(bulk__include=True)

    result = (
        TestTable(
            rows=TFoo.objects.all(),
        )
        .bind(
            request=req('get'),
        )
        .__html__()
    )
    assert '<form action="" enctype="multipart/form-data" method="post">' in result, result
    assert '<button accesskey="s" name="-bulk/submit">Bulk change</button>' in result, result

    def post_bulk_edit(table, queryset, updates, **_):
        assert isinstance(table, TestTable)
        assert isinstance(queryset, QuerySet)
        assert {x.pk for x in queryset} == {1, 2}
        assert updates == dict(a=0, b='changed')

    # The most important part of the test: don't bulk update with an invalid form!
    t = TestTable(rows=TFoo.objects.all().order_by('pk'), post_bulk_edit=post_bulk_edit,).bind(
        request=req('post', pk_1='', pk_2='', **{'bulk/a': 'asd', 'bulk/b': 'changed', '-bulk/submit': ''}),
    )
    assert t._is_bound
    assert t.bulk._name == 'bulk'
    t.render_to_response()

    assert [(x.pk, x.a, x.b) for x in TFoo.objects.all()] == [
        (1, 1, u''),
        (2, 2, u''),
        (3, 3, u''),
        (4, 4, u''),
    ]

    # Now do the bulk update
    t = TestTable(rows=TFoo.objects.all().order_by('pk'), post_bulk_edit=post_bulk_edit,).bind(
        request=req('post', pk_1='', pk_2='', **{'bulk/a': '0', 'bulk/b': 'changed', '-bulk/submit': ''}),
    )
    assert t._is_bound
    assert t.bulk._name == 'bulk'
    t.render_to_response()

    assert [(x.pk, x.a, x.b) for x in TFoo.objects.all()] == [
        (1, 0, u'changed'),
        (2, 0, u'changed'),
        (3, 3, u''),
        (4, 4, u''),
    ]

    # Test that empty field means "no change", even with the form set to not parse empty as None
    t = TestTable(
        rows=TFoo.objects.all(),
        # TODO: this doesn't do anything, but imo it should work :(
        # bulk__fields__b__parse_empty_string_as_none=False,
        columns__b__bulk__parse_empty_string_as_none=False,
    ).bind(
        request=req('post', pk_1='', pk_2='', **{'bulk/a': '', 'bulk/b': '', '-bulk/submit': ''}),
    )
    t.render_to_response()
    assert t.bulk.fields.b.value == ''
    assert [(x.pk, x.a, x.b) for x in TFoo.objects.all()] == [
        (1, 0, u'changed'),
        (2, 0, u'changed'),
        (3, 3, u''),
        (4, 4, u''),
    ]

    # Test edit all feature
    TestTable(rows=TFoo.objects.all()).bind(
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
    assert t.bulk.fields.b.__tri_declarative_shortcut_stack[0] == 'boolean_tristate'


@pytest.mark.django_db
def test_bulk_edit_container():
    t = Table(
        auto__model=BooleanFromModelTestModel,
        columns__b__bulk__include=True,
        bulk_container__tag='megatag',
        bulk_container__attrs__class__foo=True,
    ).bind(request=req('get'))
    assert '<megatag class="foo">' in str(t)


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
def test_bulk_delete_all_uses_original_rows():
    TFoo.objects.create(a=1, b='a')
    TFoo.objects.create(a=2, b='b')
    TFoo.objects.create(a=3, b='a')
    table = Table(
        rows=TFoo.objects.all().filter(b='a'),
        page_size=1,
        bulk__actions__delete__include=True,
    )

    t = table.bind(request=req('post', _all_pks_='1', **{'-delete': ''}))

    assert 'Are you sure you want to delete these' in t.render_to_response().content.decode()

    t = table.bind(request=req('post', _all_pks_='1', confirmed='confirmed', **{'-delete': ''}))
    response = t.render_to_response()

    assert response.status_code == 302, response.content.decode()
    # Deleting all should not have touched objects in TFoo that were not in rows.
    assert list(TFoo.objects.all().order_by('a').values_list('a', flat=True)) == [2]


@pytest.mark.django_db
def test_bulk_include_false():

    table = Table(
        auto__rows=TFoo.objects.all(),
        columns__a__bulk__include=True,
        bulk__include=False,
    ).bind(request=req('get'))

    assert table.bulk is None
    # we want to see that we can render the table with no crash
    table.__html__()


@pytest.mark.django_db
def test_bulk_delete_all_respects_query():
    TFoo.objects.create(a=1, b='a')
    TFoo.objects.create(a=2, b='b')
    TFoo.objects.create(a=3, b='a')
    table = Table(
        auto__model=TFoo,
        page_size=1,
        bulk__actions__delete__include=True,
        columns__b__filter__include=True,
    )
    t = table.bind(request=req('post', b='a', _all_pks_='1', **{'-delete': ''}))

    assert 'Are you sure you want to delete these' in t.render_to_response().content.decode()

    t = table.bind(request=req('post', b='a', _all_pks_='1', confirmed='confirmed', **{'-delete': ''}))
    response = t.render_to_response()

    assert response.status_code == 302, response.content.decode()
    # Deleting all should not have touched objects in TFoo that were filtered out.
    assert list(TFoo.objects.all().order_by('a').values_list('a', flat=True)) == [2]


def test_bulk_delete_post_handler_does_nothing_on_invalid_form():
    assert bulk_delete__post_handler(table=None, form=Struct(is_valid=lambda: False)) is None


@pytest.mark.django_db
def test_bulk_custom_action_on_list():
    class Row:
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):
            return self.name == other.name

    selected = []

    def my_handler(table, **_):
        nonlocal selected
        selected = table.selection()

    table = Table(
        page_size=None,
        rows=[
            Row('Kaa'),
            Row('Nagini'),
            Row('Mrs. Plithiver'),
        ],
        columns__name=Column(),
        bulk__actions__my_handler=Action.submit(post_handler=my_handler),
    )
    expected_html = """<div class="links">
         <button accesskey="s" name="-my_handler">Submit</button>
    </div>"""
    verify_table_html(table=table.bind(request=req('get')), expected_html=expected_html, find=dict(class_="links"))
    response = table.bind(request=req('post', pk_1='on', **{'-my_handler': ''})).render_to_response()
    assert response.status_code == 200, response.content.decode()
    assert selected == [Row(name='Nagini')]


@pytest.mark.django_db
def test_invalid_syntax_query():
    class TestTable(Table):
        a = Column.number(sortable=False, filter__include=True)

    adv_query_param = TestTable(model=TFoo).bind(request=req('get')).query.get_advanced_query_param()

    verify_table_html(
        query={adv_query_param: '!!!'},
        table=TestTable(rows=TFoo.objects.all().order_by('pk')),
        find=dict(class_='iommi_query_error'),
        expected_html='<div class="iommi_query_error">Invalid syntax for query</div>',
    )


@pytest.mark.django_db
def test_freetext_searching():
    objects = [
        T2.objects.create(foo='q', bar='q'),
        T2.objects.create(foo='A', bar='q'),  # <- we should find this
        T2.objects.create(foo='q', bar='a'),  # <- ...and this
        T2.objects.create(foo='w', bar='w'),
    ]

    t = Table(
        auto__model=T2,
        columns=dict(
            foo__filter=dict(include=True, freetext=True),
            bar__filter=dict(include=True, freetext=True),
        )
    ).bind(request=req('get', freetext_search='a'))

    assert set(t.rows) == set(objects[1:-1])


@pytest.mark.django_db
def test_query_form_freetext():
    class TestTable(Table):
        b = Column(filter__include=True, filter__freetext=True)

    expected_html = """
        <span class="iommi_query_form_simple">
            <div><label for="id_freetext_search">Search</label><input id="id_freetext_search" name="freetext_search" type="text" value=""></div>
        </span>
    """
    verify_table_html(
        table=TestTable(rows=TFoo.objects.all()[:1]),
        find=dict(class_="iommi_query_form_simple"),
        expected_html=expected_html,
    )


@pytest.mark.django_db
def test_query_form_freetext__exclude_label():
    # As of right now this test does not pass!  But I claim it should.
    class TestTable(Table):
        b = Column(filter__include=True, filter__freetext=True)

        class Meta:
            query__form__fields__freetext__label__include = False

    expected_html = """
        <span class="iommi_query_form_simple">
            <div><input id="id_freetext_search" name="freetext_search" type="text" value=""></div>
        </span>
    """
    verify_table_html(
        table=TestTable(rows=TFoo.objects.all()[:1]),
        find=dict(class_="iommi_query_form_simple"),
        expected_html=expected_html,
    )


@pytest.mark.django_db
def test_query_form_foo__exclude_label():
    # As of right now this test does not pass!  But I claim it should.
    class TestTable(Table):
        b = Column(filter__include=True)

        class Meta:
            query__form__fields__b__label__include = False

    expected_html = """
        <span class="iommi_query_form_simple">
            <div><input id="id_b" name="b" type="text" value=""></div>
        </span>
    """
    verify_table_html(
        table=TestTable(rows=TFoo.objects.all()[:1]),
        find=dict(class_="iommi_query_form_simple"),
        expected_html=expected_html,
    )


@pytest.mark.django_db
def test_query():
    assert TFoo.objects.all().count() == 0

    TFoo(a=1, b="foo").save()
    TFoo(a=2, b="foo").save()
    TFoo(a=3, b="bar").save()
    TFoo(a=4, b="bar").save()

    class TestTable(Table):
        a = Column.number(
            sortable=False, filter__include=True
        )  # turn off sorting to not get the link with random query params
        b = Column.substring(filter__include=True)

        class Meta:
            sortable = False

    t = TestTable(rows=TFoo.objects.all().order_by('pk'))
    t = t.bind(request=req('get'))
    assert t.query.filters.a.iommi_path == 'query/a'
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
    """,
    )
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
    """,
    )
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
    """,
    )
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
    """,
    )


def test_cell_template(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(cell__template='test_cell_template.html')

    rows = [Struct(foo="sentinel")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
            <thead>
                <tr><th class="first_column subheader"> Foo </th></tr>
            </thead>
            <tbody>
                <tr>
                    Custom rendered: sentinel
                </tr>
            </tbody>
        </table>""",
    )


def test_no_cell_tag(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(cell__tag=None)

    rows = [Struct(foo="sentinel")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
            <thead>
                <tr><th class="first_column subheader"> Foo </th></tr>
            </thead>
            <tbody>
                <tr>
                    sentinel
                </tr>
            </tbody>
        </table>""",
    )


def test_no_row_tag(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column()

        class Meta:
            row__tag = None

    rows = [Struct(foo="sentinel")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
            <thead>
                <tr><th class="first_column subheader"> Foo </th></tr>
            </thead>
            <tbody>
                <td>sentinel</td>
            </tbody>
        </table>""",
    )


def test_cell_format_escape(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(cell__format=lambda request, value, **_: '<foo>')

    rows = [Struct(foo="foo")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
            <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
            </table>""",
    )


def test_cell_format_no_escape(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(cell__format=lambda value, **_: mark_safe('<foo/>'))

    rows = [Struct(foo="foo")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
            <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
            </table>""",
    )


@pytest.mark.django_db
def test_template_string(NoSortTable):
    TFoo.objects.create(a=1)

    class TestTable(NoSortTable):
        class Meta:
            model = TFoo
            actions_template = Template('What links')
            header__template = Template('What headers')
            query__template = Template('What filters')

            row__template = Template('Oh, rows: {% for cell in cells %}{{ cell }}{% endfor %}')

        a = Column(
            cell__template=Template('Custom cell: {{ row.a }}'),
            filter__include=True,
        )

    verify_table_html(
        table=TestTable(
            actions__foo=Action(display_name='foo', attrs__href='bar'),
        ),
        expected_html="""
        What filters
        <div class="iommi-table-container">
            <form action="." method="post">
                <table class="table" data-endpoint="/tbody" data-iommi-id="">
                    What headers
                    <tbody>
                        Oh, rows: Custom cell: 1
                    </tbody>
                </table>
                What links
            </form>
        </div>""",
    )


def test_cell_template_string(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column(
            cell__template=Template('Custom renderedXXXX: {{ row.foo }}'),
        )

    rows = [Struct(foo="sentinel")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
            <thead>
                <tr><th class="first_column subheader"> Foo </th></tr>
            </thead>
            <tbody>
                <tr>
                    Custom renderedXXXX: sentinel
                </tr>
            </tbody>
        </table>""",
    )


def test_no_header_template(NoSortTable):
    class TestTable(NoSortTable):
        class Meta:
            header__template = None

        foo = Column()

    rows = [Struct(foo="bar")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
            <tbody>
                <tr>
                    <td>
                        bar
                    </td>
                </tr>
            </tbody>
        </table>""",
    )


def test_row_template(NoSortTable):
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column()

        class Meta:
            row__template = lambda table, **_: 'test_table_row.html'

    rows = [Struct(foo="sentinel", bar="schmentinel")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
        </table>""",
    )


def test_cell_lambda(NoSortTable):
    class TestTable(NoSortTable):
        sentinel1 = 'sentinel1'

        sentinel2 = Column(
            cell__value=lambda table, column, row, **_: '%s %s %s' % (table.sentinel1, column._name, row.sentinel3)
        )

    rows = [Struct(sentinel3="sentinel3")]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
        </table>""",
    )


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
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
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


def test_auto_rowspan_fail_on_override():
    with pytest.raises(AssertionError) as e:
        Table(
            columns__foo=Column(
                auto_rowspan=True,
                cell__attrs__rowspan=17,
            )
        ).bind()

    assert str(e.value) == 'Explicitly set rowspan html attribute collides with auto_rowspan on column foo'


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
            return 'this should not end up in the table'  # pragma: no cover

    register_cell_formatter(SomeType, lambda value, **_: 'sentinel')

    assert TFoo.objects.all().count() == 0

    TFoo(a=1, b="3").save()
    TFoo(a=2, b="5").save()

    dt = datetime(2020, 1, 2, 3, 4, 5)
    assert datetime_formatter(dt, format='DATETIME_FORMAT') == 'datetime: Jan. 2, 2020, 3:04 a.m.'

    rows = [
        Struct(foo=1),
        Struct(foo=True),
        Struct(foo=False),
        Struct(foo=[1, 2, 3]),
        Struct(foo=SomeType()),
        Struct(foo=TFoo.objects.all()),
        Struct(foo=None),
        Struct(foo=dt),
        Struct(foo=date(2020, 1, 2)),
        Struct(foo=time(3, 4, 5)),
    ]

    verify_table_html(
        table=TestTable(rows=rows),
        expected_html="""
        <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
                <tr>
                    <td>datetime: Jan. 2, 2020, 3:04 a.m.</td>
                </tr>
                <tr>
                    <td>date: Jan. 2, 2020</td>
                </tr>
                <tr>
                    <td>time: 3:04 a.m.</td>
                </tr>
            </tbody>
        </table>""",
    )


@pytest.mark.django_db
def test_choice_queryset():
    assert TFoo.objects.all().count() == 0

    TFoo.objects.create(a=1)
    TFoo.objects.create(a=2)

    class FooTable(Table):
        foo = Column.choice_queryset(
            attr='a', filter__include=True, bulk__include=True, choices=lambda table, **_: TFoo.objects.filter(a=1)
        )

        class Meta:
            model = TFoo

    foo_table = FooTable(rows=TFoo.objects.all(),).bind(
        request=req('get'),
    )

    assert repr(foo_table.columns['foo'].choices) == repr(TFoo.objects.filter(a=1))
    assert repr(foo_table.bulk.fields['foo'].choices) == repr(TFoo.objects.filter(a=1))
    assert repr(foo_table.query.form.fields['foo'].choices) == repr(TFoo.objects.filter(a=1))


@pytest.mark.django_db
def test_multi_choice_queryset():
    assert TFoo.objects.all().count() == 0

    TFoo.objects.create(a=1)
    TFoo.objects.create(a=2)
    TFoo.objects.create(a=3)
    TFoo.objects.create(a=4)

    class FooTable(Table):
        foo = Column.multi_choice_queryset(
            filter__include=True, bulk__include=True, choices=lambda table, **_: TFoo.objects.exclude(a=3).exclude(a=4)
        )

        class Meta:
            model = TFoo

    table = FooTable(rows=TFoo.objects.all())
    table = table.bind(request=req('get'))

    assert repr(table.columns['foo'].choices) == repr(TFoo.objects.exclude(a=3).exclude(a=4))
    assert repr(table.bulk.fields['foo'].choices) == repr(TFoo.objects.exclude(a=3).exclude(a=4))
    assert repr(table.query.form.fields['foo'].choices) == repr(TFoo.objects.exclude(a=3).exclude(a=4))


@pytest.mark.django_db
def test_query_namespace_inject():
    class FooException(Exception):
        pass

    def post_validation(**_):
        raise FooException()

    with pytest.raises(FooException):
        Table(
            rows=[],
            model=TFoo,
            columns__a=Column(_name='a', filter__include=True),
            query__form__post_validation=post_validation,
        ).bind(
            request=Struct(method='POST', POST={'-submit': '-'}, GET=Struct(urlencode=lambda: '')),
        )


def test_float():
    x = Column.float()
    assert getattr_path(x, 'filter__call_target__attribute') == 'float'
    assert getattr_path(x, 'bulk__call_target__attribute') == 'float'


def test_integer():
    x = Column.integer()
    assert getattr_path(x, 'filter__call_target__attribute') == 'integer'
    assert getattr_path(x, 'bulk__call_target__attribute') == 'integer'


def test_date():
    x = Column.date()
    assert getattr_path(x, 'filter__call_target__attribute') == 'date'
    assert getattr_path(x, 'bulk__call_target__attribute') == 'date'


def test_datetime():
    x = Column.datetime()
    assert getattr_path(x, 'filter__call_target__attribute') == 'datetime'
    assert getattr_path(x, 'bulk__call_target__attribute') == 'datetime'


def test_email():
    x = Column.email()
    assert getattr_path(x, 'filter__call_target__attribute') == 'email'
    assert getattr_path(x, 'bulk__call_target__attribute') == 'email'


def test_extra():
    class TestTable(Table):
        foo = Column(extra__foo=1, extra__bar=2)

    assert TestTable(rows=[]).bind(request=None).columns.foo.extra.foo == 1
    assert TestTable(rows=[]).bind(request=None).columns.foo.extra.bar == 2


def test_row_extra():
    class TestTable(Table):
        result = Column(cell__value=lambda cells, **_: cells.extra_evaluated.foo)

        class Meta:
            row__extra__foo = 7
            row__extra_evaluated__foo = lambda table, row, **_: row.a + row.b

    table = TestTable(rows=[Struct(a=5, b=7)]).bind(
        request=req('get'),
    )
    cells = list(table.cells_for_rows())[0]

    assert cells.extra.foo == 7
    assert cells.extra_evaluated.foo == 5 + 7
    assert cells['result'].value == 5 + 7


def test_row_extra_evaluated():
    def some_callable(row, **_):
        return row.a + row.b

    class TestTable(Table):
        result = Column(cell__value=lambda cells, **_: cells.extra_evaluated.foo)

        class Meta:
            row__extra__foo = some_callable
            row__extra_evaluated__foo = some_callable

    table = TestTable(rows=[Struct(a=5, b=7)],).bind(
        request=req('get'),
    )
    cells = list(table.cells_for_rows())[0]
    assert cells.extra.foo is some_callable
    assert cells.extra_evaluated.foo == 5 + 7
    assert cells['result'].value == 5 + 7


@pytest.mark.django_db
def test_from_model():
    t = Table(
        auto__model=TFoo,
        columns__a__display_name='Some a',
        columns__a__extra__stuff='Some stuff',
    )
    t = t.bind(request=None)
    assert list(declared_members(t).columns.keys()) == ['select', 'id', 'a', 'b']
    assert list(t.columns.keys()) == ['a', 'b']
    assert 'Some a' == t.columns['a'].display_name
    assert 'Some stuff' == t.columns['a'].extra.stuff


@pytest.mark.django_db
def test_from_model_foreign_key():
    t = Table(
        auto__model=TBar,
    ).bind(request=None)
    assert list(declared_members(t).columns.keys()) == ['select', 'id', 'foo', 'c']
    assert list(t.columns.keys()) == ['foo', 'c']


@pytest.mark.django_db
def test_select_ordering():
    t = Table(
        auto__model=TBar,
        columns__select__include=True,
    ).bind(request=None)
    assert list(declared_members(t).columns.keys()) == ['select', 'id', 'foo', 'c']
    assert list(t.columns.keys()) == ['select', 'foo', 'c']


@pytest.mark.django_db
def test_explicit_table_does_not_use_from_model():
    class TestTable(Table):
        foo = Column.choice_queryset(
            model=TFoo,
            choices=lambda table, **_: TFoo.objects.all(),
            filter__include=True,
            bulk__include=True,
        )

    t = TestTable().bind(request=None)
    assert list(declared_members(t).columns.keys()) == ['select', 'foo']
    assert list(t.iommi_bound_members().columns._bound_members.keys()) == ['foo']


@pytest.mark.django_db
def test_from_model_implicit():
    t = Table(auto__rows=TBar.objects.all()).bind(request=None)
    assert list(declared_members(t).columns.keys()) == ['select', 'id', 'foo', 'c']


@pytest.mark.django_db
def test_from_model_implicit_not_break_sorting():
    t = Table(auto__model=TBar, rows=lambda table, **_: TBar.objects.all()).bind(request=None)
    assert isinstance(t.rows, QuerySet)


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
            filter__include=True,
            bulk__include=True,
        )

    # This test could also have been made with perform_ajax_dispatch directly, but it's nice to have a test that tests more of the code path
    result = request_with_middleware(
        Page(
            parts__table=TestTable(rows=TBar.objects.all()),
        ),
        req('get', **{'/parts/table/query/form/fields/foo/endpoints/choices': 'hopp'}),
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
            endpoints__data__func = lambda table, **_: [
                {cell.column._name: cell.value for cell in cells} for cells in table.cells_for_rows()
            ]

        foo = Column()
        bar = Column()

    table = TestTable(
        rows=[
            Struct(foo=1, bar=2),
            Struct(foo=3, bar=4),
        ]
    )
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
            rows = [Struct(foo='a', bar=1), Struct(foo='b', bar=2)]

        foo = Column()
        bar = Column(cell__value=lambda row, **_: row['bar'] + 1)

    table = TestTable().bind(request=req('get'))

    assert [
        {bound_cell.column._name: bound_cell.value for bound_cell in cells} for cells in table.cells_for_rows()
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
    assert table.bulk is None
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
    assert not t.sorted_rows.query.order_by

    # ordering from GET parameter
    t = Table(auto__model=TFoo)
    t = t.bind(request=req('get', order='a'))
    assert list(t.sorted_rows.query.order_by) == ['a']

    # default ordering
    t = Table(auto__model=TFoo, default_sort_order='b')
    t = t.bind(request=req('get', order='b'))
    assert list(t.sorted_rows.query.order_by) == ['b']


@pytest.mark.django_db
def test_many_to_many():
    f1 = TFoo.objects.create(a=17, b="Hej")
    f2 = TFoo.objects.create(a=23, b="Hopp")

    baz = TBaz.objects.create()
    f1.tbaz_set.add(baz)
    f2.tbaz_set.add(baz)

    expected_html = """
<table class="table" data-endpoint="/tbody" data-iommi-id="">
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

    def preprocess(row, **_):
        row.some_non_existent_property = 1
        return row

    class PreprocessedTable(Table):
        some_non_existent_property = Column()

        class Meta:
            preprocess_row = preprocess
            rows = TFoo.objects.all().order_by('pk')

    expected_html = """
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
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

    def my_preprocess_rows(rows, **_):
        for row in rows:
            yield row
            yield Struct(a=row.a * 5)

    class MyTable(Table):
        a = Column()

        class Meta:
            preprocess_rows = my_preprocess_rows

    table = MyTable(rows=TFoo.objects.all())
    table = table.bind(request=None)
    results = list(table.cells_for_rows())
    assert len(results) == 2
    assert results[0].row == f
    assert results[1].row == Struct(a=15)


@pytest.mark.skip('This assert is broken currently, due to value_to_q being a function by default which is truthy')
@pytest.mark.django_db
def test_error_on_invalid_filter_setup():  # pragma: no cover
    class MyTable(Table):
        c = Column(attr=None, filter__include=True)

        class Meta:
            model = TFoo

    table = MyTable()
    with pytest.raises(AssertionError):
        table.bind(request=req('get'))


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

    class MyFilter(Filter):
        @classmethod
        @class_shortcut(
            field__call_target__attribute='float',
        )
        def float(cls, call_target=None, **kwargs):
            was_called['MyVariable.float'] += 1
            return call_target(**kwargs)

    class MyQuery(Query):
        class Meta:
            member_class = MyFilter
            form_class = MyForm

    class MyColumn(Column):
        @classmethod
        @class_shortcut(
            call_target__attribute='number',
            filter__call_target__attribute='float',
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
        columns__value__filter__include=True,
        columns__value__bulk__include=True,
    ).bind(
        request=req('get'),
    )

    assert was_called == {
        'MyField.float': 6,
        'MyVariable.float': 2,
        'MyColumn.float': 2,
    }


def test_column_merge():
    table = Table(
        columns__foo={},
        rows=[
            Struct(foo=1),
        ],
    )
    table = table.bind(request=None)
    assert len(table.columns) == 1
    assert table.columns.foo._name == 'foo'
    for row in table.cells_for_rows():
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
        return Table(auto__model=TBar, columns__foo__filter=dict(include=True, field__include=True))

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


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_endpoint_path_of_nested_part():
    table = Table(
        auto__model=TBar,
        columns__foo__filter=dict(
            include=True,
            field__include=True,
        ),
    ).bind(request=None)
    target = find_target(path='/query/form/fields/foo/endpoints/choices', root=table)
    assert target.endpoint_path == '/choices'
    assert target.iommi_dunder_path == 'query__form__fields__foo__endpoints__choices'


@pytest.mark.django_db
def test_dunder_name_for_column():
    class FooTable(Table):
        class Meta:
            model = TBar

        foo = Column(filter__include=True)
        a = Column(attr='foo__a', filter__include=True)

    table = FooTable()
    table = table.bind(request=None)

    assert list(table.columns.keys()) == ['foo', 'a']
    assert list(table.query.filters.keys()) == ['foo', 'a']
    assert list(table.query.form.fields.keys()) == ['foo', 'a']


@pytest.mark.django_db
def test_dunder_name_for_column_deprecated():
    class FooTable(Table):
        class Meta:
            model = TBar

        foo = Column(filter__include=True)
        foo__a = Column(filter__include=True)

    with pytest.deprecated_call():
        table = FooTable()
        table = table.bind(request=None)

    assert list(table.columns.keys()) == ['foo', 'foo__a']
    assert list(table.query.filters.keys()) == ['foo', 'foo__a']
    assert list(table.query.form.fields.keys()) == ['foo', 'foo__a']


@pytest.mark.django_db
def test_render_column_attribute():
    class FooTable(Table):
        class Meta:
            model = TBar

        a = Column()
        b = Column(render_column=False)
        c = Column(render_column=lambda column, **_: False)
        d = Column(filter__include=True, include=False)

    t = FooTable()
    t = t.bind(request=None)

    assert not keys(t.query.filters)

    assert list(t.columns.keys()) == ['a', 'b', 'c']
    assert [k for k, v in items(t.columns) if v.render_column] == ['a']
    assert [h.display_name for h in t.header_levels[0]] == ['A']

    expected_html = """
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
        'number',  # no equivalent in Field or Filter, there you have to choose integer or float
        'substring',
        'boolean_tristate',  # this is special in the bulk case where you want want a boolean_quadstate: don't change, clear, True, False. For now we'll wait for someone to report this misfeature/bug :)
        'textarea',
    }
    if name in whitelist:
        return

    if 'call_target' in shortcut.dispatch and shortcut.dispatch.call_target.attribute in whitelist:
        # shortcuts that in turn point to whitelisted ones are also whitelisted
        return

    assert shortcut.dispatch.filter.call_target.attribute == name
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
    assert t.bulk.fields.a.initial == 3
    assert t.bulk.fields.a.display_name == '7'


@override_settings(IOMMI_DEBUG=True)
def test_data_iommi_path():
    class FooTable(Table):
        a = Column(group='foo')

    t = FooTable()
    t = t.bind(request=None)

    expected_html = """
    <table class="table" data-endpoint="/tbody" data-iommi-id="" data-iommi-path="" data-iommi-type="FooTable">
        <thead>
            <tr>
                <th class="superheader" colspan="1" data-iommi-type="ColumnHeader">
                    foo
                </th>
            </tr>

            <tr>
                <th class="first_column subheader" data-iommi-path="columns__a__header" data-iommi-type="ColumnHeader">
                    <a href="?order=a">
                        A
                    </a>
                </th>
            </tr>
        </thead>
        <tbody data-iommi-path="tbody" data-iommi-type="Fragment">
            <tr data-iommi-path="row" data-iommi-type="Cells">
                <td data-iommi-path="columns__a__cell" data-iommi-type="Cell">
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
    assert (
        response.getvalue().decode()
        == """
A,B,C,D,DANGER
1,a,2.3,,\t=2+5+cmd|' /C calc'!A0
2,b,5.0,,\t=2+5+cmd|' /C calc'!A0
""".lstrip().replace(
            '\n', '\r\n'
        )
    )


@pytest.mark.django_db
def test_query_from_indexes():
    t = Table(
        auto__model=QueryFromIndexesTestModel,
        query_from_indexes=True,
    ).bind(request=req('get'))
    assert list(t.query.filters.keys()) == ['b', 'c', 'd']
    assert list(t.query.form.fields.keys()) == ['b', 'c', 'd']


@pytest.mark.django_db
def test_table_as_view():
    render_to_response_path = (
        Table(
            auto__model=TFoo,
            query_from_indexes=True,
        )
        .bind(request=req('get'))
        .render_to_response()
        .content
    )

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

    all_shortcut_names = keys(
        get_members(
            cls=MyFancyColumn,
            member_class=Shortcut,
            is_member=is_shortcut,
        )
    )

    config = {f'columns__column_of_type_{t}__call_target__attribute': t for t in all_shortcut_names}

    type_specifics = Namespace(
        columns__column_of_type_choice__choices=[],
        columns__column_of_type_multi_choice__choices=[],
        columns__column_of_type_choice_queryset__choices=TFoo.objects.none(),
        columns__column_of_type_multi_choice_queryset__choices=TFoo.objects.none(),
        columns__column_of_type_many_to_many__model_field=TBaz.foo.field,
        columns__column_of_type_foreign_key__model_field=TBar.foo.field,
    )

    table = MyFancyTable(**config, **type_specifics,).bind(
        request=req('get'),
    )

    for name, column in items(table.columns):
        assert column.extra.get('fancy'), name


@pytest.mark.django_db
def test_paginator_rendered():
    TFoo.objects.create(a=17, b="Hej")
    TFoo.objects.create(a=42, b="Hopp")

    table = Table(
        auto__model=TFoo,
        query_from_indexes=True,
        page_size=1,
    ).bind(request=req('get'))
    assert table.paginator.page_size == 1
    assert table.paginator.count == 2
    assert table.paginator.number_of_pages == 2
    assert table.paginator.is_paginated() is True
    content = table.render_to_response().content.decode()

    assert 'aria-label="Pages"' in content


def test_paginator_clamping():
    t = Table(page_size=1, rows=list(range(10)))
    assert t.bind(request=req('get', page='0')).paginator.page == 1
    assert t.bind(request=req('get', page='3')).paginator.page == 3
    assert t.bind(request=req('get', page='11')).paginator.page == 10


@pytest.mark.django_db
def test_reinvoke():
    class MyTable(Table):
        class Meta:
            auto__model = TFoo

    class MyPage(Page):
        my_table = MyTable(columns__a__filter__include=True)

    assert 'a' in MyPage().bind(request=req('get')).parts.my_table.query.filters
    assert (
        'a'
        not in MyPage(parts__my_table__columns__a__filter__include=False)
        .bind(request=req('get'))
        .parts.my_table.query.filters
    )


@pytest.mark.django_db
def test_reinvoke_2():
    class MyTable(Table):
        class Meta:
            auto__model = TFoo
            columns__a__filter__include = True

    assert 'a' in MyTable().bind(request=req('get')).query.filters

    class MyPage(Page):
        my_table = MyTable()

        class Meta:
            parts__my_table__columns__a__filter__include = False

    assert 'a' not in MyPage().bind(request=req('get')).parts.my_table.query.filters
    assert (
        'a'
        in MyPage(parts__my_table__columns__a__filter__include=True)
        .bind(request=req('get'))
        .parts.my_table.query.filters
    )


def test_cell_value_is_none_if_attr_is_none():
    class MyTable(Table):
        foo = Column(attr=None)

    rows = [11]  # this would blow up if we tried to access pretty much any attribute from it

    t = MyTable(rows=rows).bind(request=req('get'))
    bound_rows = list(t.cells_for_rows())
    assert len(bound_rows) == 1
    cells = bound_rows[0]
    assert cells['foo'].value is None

    # Check some random stuff on Cells, Cell and ColumnHeader for coverage
    assert cells.__html__() == str(cells)
    cell = cells['foo']
    assert cell.iommi_evaluate_parameters() is cell._evaluate_parameters
    assert cell.get_request() is cells.get_request()
    assert cell.get_context() == cells.get_context()
    assert repr(cell) == '<Cell column=<iommi.table.Column foo> row=11>'
    assert repr(t.header_levels[0][0]) == '<Header: foo>'


@pytest.mark.django_db
def test_automatic_url():
    foo = AutomaticUrl.objects.create(a=7)
    AutomaticUrl2.objects.create(foo=foo)

    t = Table(auto__model=AutomaticUrl2).bind(request=req('get'))
    bound_rows = list(t.cells_for_rows())
    assert len(bound_rows) == 1
    cells = bound_rows[0]
    assert cells['foo'].__html__() == '<td><a href="url here!">the str of AutomaticUrl</a></td>'


def test_icon_value():
    class TestTable(Table):
        foo = Column.icon(
            extra__icon='foo',
            cell__value=lambda row, **_: row.foo,
        )
        bar = Column.icon(
            display_name='bar',
            cell__value=lambda row, **_: row.foo,
        )

    rows = [
        Struct(foo=False),
        Struct(foo=True),
    ]

    verify_table_html(
        table=TestTable(rows=rows),
        find=dict(name='tbody'),
        expected_html="""
            <tbody>
                <tr>
                    <td> </td>
                    <td> </td>
                </tr>
                <tr>
                    <td>
                        <i class="fa fa-foo fa-lg">
                    </td>
                    <td>
                        bar
                    </td>
                </tr>
            </tbody>
        """,
    )


@pytest.mark.django_db
def test_no_dispatch_parameter_in_sorting_or_pagination_links():
    for x in range(4):
        TFoo(a=x, b="foo").save()

    class TestTable(Table):
        a = Column.number()

    verify_table_html(
        find=dict(class_='iommi-table-plus-paginator'),
        table=TestTable(rows=TFoo.objects.all().order_by('pk')),
        query={'page_size': 2, 'page': 1, 'query': 'b="foo"'},
        expected_html="""
<div class="iommi-table-plus-paginator">
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
        <thead>
            <tr>
                <th class="first_column subheader">
                    <a href="?page_size=2&amp;page=1&amp;query=b%3D%22foo%22&amp;order=a">
                        A
                    </a>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr data-pk="1">
                <td class="rj">
                    0
                </td>
            </tr>
            <tr data-pk="2">
                <td class="rj">
                    1
                </td>
            </tr>
        </tbody>
    </table>
    <nav aria-label="Pages">
        <ul>
            <li>
                <a aria-label="Page 1" href="?page_size=2&amp;query=b%3D%22foo%22&amp;page=1">
                    1
                </a>
            </li>
            <li>
                <a aria-label="Page 2" href="?page_size=2&amp;query=b%3D%22foo%22&amp;page=2">
                    2
                </a>
            </li>
            <li>
                <a aria-label="Next Page" href="?page_size=2&amp;query=b%3D%22foo%22&amp;page=2">
                    &gt;
                </a>
            </li>
        </ul>
    </nav>
</div>
        """,
    )

    verify_table_html(
        find=dict(class_='iommi-table-plus-paginator'),
        table=TestTable(rows=TFoo.objects.all().order_by('pk')),
        query={'page_size': 2, 'page': 1, 'query': 'b="foo"', '/tbody': ''},
        expected_html="""
<div class="iommi-table-plus-paginator">
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
        <thead>
            <tr>
                <th class="first_column subheader">
                    <a href="?page_size=2&amp;page=1&amp;query=b%3D%22foo%22&amp;order=a">
                        A
                    </a>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr data-pk="1">
                <td class="rj">
                    0
                </td>
            </tr>
            <tr data-pk="2">
                <td class="rj">
                    1
                </td>
            </tr>
        </tbody>
    </table>
    <nav aria-label="Pages">
        <ul>
            <li>
                <a aria-label="Page 1" href="?page_size=2&amp;query=b%3D%22foo%22&amp;page=1">
                    1
                </a>
            </li>
            <li>
                <a aria-label="Page 2" href="?page_size=2&amp;query=b%3D%22foo%22&amp;page=2">
                    2
                </a>
            </li>
            <li>
                <a aria-label="Next Page" href="?page_size=2&amp;query=b%3D%22foo%22&amp;page=2">
                    &gt;
                </a>
            </li>
        </ul>
    </nav>
</div>
""",
    )


@pytest.mark.django_db
def test_evil_names():
    from tests.models import EvilNames

    Table(auto__model=EvilNames)


def test_sort_list():
    class TestTable(Table):
        foo = Column()
        bar = Column.number(sort_key='bar')

    rows = [
        Struct(foo='c', bar=3),
        Struct(foo='b', bar=2),
        Struct(foo='a', bar=1),
    ]

    verify_table_html(
        table=TestTable(rows=rows),
        query=dict(order='bar'),
        expected_html="""\
      <table class="table" data-endpoint="/tbody" data-iommi-id="">
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="ascending first_column sorted subheader">
              <a href="?order=-bar"> Bar </a>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td> a </td>
            <td class="rj"> 1 </td>
          </tr>
          <tr>
            <td> b </td>
            <td class="rj"> 2 </td>
          </tr>
          <tr>
            <td> c </td>
            <td class="rj"> 3 </td>
          </tr>
        </tbody>
      </table>
    """,
    )

    # now reversed
    verify_table_html(
        table=TestTable(rows=rows),
        query=dict(order='-bar'),
        expected_html="""\
      <table class="table" data-endpoint="/tbody" data-iommi-id="">
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="descending first_column sorted subheader">
              <a href="?order=bar"> Bar </a>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td> c </td>
            <td class="rj"> 3 </td>
          </tr>
          <tr>
            <td> b </td>
            <td class="rj"> 2 </td>
          </tr>
          <tr>
            <td> a </td>
            <td class="rj"> 1 </td>
          </tr>
        </tbody>
      </table>
    """,
    )


def test_sort_with_name():
    class TestTable(Table):
        class Meta:
            _name = 'my_table'

        foo = Column()
        bar = Column.number(sort_key='bar')

    rows = [
        Struct(foo='c', bar=3),
        Struct(foo='b', bar=2),
        Struct(foo='a', bar=1),
    ]

    table = TestTable(rows=rows)
    verify_table_html(
        table=table,
        query={'order': 'bar'},
        expected_html="""\
      <table class="table" data-endpoint="/tbody" data-iommi-id="">
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="ascending first_column sorted subheader">
              <a href="?order=-bar"> Bar </a>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td> a </td>
            <td class="rj"> 1 </td>
          </tr>
          <tr>
            <td> b </td>
            <td class="rj"> 2 </td>
          </tr>
          <tr>
            <td> c </td>
            <td class="rj"> 3 </td>
          </tr>
        </tbody>
      </table>
    """,
    )


def test_sort_list_with_none_values():
    class TestTable(Table):
        foo = Column()
        bar = Column.number(sort_key='bar')

    rows = [
        Struct(foo='c', bar=3),
        Struct(foo='b', bar=2),
        Struct(foo='a', bar=None),
        Struct(foo='a', bar=None),
    ]

    verify_table_html(
        table=TestTable(rows=rows),
        query=dict(order='bar'),
        expected_html="""\
      <table class="table" data-endpoint="/tbody" data-iommi-id="">
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="ascending first_column sorted subheader">
              <a href="?order=-bar"> Bar </a>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td> a </td>
            <td class="rj">  </td>
          </tr>
          <tr>
            <td> a </td>
            <td class="rj">  </td>
          </tr>
          <tr>
            <td> b </td>
            <td class="rj"> 2 </td>
          </tr>
          <tr>
            <td> c </td>
            <td class="rj"> 3 </td>
          </tr>
        </tbody>
      </table>
    """,
    )


def test_sort_list_bad_parameter():
    class TestTable(Table):
        foo = Column()
        bar = Column.number(sort_key='bar')

    rows = [
        Struct(foo='b', bar=2),
        Struct(foo='a', bar=1),
    ]

    verify_table_html(
        table=TestTable(rows=rows),
        query=dict(order='barfology'),
        expected_html="""\
      <table class="table" data-endpoint="/tbody" data-iommi-id="">
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
            <td> b </td>
            <td class="rj"> 2 </td>
          </tr>
          <tr>
            <td> a </td>
            <td class="rj"> 1 </td>
          </tr>
        </tbody>
      </table>
    """,
    )


@pytest.mark.django_db
def test_sort_django_table():

    TFoo(a=4711, b="c").save()
    TFoo(a=17, b="a").save()
    TFoo(a=42, b="b").save()

    class TestTable(Table):
        a = Column.number()
        b = Column()

    verify_table_html(
        table=TestTable(rows=TFoo.objects.all()),
        query=dict(order='a'),
        expected_html="""\
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
      <thead>
        <tr>
          <th class="ascending first_column sorted subheader">
            <a href="?order=-a"> A </a>
          </th>
          <th class="first_column subheader">
            <a href="?order=b"> B </a>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr data-pk="2">
          <td class="rj"> 17 </td>
          <td> a </td>
        </tr>
        <tr data-pk="3">
          <td class="rj"> 42 </td>
          <td> b </td>
        </tr>
        <tr data-pk="1">
          <td class="rj"> 4711 </td>
          <td> c </td>
        </tr>
      </tbody>
    </table>
    """,
    )

    # now reversed
    verify_table_html(
        table=TestTable(rows=TFoo.objects.all()),
        query=dict(order='-a'),
        expected_html="""\
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
      <thead>
        <tr>
          <th class="descending first_column sorted subheader">
            <a href="?order=a"> A </a>
          </th>
          <th class="first_column subheader">
            <a href="?order=b"> B </a>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr data-pk="1">
          <td class="rj"> 4711 </td>
          <td> c </td>
        </tr>
        <tr data-pk="3">
          <td class="rj"> 42 </td>
          <td> b </td>
        </tr>
        <tr data-pk="2">
          <td class="rj"> 17 </td>
          <td> a </td>
        </tr>
      </tbody>
    </table>
    """,
    )


def test_order_by_on_list_nested():
    rows = [
        Struct(foo=Struct(bar='c')),
        Struct(foo=Struct(bar='b')),
        Struct(foo=Struct(bar='a')),
    ]

    sorted_rows = ordered_by_on_list(rows, 'foo__bar')
    assert sorted_rows == list(reversed(rows))

    sorted_rows = ordered_by_on_list(rows, lambda x: x.foo.bar)
    assert sorted_rows == list(reversed(rows))


def test_sort_default_desc_no_sort():
    class TestTable(Table):
        foo = Column()
        bar = Column(sort_default_desc=True)

    verify_table_html(
        table=TestTable(rows=[]),
        query=dict(),
        find=dict(name='thead'),
        expected_html="""\
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="first_column subheader">
              <a href="?order=-bar"> Bar </a>
            </th>
        </thead>
    """,
    )


def test_sort_default_desc_other_col_sorted():
    class TestTable(Table):
        foo = Column()
        bar = Column(sort_default_desc=True)

    verify_table_html(
        table=TestTable(rows=[]),
        query=dict(order='foo'),
        find=dict(name='thead'),
        expected_html="""\
        <thead>
          <tr>
            <th class="ascending first_column sorted subheader">
              <a href="?order=-foo"> Foo </a>
            </th>
            <th class="first_column subheader">
              <a href="?order=-bar"> Bar </a>
            </th>
        </thead>
    """,
    )


def test_sort_default_desc_already_sorted():
    class TestTable(Table):
        foo = Column()
        bar = Column(sort_default_desc=True)

    verify_table_html(
        table=TestTable(rows=[]),
        query=dict(order='bar'),
        find=dict(name='thead'),
        expected_html="""\
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="ascending first_column sorted subheader">
              <a href="?order=-bar"> Bar </a>
            </th>
        </thead>
    """,
    )


@pytest.mark.django_db
def test_sort_django_table_from_model():

    TFoo(a=4711, b="c").save()
    TFoo(a=17, b="a").save()
    TFoo(a=42, b="b").save()

    verify_table_html(
        table__auto__rows=TFoo.objects.all(),
        query=dict(order='a'),
        expected_html="""\
    <table class="table" data-endpoint="/tbody" data-iommi-id="">
      <thead>
        <tr>
          <th class="ascending first_column sorted subheader">
            <a href="?order=-a"> A </a>
          </th>
          <th class="first_column subheader">
            <a href="?order=b"> B </a>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr data-pk="2">
          <td class="rj"> 17 </td>
          <td> a </td>
        </tr>
        <tr data-pk="3">
          <td class="rj"> 42 </td>
          <td> b </td>
        </tr>
        <tr data-pk="1">
          <td class="rj"> 4711 </td>
          <td> c </td>
        </tr>
      </tbody>
    </table>
    """,
    )


@pytest.mark.django_db
def test_default_sort_key_on_foreign_key():
    table = Table(auto__model=SortKeyOnForeignKeyB).bind(request=req('get'))
    assert table.columns.remote.sort_key == 'remote__name'


def test_title_default_to_none():
    table = Table(rows=[]).bind(request=req('get'))
    assert table.title is None

    assert 'None' not in str(table)


@pytest.mark.skip('This assert is broken currently, due to value_to_q being a function by default which is truthy')
@pytest.mark.django_db
def test_error_when_inserting_field_into_query_form_with_no_attr():  # pragma: no cover
    with pytest.raises(AssertionError):
        Table(
            auto__model=TFoo,
            auto__include=[],
            query__filters__not_in_t_foo=Filter.choice(attr=None, choices=['Foo', 'Track']),
        ).bind(request=req('get'))


@pytest.mark.django_db
def test_inserting_field_into_query_form_with_no_attr_and_bypassing_check():
    # Does not raise
    Table(
        auto__model=TFoo,
        auto__include=[],
        query__filters__not_in_t_foo=Filter.choice(
            attr=None,
            choices=['Foo', 'Track'],
            is_valid_filter=lambda **_: (True, ''),
        ),
    ).bind(request=req('get'))


@pytest.mark.django_db
def test_insert_into_query_form_bypassing_query():
    t = Table(
        auto__model=TFoo,
        auto__include=[],
        query__form__fields__not_in_t_foo=Field.choice(choices=['Foo', 'Track']),
    ).bind(request=req('get'))

    assert 'not_in_t_foo' in keys(t.query.form.fields)


@pytest.mark.django_db
def test_insert_field_into_query_form():
    table = Table(
        auto__model=TFoo,
        query__form__fields__not_in_t_foo=Field.choice(choices=['Foo', 'Track']),
    ).bind(request=req('get'))

    assert 'not_in_t_foo' in keys(table.query.form.fields)


@pytest.mark.django_db
def test_auto_model_dunder_path():
    tfoo = TFoo.objects.create(a=1, b='2')
    tbar = TBar.objects.create(foo=tfoo, c=True)
    TBar2.objects.create(bar=tbar)

    table = Table(
        auto__model=TBar2,
        auto__include=['bar__foo'],
        # columns__bar_foo__bulk__include=True,
    ).bind(request=req('get'))

    assert 'bar_foo' in keys(table.columns)
    table.__html__()


@pytest.mark.django_db
def test_invalid_form_message():
    invalid_form_message = 'Seventh Star'
    t = Table(auto__model=TBar, columns__foo__filter__include=True, invalid_form_message=invalid_form_message,).bind(
        request=req('get', foo=11)
    )  # 11 isn't in valid choices!
    assert invalid_form_message in t.__html__()


@pytest.mark.django_db
def test_empty_message():
    empty_message = 'Destruction of the empty spaces was my one and only crime'
    t = Table(
        auto__model=TBar,
        columns__foo__filter__include=True,
        empty_message=empty_message,
    ).bind(request=req('get'))
    assert empty_message in t.__html__()


@pytest.mark.django_db
def test_column_include_false_excludes_bulk_and_filter():
    class MyTable(Table):
        foo = Column(
            include=lambda **_: False,
            filter__include=True,
            bulk__include=True,
        )

        c = Column(
            filter__include=True,
            bulk__include=True,
        )

        class Meta:
            model = TBar

    t = MyTable().bind(request=req('get'))

    assert 'foo' not in t.columns
    assert set(t.query.filters.keys()) == {'c'}
    assert set(t.query.form.fields.keys()) == {'c'}
    assert set(t.bulk.fields.keys()) == {'_all_pks_', 'c'}


@pytest.mark.django_db
def test_auto_model_include_pk():
    t = Table(
        auto__model=TBar,
        auto__include=['pk'],
    ).bind(request=req('get'))
    assert 'pk' in t.columns


def test_h_tag():
    class TestTable(Table):
        foo = Column()

    rows = [
        Struct(foo=False),
    ]

    verify_table_html(
        table=TestTable(rows=rows, h_tag=html.h1('foo', attrs__class__foo=True)),
        find=dict(name='h1'),
        expected_html="""
            <h1 class="foo">foo</h1>
        """,
    )

    verify_table_html(
        table=TestTable(rows=rows, title='bar', h_tag__attrs__class__bar=True),
        find=dict(name='h1'),
        expected_html="""
            <h1 class="bar">Bar</h1>
        """,
    )


@pytest.mark.django_db
def test_bulk_no_actions_makes_bulk_form_none():
    # normal case
    assert Table(auto__model=TFoo, columns__a__bulk__include=True).bind(request=req('get')).bulk is not None
    # the thing we want to test
    assert (
        Table(auto__model=TFoo, columns__a__bulk__include=True, bulk__actions__submit__include=False)
        .bind(request=req('get'))
        .bulk
        is None
    )


@pytest.mark.django_db
def test_lazy_rows(settings):
    settings.DEBUG = True
    set_sql_debug(SQL_DEBUG_LEVEL_ALL)
    q = TBar.objects.all()
    choices = [1, 2, 3]
    t = Table(
        model=TBar,
        rows=lambda **_: q,
        columns__foo=Column.choice(
            choices=choices,
            filter__include=True,
        ),
    ).bind()
    assert t.query.form.fields.foo.choices == choices
    assert q._result_cache is None, "No peeking!"


@pytest.mark.django_db
def test_lazy_paginator(settings):
    settings.DEBUG = True
    set_sql_debug(SQL_DEBUG_LEVEL_ALL)
    q = TBar.objects.all()
    choices = [1, 2, 3]
    t = Table(
        model=TBar,
        rows=lambda **_: q,
        columns__foo=Column.choice(
            choices=choices,
            filter__include=True,
        ),
    ).bind(request=req('get'))
    assert t.query.form.fields.foo.choices == choices
    assert 'page' not in t._bound_members.parts._bound_members, "No peeking!"
    t.__html__()
    assert t.visible_rows is not None
    assert 'page' in t._bound_members.parts._bound_members, "Did you not peek?"


@pytest.mark.django_db
def test_rows_should_not_cache():
    q = TBar.objects.all()
    assert q._result_cache is None, "Cache should be empty"
    Table(
        model=TBar,
        rows=lambda **_: q,
    ).bind(request=req('get')).render_to_response()
    assert q._result_cache is None, "Cache should be empty"


@pytest.mark.django_db
def test_auto_model_for_textchoices():
    class TestTable(Table):
        class Meta:
            auto__model = ChoicesModel

    verify_table_html(table=TestTable(rows=[]), find=dict(name='tbody'), expected_html="""<tbody></tbody>""")


@pytest.mark.skipif(not django.VERSION[:2] >= (3, 0), reason='Requires django 3.0+')
@pytest.mark.django_db
def test_auto_model_for_textchoices_with_choices_class():
    from tests.models import ChoicesClassModel

    class TestTable(Table):
        class Meta:
            auto__model = ChoicesClassModel

    verify_table_html(table=TestTable(rows=[]), find=dict(name='tbody'), expected_html="""<tbody></tbody>""")


@pytest.mark.django_db
def test_table_foreign_key_column_name():
    t = Table(
        auto__model=TBar,
        auto__include=['foo'],
    ).bind(request=req('get'))
    assert t.columns.foo.display_name == 'Foo'


def test_filter_model_mixup():
    t = Table(auto__model=TBar, page_size=None).bind(request=req('get'))
    assert t.columns.foo.model == TFoo


@pytest.mark.django_db
def test_nest_table_inside_form_does_not_crash_due_to_nested_forms():
    # This used to crash
    Form(
        auto__instance=TFoo(),
        fields__a_table=Table(auto__model=TFoo)
    ).bind(request=req('get'))

