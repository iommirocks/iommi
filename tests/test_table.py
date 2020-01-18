import json
from collections import defaultdict

import django
import pytest
from django.db.models import QuerySet
from django.http import HttpResponse
from django.template import Template
from django.test import override_settings
from django.utils.safestring import mark_safe
from iommi.base import (
    InvalidEndpointPathException,
    find_target,
)
from iommi.form import (
    Action,
    Field,
    Form,
)
from iommi.base import perform_ajax_dispatch
from iommi.query import (
    Query,
    Variable,
)
from iommi.table import (
    Column,
    SELECT_DISPLAY_NAME,
    Struct,
    Table,
    register_cell_formatter,
    yes_no_formatter,
)
from tri_declarative import (
    Namespace,
    class_shortcut,
    getattr_path,
)

from tests.helpers import (
    req,
    request_with_middleware,
    verify_table_html,
)
from tests.models import (
    FromModelWithInheritanceTest,
    TBar,
    TBaz,
    TFoo,
)


def get_rows():
    return [
        Struct(foo="Hello", bar=17),
        Struct(foo="<evil/> &", bar=42)
    ]


def explicit_table():

    columns = [
        Column(name="foo"),
        Column.number(name="bar"),
    ]

    return Table(rows=get_rows(), columns=columns, attrs__class__another_class=True, attrs__id='table_id')


def declarative_table():

    class TestTable(Table):

        class Meta:
            attrs__class__another_class = lambda table: True
            attrs__id = lambda table: 'table_id'

        foo = Column()
        bar = Column.number()

    return TestTable(rows=get_rows())


@pytest.mark.parametrize('table', [
    explicit_table(),
    declarative_table()
])
def test_render_impl(table):

    verify_table_html(table=table, expected_html="""
        <table class="another_class listview" data-endpoint="/tbody" id="table_id">
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
            columns = [Column(name='foo')]

        bar = Column()

    assert {'foo', 'bar'} == {column.name for column in MyTable(rows=[]).columns}


def test_kwarg_column_config_injection():
    class MyTable(Table):
        foo = Column()

    table = MyTable(rows=[], column__foo__extra__stuff="baz")
    table.bind(request=None)
    assert 'baz' == table.bound_column_by_name['foo'].extra.stuff


def test_bad_arg():
    with pytest.raises(TypeError) as e:
        Table(rows=[], columns=[Column()], foo=None)
    assert 'foo' in str(e.value)


def test_column_ordering():

    class MyTable(Table):
        foo = Column(after='bar')
        bar = Column()

    assert ['bar', 'foo'] == [column.name for column in MyTable(rows=[]).columns]


def test_column_with_meta():
    class MyColumn(Column):
        class Meta:
            sortable = False

    class MyTable(Table):
        foo = MyColumn()
        bar = MyColumn.icon('history')

    table = MyTable(rows=[])
    table.bind(request=None)
    assert not table.bound_column_by_name['foo'].sortable
    assert not table.bound_column_by_name['bar'].sortable


@pytest.mark.django_db
def test_django_table():

    f1 = TFoo.objects.create(a=17, b="Hej")
    f2 = TFoo.objects.create(a=42, b="Hopp")

    TBar(foo=f1, c=True).save()
    TBar(foo=f2, c=False).save()

    class TestTable(Table):
        foo__a = Column.number()
        foo__b = Column()
        foo = Column.choice_queryset(model=TFoo, choices=lambda table, **_: TFoo.objects.all(), query__show=True, bulk__show=True, query__gui__show=True)

    t = TestTable(rows=TBar.objects.all().order_by('pk'))
    t.bind(request=req('get'))

    assert list(t.bound_column_by_name['foo'].choices) == list(TFoo.objects.all())

    assert t.bulk_form._is_bound
    assert list(t.bulk_form.fields_by_name['foo'].choices) == list(TFoo.objects.all())

    assert t.query_form._is_bound
    assert list(t.query_form.fields_by_name['foo'].choices) == list(TFoo.objects.all())

    verify_table_html(table=t, expected_html="""
        <table class="listview" data-endpoint="/tbody">
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

    t = TestTable(rows=[])
    assert [c.name for c in t.columns] == ['foo', 'bar', 'another']


def test_output():

    is_report = False

    class TestTable(Table):

        class Meta:
            attrs__class__listview = True
            attrs__id = 'table_id'

        foo = Column()
        bar = Column.number()
        icon = Column.icon('history', is_report, group="group")
        edit = Column.edit(is_report, group="group")
        delete = Column.delete(is_report)

    rows = [
        Struct(foo="Hello räksmörgås ><&>",
               bar=17,
               get_absolute_url=lambda: '/somewhere/'),
    ]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="listview" data-endpoint="/tbody" id="table_id">
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
                    <th class="first_column subheader thin"> </th>
                    <th class="subheader thin" title="Edit"> </th>
                    <th class="first_column subheader thin" title="Delete"> </th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td> Hello räksmörgås &gt;&lt;&amp;&gt; </td>
                    <td class="rj"> 17 </td>
                    <td class="cj"> <i class="fa fa-lg fa-history"> </i> </td>
                    <td class="cj"> <a href="/somewhere/edit/"> <i class="fa fa-lg fa-pencil-square-o" title="Edit"> </i> </a> </td>
                    <td class="cj"> <a href="/somewhere/delete/"> <i class="fa fa-lg fa-trash-o" title="Delete"> </i> </a> </td>
                </tr>
            </tbody>
        </table>
        """)


def test_name_traversal():
    class TestTable(Table):
        foo__bar = Column(sortable=False)

    rows = [Struct(foo=Struct(bar="bar"))]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="listview" data-endpoint="/tbody">
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
#         <table class="listview" data-endpoint="/tbody">
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
#         <table class="listview" data-endpoint="/tbody">
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


class NoSortTable(Table):
    class Meta:
        sortable = False


def test_display_name():
    class TestTable(NoSortTable):
        foo = Column(display_name="Bar")

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="listview" data-endpoint="/tbody">
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


def test_link():
    class TestTable(NoSortTable):
        foo = Column.link(cell__url='https://whereever', cell__url_title="whatever")
        bar = Column.link(cell__value='bar', cell__url_title=lambda **_: "url_title_goes_here")

    rows = [Struct(foo='foo', bar=Struct(get_absolute_url=lambda: '/get/absolute/url/result'))]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="listview" data-endpoint="/tbody">
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


def test_css_class():
    class TestTable(NoSortTable):
        foo = Column(
            header__attrs__class__some_class=True,
            cell__attrs__class__bar=True
        )

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
    <table class="listview" data-endpoint="/tbody">
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


def test_header_url():
    class TestTable(NoSortTable):
        foo = Column(url="/some/url")

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
    <table class="listview" data-endpoint="/tbody">
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


def test_show():
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column(show=False)

    rows = [Struct(foo="foo", bar="bar")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
    <table class="listview" data-endpoint="/tbody">
        <thead>
            <tr><th class="first_column subheader"> Foo </th></tr>
        </thead>
        <tbody>
            <tr>
                <td> foo </td>
            </tr>
        </tbody>
    </table>""")


def test_show_lambda():
    def show_callable(table, column):
        assert isinstance(table, TestTable)
        assert column.name == 'bar'
        return False

    class TestTable(NoSortTable):
        foo = Column()
        bar = Column.icon('foo', show=show_callable)

    rows = [Struct(foo="foo", bar="bar")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
    <table class="listview" data-endpoint="/tbody">
        <thead>
            <tr><th class="first_column subheader"> Foo </th></tr>
        </thead>
        <tbody>
            <tr>
                <td> foo </td>
            </tr>
        </tbody>
    </table>""")


def test_attr():
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column(attr='foo')

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
    <table class="listview" data-endpoint="/tbody">
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


def test_attrs():
    class TestTable(NoSortTable):
        class Meta:
            attrs__class__classy = True
            attrs__foo = lambda table: 'bar'
            row__attrs__class__classier = True
            row__attrs__foo = lambda table, row, **_: "barier"

        yada = Column()

    verify_table_html(table=TestTable(rows=[Struct(yada=1), Struct(yada=2)]), expected_html="""
        <table class="classy listview" data-endpoint="/tbody" foo="bar">
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


def test_attrs_new_syntax():
    class TestTable(NoSortTable):
        class Meta:
            attrs__class__classy = True
            attrs__foo = lambda table: 'bar'

            row__attrs__class__classier = True
            row__attrs__foo = lambda table: "barier"

        yada = Column()

    verify_table_html(table=TestTable(rows=[Struct(yada=1), Struct(yada=2)]), expected_html="""
        <table class="classy listview" data-endpoint="/tbody" foo="bar">
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


def test_column_presets():
    is_report = False

    class TestTable(NoSortTable):
        icon = Column.icon(is_report)
        edit = Column.edit(is_report)
        delete = Column.delete(is_report)
        download = Column.download(is_report)
        run = Column.run(is_report)
        select = Column.select(is_report)
        boolean = Column.boolean(is_report)
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
        <table class="listview" data-endpoint="/tbody">
            <thead>
                <tr>
                    <th class="first_column subheader thin" />
                    <th class="first_column subheader thin" title="Edit" />
                    <th class="first_column subheader thin" title="Delete" />
                    <th class="first_column subheader thin" title="Download" />
                    <th class="first_column subheader thin" title="Run"> Run </th>
                    <th class="first_column nopad subheader thin" title="Select all">
                        {}
                    </th>
                    <th class="first_column subheader"> Boolean </th>
                    <th class="first_column subheader"> Link </th>
                    <th class="first_column subheader"> Number </th>
                </tr>
            </thead>
            <tbody>
                <tr data-pk="123">
                    <td class="cj"> <i class="fa fa-lg fa-False" /> </td>
                    <td class="cj"> <a href="http://yada/edit/"> <i class="fa fa-lg fa-pencil-square-o" title="Edit" /> </a> </td>
                    <td class="cj"> <a href="http://yada/delete/"> <i class="fa fa-lg fa-trash-o" title="Delete" /> </a> </td>
                    <td class="cj"> <a href="http://yada/download/"> <i class="fa fa-lg fa-download" title="Download" /> </a> </td>
                    <td> <a href="http://yada/run/"> Run </a> </td>
                    <td class="cj"> <input class="checkbox" name="pk_123" type="checkbox"/> </td> <td class="cj"> <i class="fa fa-check" title="Yes" /> </td>
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
        b = Column(show=False)  # should still be able to filter on this though!

    verify_table_html(table=TestTable(rows=TFoo.objects.all().order_by('pk')),
                      query=dict(page_size=2, page=2, query='b="foo"'),
                      expected_html="""
        <table class="listview" data-endpoint="/tbody">
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
        b = Column(show=False)  # should still be able to filter on this though!

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
        <table class="listview" data-endpoint="/tbody">
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


def test_actions():
    class TestTable(NoSortTable):
        foo = Column(header__attrs__title="Some title")

        class Meta:
            action = dict(
                a=Action(display_name='Foo', attrs__href='/foo/', show=lambda table, **_: table.rows is not rows),
                b=Action(display_name='Bar', attrs__href='/bar/', show=lambda table, **_: table.rows is rows),
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
        a = Column.integer(sortable=False, bulk__show=True)  # turn off sorting to not get the link with random query params
        b = Column(bulk__show=True)

    result = TestTable(
        rows=TFoo.objects.all(),
        request=req('get', pk_1='', pk_2='', a='0', b='changed'),
    ).render()
    assert '<form method="post" action=".">' in result
    assert '<input type="submit" class="button" value="Bulk change"/>' in result

    def post_bulk_edit(table, queryset, updates, **_):
        assert isinstance(table, TestTable)
        assert isinstance(queryset, QuerySet)
        assert {x.pk for x in queryset} == {1, 2}
        assert updates == dict(a=0, b='changed')

    t = TestTable(
        rows=TFoo.objects.all().order_by('pk'),
        post_bulk_edit=post_bulk_edit,
        request=req('post', pk_1='', pk_2='', **{'bulk/a': '0', 'bulk/b': 'changed'}),
    )
    assert t._is_bound
    assert t.bulk_form.name == 'bulk'
    t.render()

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
    ).render()
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
        request=req('post', _all_pks_='1', **{'bulk/a': '11', 'bulk/b': 'changed2'}),
    ).render()

    assert [(x.pk, x.a, x.b) for x in TFoo.objects.all()] == [
        (1, 11, u'changed2'),
        (2, 11, u'changed2'),
        (3, 11, u'changed2'),
        (4, 11, u'changed2'),
    ]


@pytest.mark.django_db
def test_query():
    assert TFoo.objects.all().count() == 0

    TFoo(a=1, b="foo").save()
    TFoo(a=2, b="foo").save()
    TFoo(a=3, b="bar").save()
    TFoo(a=4, b="bar").save()

    class TestTable(Table):
        a = Column.number(sortable=False, query__show=True, query__gui__show=True)  # turn off sorting to not get the link with random query params
        b = Column.substring(query__show=True, query__gui__show=True)

        class Meta:
            sortable = False

    verify_table_html(query=dict(query='asdasdsasd'), table=TestTable(rows=TFoo.objects.all().order_by('pk')), find=dict(id='iommi_query_error'), expected_html='<div id="iommi_query_error">Invalid syntax for query</div>')

    verify_table_html(query=dict(a='1'), table=TestTable(rows=TFoo.objects.all().order_by('pk')), find=dict(name='tbody'), expected_html="""
    <tbody>
        <tr data-pk="1">
            <td class="rj">
                1
            </td>
            <td>
                foo
            </td>
        </tr>
    </table>""")
    verify_table_html(query=dict(b='bar'), table=TestTable(rows=TFoo.objects.all().order_by('pk')), find=dict(name='tbody'), expected_html="""
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
    </tbody>""")
    verify_table_html(query=dict(query='b="bar"'), table=TestTable(rows=TFoo.objects.all().order_by('pk')), find=dict(name='tbody'), expected_html="""
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
    </tbody>""")
    verify_table_html(query=dict(b='fo'), table=TestTable(rows=TFoo.objects.all().order_by('pk')), find=dict(name='tbody'), expected_html="""
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
    </table>""")


def test_cell_template():
    def explode(**_):
        assert False

    class TestTable(NoSortTable):
        foo = Column(cell__template='test_cell_template.html', cell__format=explode, cell__url=explode, cell__url_title=explode)

    rows = [Struct(foo="sentinel")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="listview" data-endpoint="/tbody">
            <thead>
                <tr><th class="first_column subheader"> Foo </th></tr>
            </thead>
            <tbody>
                <tr>
                    Custom rendered: sentinel
                </tr>
            </tbody>
        </table>""")


def test_cell_format_escape():

    class TestTable(NoSortTable):
        foo = Column(cell__format=lambda value, **_: '<foo>')

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
            <table class="listview" data-endpoint="/tbody">
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


def test_cell_format_no_escape():

    class TestTable(NoSortTable):
        foo = Column(cell__format=lambda value, **_: mark_safe('<foo/>'))

    rows = [Struct(foo="foo")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
            <table class="listview" data-endpoint="/tbody">
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
def test_template_string():

    TFoo.objects.create(a=1)

    def explode(**_):
        assert False

    class TestTable(NoSortTable):
        class Meta:
            model = TFoo
            actions_template = Template('What links')
            header__template = Template('What headers')
            filter__template = Template('What filters')

            row__template = Template('Oh, rows: {{ bound_row.render_cells }}')

        a = Column(
            cell__template=Template('Custom cell: {{ row.a }}'),
            cell__format=explode,
            cell__url=explode,
            cell__url_title=explode,
            query__show=True,
            query__gui__show=True,
        )

    verify_table_html(
        table=TestTable(
            action__foo=Action(display_name='foo', attrs__href='bar'),
        ),
        expected_html="""
        What filters
        <div class="table-container">
            <form action="." method="post">
                <table class="listview" data-endpoint="/tbody">
                    What headers
                    <tbody>
                        Oh, rows: Custom cell: 1
                    </tbody>
                </table>
                What links
            </form>
        </div>""")


def test_cell_template_string():
    def explode(**_):
        assert False

    class TestTable(NoSortTable):
        foo = Column(
            cell__template=Template('Custom renderedXXXX: {{ row.foo }}'),
            cell__format=explode,
            cell__url=explode,
            cell__url_title=explode,
        )

    rows = [Struct(foo="sentinel")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="listview" data-endpoint="/tbody">
            <thead>
                <tr><th class="first_column subheader"> Foo </th></tr>
            </thead>
            <tbody>
                <tr>
                    Custom renderedXXXX: sentinel
                </tr>
            </tbody>
        </table>""")


def test_no_header_template():
    class TestTable(NoSortTable):
        class Meta:
            header__template = None

        foo = Column()

    rows = [Struct(foo="bar")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="listview" data-endpoint="/tbody">
            <tbody>
                <tr>
                    <td>
                        bar
                    </td>
                </tr>
            </tbody>
        </table>""")


def test_row_template():
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column()

        class Meta:
            row__template = lambda table: 'test_table_row.html'

    rows = [Struct(foo="sentinel", bar="schmentinel")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="listview" data-endpoint="/tbody">
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


def test_cell_lambda():
    class TestTable(NoSortTable):
        sentinel1 = 'sentinel1'

        sentinel2 = Column(cell__value=lambda table, bound_column, row, **_: '%s %s %s' % (table.sentinel1, bound_column.name, row.sentinel3))

    rows = [Struct(sentinel3="sentinel3")]

    verify_table_html(table=TestTable(rows=rows), expected_html="""
        <table class="listview" data-endpoint="/tbody">
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


def test_auto_rowspan_and_render_twice():
    class TestTable(NoSortTable):
        foo = Column(auto_rowspan=True)

    rows = [
        Struct(foo=1),
        Struct(foo=1),
        Struct(foo=2),
        Struct(foo=2),
    ]

    expected = """
        <table class="listview" data-endpoint="/tbody">
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
    verify_table_html(table=t, expected_html=expected)
    verify_table_html(table=t, expected_html=expected)


def test_render_table():
    class TestTable(NoSortTable):
        foo = Column(display_name="TBar")

    rows = [Struct(foo="foo")]

    response = TestTable(rows=rows).bind(request=req('get')).render_to_response()
    assert isinstance(response, HttpResponse)
    assert b'<table' in response.content


@pytest.mark.django_db
def test_default_formatters():
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
        <table class="listview" data-endpoint="/tbody">
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
        foo = Column.choice_queryset(query__show=True, query__gui__show=True, bulk__show=True, choices=lambda table, **_: TFoo.objects.filter(a=1))

        class Meta:
            model = TFoo

    foo_table = FooTable(rows=TFoo.objects.all(), request=req('get'))

    assert repr(foo_table.bound_column_by_name['foo'].choices) == repr(TFoo.objects.filter(a=1))
    assert repr(foo_table.bulk_form.fields_by_name['foo'].choices) == repr(TFoo.objects.filter(a=1))
    assert repr(foo_table.query_form.fields_by_name['foo'].choices) == repr(TFoo.objects.filter(a=1))


@pytest.mark.django_db
def test_multi_choice_queryset():
    assert TFoo.objects.all().count() == 0

    TFoo.objects.create(a=1)
    TFoo.objects.create(a=2)
    TFoo.objects.create(a=3)
    TFoo.objects.create(a=4)

    class FooTable(Table):
        foo = Column.multi_choice_queryset(query__show=True, query__gui__show=True, bulk__show=True, choices=lambda table, **_: TFoo.objects.exclude(a=3).exclude(a=4))

        class Meta:
            model = TFoo

    foo_table = FooTable(rows=TFoo.objects.all())
    foo_table.bind(request=req('get'))

    assert repr(foo_table.bound_column_by_name['foo'].choices) == repr(TFoo.objects.exclude(a=3).exclude(a=4))
    assert repr(foo_table.bulk_form.fields_by_name['foo'].choices) == repr(TFoo.objects.exclude(a=3).exclude(a=4))
    assert repr(foo_table.query_form.fields_by_name['foo'].choices) == repr(TFoo.objects.exclude(a=3).exclude(a=4))


@pytest.mark.django_db
def test_query_namespace_inject():
    class FooException(Exception):
        pass

    def post_validation(form):
        del form
        raise FooException()

    with pytest.raises(FooException):
        foo = Table(
            rows=[],
            model=TFoo,
            request=Struct(method='POST', POST={'-': '-'}, GET=Struct(urlencode=lambda: '')),
            columns=[Column(name='a', query__show=True, query__gui__show=True)],
            query__gui__post_validation=post_validation)
        foo.bind(request=None)


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

    assert TestTable(rows=[]).columns[0].extra.foo == 1
    assert TestTable(rows=[]).columns[0].extra.bar == 2


def test_row_extra():
    class TestTable(Table):
        result = Column(cell__value=lambda bound_row, **_: bound_row.extra.foo)

        class Meta:
            row__extra__foo = lambda table, row, **_: row.a + row.b

    bound_row = list(TestTable(request=req('get'), rows=[Struct(a=5, b=7)]))[0]
    assert bound_row.extra.foo == 5 + 7
    assert bound_row['result'].value == 5 + 7


def test_row_extra_struct():
    class TestTable(Table):
        result = Column(cell__value=lambda bound_row, **_: bound_row.extra.foo)

        class Meta:
            row__extra = lambda table, row, **_: Namespace(foo=row.a + row.b)

    bound_row = list(TestTable(request=req('get'), rows=[Struct(a=5, b=7)]))[0]
    assert bound_row.extra.foo == 5 + 7
    assert bound_row['result'].value == 5 + 7


def test_from_model():
    t = Table.from_model(
        model=TFoo,
        rows=TFoo.objects.all(),
        column__a__display_name='Some a',
        column__a__extra__stuff='Some stuff',
    )
    t.bind(request=None)
    assert [x.name for x in t.columns] == ['id', 'a', 'b']
    assert [x.name for x in t.columns if x.show] == ['a', 'b']
    assert 'Some a' == t.bound_column_by_name['a'].display_name
    assert 'Some stuff' == t.bound_column_by_name['a'].extra.stuff


def test_from_model_foreign_key():
    t = Table.from_model(
        model=TBar,
    )
    assert [x.name for x in t.columns] == ['id', 'foo', 'c']
    assert [x.name for x in t.columns if x.show] == ['foo', 'c']


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
            query__gui__extra__endpoint_attr='b',
            query__show=True,
            bulk__show=True,
            query__gui__show=True)

    # This test could also have been made with perform_ajax_dispatch directly, but it's nice to have a test that tests more of the code path
    result = request_with_middleware(response=TestTable.as_page(rows=TBar.objects.all()), data={'/table/query/gui/field/foo': 'hopp'})
    assert json.loads(result.content) == {
        'more': False,
        'page': 1,
        'results': [{'id': 2, 'text': 'Foo(42, Hopp)'}]
    }


@pytest.mark.django_db
def test_ajax_endpoint_empty_response():
    class TestTable(Table):
        class Meta:
            endpoint__foo = lambda **_: []

        bar = Column()

    actual = perform_ajax_dispatch(root=TestTable(rows=[]), path='/foo', value='', request=req('get'))
    assert actual == []


def test_ajax_data_endpoint():

    class TestTable(Table):
        class Meta:
            endpoint__data = lambda table, **_: [{cell.bound_column.name: cell.value for cell in bound_row} for bound_row in table]

        foo = Column()
        bar = Column()


    table = TestTable(rows=[
        Struct(foo=1, bar=2),
        Struct(foo=3, bar=4),
    ])
    table.bind(request=None)

    actual = perform_ajax_dispatch(root=table, path='/data', value='', request=req('get'))
    expected = [dict(foo=1, bar=2), dict(foo=3, bar=4)]
    assert actual == expected


def test_ajax_endpoint_namespacing():
    class TestTable(Table):
        class Meta:
            endpoint__bar = lambda **_: 17

        baz = Column()

    with pytest.raises(InvalidEndpointPathException):
        perform_ajax_dispatch(root=TestTable(rows=[]), path='/baz', value='', request=req('get'))

    actual = perform_ajax_dispatch(root=TestTable(rows=[]), path='/bar', value='', request=req('get'))
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

    table = TestTable(request=req('get'))

    expected = [
        dict(foo='a', bar=2),
        dict(foo='b', bar=3),
    ]
    assert expected == [{bound_cell.bound_column.name: bound_cell.value for bound_cell in bound_row} for bound_row in table]


def test_ajax_custom_endpoint():
    class TestTable(Table):
        class Meta:
            endpoint__foo = lambda value, **_: dict(baz=value)
        spam = Column()

    actual = perform_ajax_dispatch(root=TestTable(rows=[]), path='/foo', value='bar', request=req('get'))
    assert actual == dict(baz='bar')


def test_row_level_additions():
    # TODO: empty test? what was this?
    pass


def test_table_extra_namespace():
    class TestTable(Table):
        class Meta:
            extra__foo = 17

        foo = Column()

    assert 17 == TestTable(request=req('get'), rows=[]).extra.foo


def test_defaults():
    class TestTable(Table):
        foo = Column()
    assert not TestTable.foo.query.show
    assert not TestTable.foo.bulk.show
    assert not TestTable.foo.auto_rowspan
    assert TestTable.foo.sortable
    assert not TestTable.foo.sort_default_desc
    assert TestTable.foo.show


def test_yes_no_formatter():
    assert yes_no_formatter(None) == ''
    assert yes_no_formatter(True) == 'Yes'
    assert yes_no_formatter(1) == 'Yes'
    assert yes_no_formatter(False) == 'No'
    assert yes_no_formatter(0) == 'No'


def test_repr():
    assert repr(Column(name='foo')) == '<iommi.table.Column foo>'


@pytest.mark.django_db
def test_ordering():
    TFoo.objects.create(a=1, b='d')
    TFoo.objects.create(a=2, b='c')
    TFoo.objects.create(a=3, b='b')
    TFoo.objects.create(a=4, b='a')

    # no ordering
    t = Table.from_model(model=TFoo)
    t.bind(request=req('get'))
    assert not t.rows.query.order_by

    # ordering from GET parameter
    t = Table.from_model(model=TFoo)
    t.bind(request=req('get', order='a'))
    assert list(t.rows.query.order_by) == ['a']

    # default ordering
    t = Table.from_model(model=TFoo, default_sort_order='b')
    t.bind(request=req('get', order='b'))
    assert list(t.rows.query.order_by) == ['b']


@pytest.mark.django_db
def test_many_to_many():
    f1 = TFoo.objects.create(a=17, b="Hej")
    f2 = TFoo.objects.create(a=23, b="Hopp")

    baz = TBaz.objects.create()
    f1.tbaz_set.add(baz)
    f2.tbaz_set.add(baz)

    expected_html = """
<table class="listview" data-endpoint="/tbody">
    <thead>
        <tr>
            <th class="first_column subheader">
                <a href="?order=foo">
                    Foo
                </a>
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

    verify_table_html(expected_html=expected_html, table__model=TBaz)


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
    <table class="listview" data-endpoint="/tbody">
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
    table.bind(request=None)
    results = list(table)
    assert len(results) == 2
    assert results[0].row == f
    assert results[1].row == Struct(a=15)


@pytest.mark.django_db
def test_non_model_based_column_should_not_explore_in_query_object_creation():
    class MyTable(Table):
        c = Column(attr=None, query__show=True, query__gui__show=True)

        class Meta:
            model = TFoo

    table = MyTable()
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

    class MyVariable(Variable):
        @classmethod
        @class_shortcut(
            gui__call_target__attribute='float',
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

    t = MyTable.from_model(
        rows=FromModelWithInheritanceTest.objects.all(),
        model=FromModelWithInheritanceTest,
        request=req('get'),
        column__value__query__show=True,
        column__value__query__gui__show=True,
        column__value__bulk__show=True,
    )

    assert was_called == {
        'MyField.float': 2,
        'MyVariable.float': 1,
        'MyColumn.float': 1,
    }


def test_column_merge():
    table = Table(
        column__foo={},
        rows=[
            Struct(foo=1),
        ]
    )
    table.bind(request=None)
    assert len(table.columns) == 1
    assert table.columns[0].name == 'foo'
    for row in table:
        assert row['foo'].value == 1


def test_hide_named_column():
    class MyTable(Table):
        foo = Column()

    table = MyTable(column__foo__show=False, rows=[])
    table.bind(request=None)
    assert len(table.shown_bound_columns) == 0


def test_override_doesnt_stick():
    class MyTable(Table):
        foo = Column()

    table = MyTable(column__foo__show=False, rows=[])
    table.bind(request=None)
    assert len(table.shown_bound_columns) == 0

    table2 = MyTable(rows=[])
    table2.bind(request=None)
    assert len(table2.shown_bound_columns) == 1


@pytest.mark.django_db
def test_new_style_ajax_dispatch():
    TFoo.objects.create(a=1, b='A')
    TFoo.objects.create(a=2, b='B')
    TFoo.objects.create(a=3, b='C')

    def get_response(request):
        del request
        return Table.as_page(model=TBar, column__foo__query=dict(show=True, gui__show=True))

    from iommi.page import middleware
    m = middleware(get_response)
    done, response = m(request=req('get', **{'/table/query/gui/field/foo': ''}))

    assert done
    assert json.loads(response.content) == {
        'results': [
            {'id': 1, 'text': 'Foo(1, A)'},
            {'id': 2, 'text': 'Foo(2, B)'},
            {'id': 3, 'text': 'Foo(3, C)'},
        ],
        'page': 1,
        'more': False,
    }


@override_settings(DEBUG=True)
def test_endpoint_path_of_nested_part():
    page = Table.as_page(model=TBar, column__foo__query=dict(show=True, gui__show=True))
    page.bind(request=None)
    assert page.children().table.default_child
    target, parents = find_target(path='/table/query/gui/field/foo', root=page)
    assert target.endpoint_path() == '/foo'
