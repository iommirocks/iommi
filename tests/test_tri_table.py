#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import json

import django
from django.db.models import QuerySet
from django.http import HttpResponse
from django.template import Template
from django.test import RequestFactory
from django.utils.encoding import python_2_unicode_compatible
import pytest
from django.utils.safestring import mark_safe
from tri.declarative import getattr_path, Namespace
from tri.form import Field
from tri.query import Variable

from tests.helpers import verify_table_html
from tests.models import Foo, Bar, Baz

from tri.table import Struct, Table, Column, Link, render_table, render_table_to_response, register_cell_formatter, \
    yes_no_formatter, SELECT_DISPLAY_NAME


def get_data():
    return [
        Struct(foo="Hello", bar=17),
        Struct(foo="<evil/> &", bar=42)
    ]


def explicit_table():

    columns = [
        Column(name="foo"),
        Column.number(name="bar"),
    ]

    return Table(data=get_data(), columns=columns, attrs__class__another_class=True, attrs__id='table_id')


def declarative_table():

    class TestTable(Table):

        class Meta:
            attrs__class__another_class = lambda table: True
            attrs__id = lambda table: 'table_id'

        foo = Column()
        bar = Column.number()

    return TestTable(data=get_data())


@pytest.mark.parametrize('table', [
    explicit_table(),
    declarative_table()
])
def test_render_impl(table):

    verify_table_html(table=table, expected_html="""
        <table class="another_class listview" id="table_id">
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

    assert {'foo', 'bar'} == {column.name for column in MyTable([]).columns}


def test_kwarg_column_config_injection():
    class MyTable(Table):
        foo = Column()

    table = MyTable([], column__foo__extra__stuff="baz")
    assert 'baz' == table.bound_column_by_name['foo'].extra.stuff


def test_bad_arg():
    with pytest.raises(TypeError) as e:
        Table(data=[], columns=[Column()], foo=None)
    assert 'foo' in str(e)


def test_column_ordering():

    class MyTable(Table):
        foo = Column(after='bar')
        bar = Column()

    assert ['bar', 'foo'] == [column.name for column in MyTable([]).columns]


def test_column_with_meta():
    class MyColumn(Column):
        class Meta:
            sortable = False

    class MyTable(Table):
        foo = MyColumn()
        bar = MyColumn.icon('history')

    assert not MyTable([]).bound_column_by_name['foo'].sortable
    assert not MyTable([]).bound_column_by_name['bar'].sortable


@pytest.mark.django_db
def test_django_table():

    f1 = Foo.objects.create(a=17, b="Hej")
    f2 = Foo.objects.create(a=42, b="Hopp")

    Bar(foo=f1, c=True).save()
    Bar(foo=f2, c=False).save()

    class TestTable(Table):
        foo__a = Column.number()
        foo__b = Column()
        foo = Column.choice_queryset(model=Foo, choices=lambda table, column, **_: Foo.objects.all(), query__show=True, bulk__show=True, query__gui__show=True)

    t = TestTable(data=Bar.objects.all().order_by('pk'), request=RequestFactory().get("/", ''))

    assert list(t.bound_column_by_name['foo'].choices) == list(Foo.objects.all())
    assert list(t.bulk_form.fields_by_name['foo'].choices) == list(Foo.objects.all())
    assert list(t.query_form.fields_by_name['foo'].choices) == list(Foo.objects.all())

    verify_table_html(table=t, expected_html="""
        <table class="listview">
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

    t = TestTable(data=[])
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

    data = [
        Struct(foo="Hello räksmörgås ><&>",
               bar=17,
               get_absolute_url=lambda: '/somewhere/'),
    ]

    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview" id="table_id">
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

    data = [Struct(foo=Struct(bar="bar"))]

    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
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
#     data = [('a', 'b', 'c')]
#
#     verify_table_html(TestTable(data=data), """
#         <table class="listview">
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
#     data = [{'a': 'a', 'b': 'b', 'c': 'c'}]
#
#     verify_table_html(TestTable(data=data), """
#         <table class="listview">
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

    data = [Struct(foo="foo")]

    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
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

    data = [Struct(foo='foo', bar=Struct(get_absolute_url=lambda: '/get/absolute/url/result'))]

    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
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


def test_deprecated_css_class():
    with pytest.warns(DeprecationWarning):
        class TestTable(NoSortTable):
            foo = Column(attrs__class__some_class=True)
            legacy_foo = Column(css_class={"some_other_class"})
            legacy_bar = Column(cell__attrs={'class': 'foo'},
                                cell__attrs__class__bar=True)

        data = [Struct(foo="foo", legacy_foo="foo", legacy_bar="bar")]

        verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
            <thead>
                <tr>
                    <th class="first_column some_class subheader"> Foo </th>
                    <th class="first_column some_other_class subheader"> Legacy foo </th>
                    <th class="first_column subheader"> Legacy bar </th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td> foo </td>
                    <td> foo </td>
                    <td class="bar foo"> bar </td>
                </tr>
            </tbody>
        </table>""")


def test_css_class():
    class TestTable(NoSortTable):
        foo = Column(
            header__attrs__class__some_class=True,
            cell__attrs__class__bar=True
        )

    data = [Struct(foo="foo")]

    verify_table_html(table=TestTable(data=data), expected_html="""
    <table class="listview">
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

    data = [Struct(foo="foo")]

    verify_table_html(table=TestTable(data=data), expected_html="""
    <table class="listview">
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


def test_title():
    with pytest.warns(DeprecationWarning):
        class TestTable(NoSortTable):
            foo = Column(title="Some title")

        data = [Struct(foo="foo")]

        verify_table_html(table=TestTable(data), expected_html="""
        <table class="listview">
            <thead>
                <tr><th class="first_column subheader" title="Some title"> Foo </th></tr>
            </thead>\
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

    data = [Struct(foo="foo", bar="bar")]

    verify_table_html(table=TestTable(data=data), expected_html="""
    <table class="listview">
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

    data = [Struct(foo="foo", bar="bar")]

    verify_table_html(table=TestTable(data=data), expected_html="""
    <table class="listview">
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

    data = [Struct(foo="foo")]

    verify_table_html(table=TestTable(data=data), expected_html="""
    <table class="listview">
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

    verify_table_html(table=TestTable(data=[Struct(yada=1), Struct(yada=2)]), expected_html="""
        <table class="classy listview" foo="bar">
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

    verify_table_html(table=TestTable(data=[Struct(yada=1), Struct(yada=2)]), expected_html="""
        <table class="classy listview" foo="bar">
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

    data = [Struct(pk=123,
                   get_absolute_url=lambda: "http://yada/",
                   boolean=lambda: True,
                   link=Struct(get_absolute_url=lambda: "http://yadahada/"),
                   number=123)]
    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
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
        Foo(a=x, b="foo").save()

    class TestTable(Table):
        a = Column.number(sortable=False)  # turn off sorting to not get the link with random query params
        b = Column(show=False)  # should still be able to filter on this though!

    verify_table_html(table=TestTable(data=Foo.objects.all().order_by('pk')),
                      query=dict(page_size=2, page=2, query='b="foo"'),
                      expected_html="""
        <table class="listview">
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
        Foo(a=x, b="foo").save()

    class TestTable(Table):
        a = Column.number(sortable=False)  # turn off sorting to not get the link with random query params
        b = Column(show=False)  # should still be able to filter on this though!

    from django.core.paginator import Paginator

    class CustomPaginator(Paginator):
        def __init__(self, object_list):
            super(CustomPaginator, self).__init__(object_list=object_list, per_page=2)

        def get_page(self, number):
            del number
            return self.page(2)

    data = Foo.objects.all().order_by('pk')
    verify_table_html(
        table=TestTable(data=data),
        paginator=CustomPaginator(data),
        expected_html="""
        <table class="listview">
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


def test_links():
    class TestTable(NoSortTable):
        foo = Column(header__attrs__title="Some title")

    data = [Struct(foo="foo")]

    links = [
        Link('Foo', attrs__href='/foo/', show=lambda table: table.data is not data),
        Link('Bar', attrs__href='/bar/', show=lambda table: table.data is data),
        Link('Baz', attrs__href='/bar/', group='Other'),
        Link('Qux', attrs__href='/bar/', group='Other'),
        Link.icon('icon_foo', title='Icon foo', attrs__href='/icon_foo/'),
        Link.icon('icon_bar', icon_classes=['lg'], title='Icon bar', attrs__href='/icon_bar/'),
        Link.icon('icon_baz', icon_classes=['one', 'two'], title='Icon baz', attrs__href='/icon_baz/'),
    ]

    verify_table_html(table=TestTable(data=data),
                      find=dict(class_='links'),
                      links=links,
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
    assert Foo.objects.all().count() == 0

    foos = [
        Foo.objects.create(a=1, b=""),
        Foo.objects.create(a=2, b=""),
        Foo.objects.create(a=3, b=""),
        Foo.objects.create(a=4, b=""),
    ]

    assert [x.pk for x in foos] == [1, 2, 3, 4]

    class TestTable(Table):
        a = Column.number(sortable=False, bulk__show=True)  # turn off sorting to not get the link with random query params
        b = Column(bulk__show=True)

    result = render_table(request=RequestFactory(HTTP_REFERER='/').get("/", dict(pk_1='', pk_2='', a='0', b='changed')), table=TestTable(data=Foo.objects.all()))
    assert '<form method="post" action=".">' in result
    assert '<input type="submit" class="button" value="Bulk change"/>' in result

    def post_bulk_edit(table, queryset, updates, **_):
        assert isinstance(table, TestTable)
        assert isinstance(queryset, QuerySet)
        assert {x.pk for x in queryset} == {1, 2}
        assert updates == dict(a=0, b='changed')

    render_table(request=RequestFactory(HTTP_REFERER='/').post("/", dict(pk_1='', pk_2='', a='0', b='changed')), table=TestTable(data=Foo.objects.all().order_by('pk')), post_bulk_edit=post_bulk_edit)

    assert [(x.pk, x.a, x.b) for x in Foo.objects.all()] == [
        (1, 0, u'changed'),
        (2, 0, u'changed'),
        (3, 3, u''),
        (4, 4, u''),
    ]

    # Test that empty field means "no change"
    render_table(request=RequestFactory(HTTP_REFERER='/').post("/", dict(pk_1='', pk_2='', a='', b='')), table=TestTable(data=Foo.objects.all()))
    assert [(x.pk, x.a, x.b) for x in Foo.objects.all()] == [
        (1, 0, u'changed'),
        (2, 0, u'changed'),
        (3, 3, u''),
        (4, 4, u''),
    ]

    # Test edit all feature
    render_table(request=RequestFactory(HTTP_REFERER='/').post("/", dict(a='11', b='changed2', _all_pks_='1')), table=TestTable(data=Foo.objects.all()))

    assert [(x.pk, x.a, x.b) for x in Foo.objects.all()] == [
        (1, 11, u'changed2'),
        (2, 11, u'changed2'),
        (3, 11, u'changed2'),
        (4, 11, u'changed2'),
    ]


@pytest.mark.django_db
def test_query():
    assert Foo.objects.all().count() == 0

    Foo(a=1, b="foo").save()
    Foo(a=2, b="foo").save()
    Foo(a=3, b="bar").save()
    Foo(a=4, b="bar").save()

    class TestTable(Table):
        a = Column.number(sortable=False, query__show=True, query__gui__show=True)  # turn off sorting to not get the link with random query params
        b = Column.substring(query__show=True, query__gui__show=True)

        class Meta:
            sortable = False

    verify_table_html(query=dict(query='asdasdsasd'), table=TestTable(data=Foo.objects.all().order_by('pk')), find=dict(id='tri_query_error'), expected_html='<div id="tri_query_error">Invalid syntax for query</div>')

    verify_table_html(query=dict(a='1'), table=TestTable(data=Foo.objects.all().order_by('pk')), find=dict(name='tbody'), expected_html="""
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
    verify_table_html(query=dict(b='bar'), table=TestTable(data=Foo.objects.all().order_by('pk')), find=dict(name='tbody'), expected_html="""
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
    verify_table_html(query=dict(query='b="bar"'), table=TestTable(data=Foo.objects.all().order_by('pk')), find=dict(name='tbody'), expected_html="""
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
    verify_table_html(query=dict(b='fo'), table=TestTable(data=Foo.objects.all().order_by('pk')), find=dict(name='tbody'), expected_html="""
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

    data = [Struct(foo="sentinel")]

    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
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

    data = [Struct(foo="foo")]

    verify_table_html(table=TestTable(data=data), expected_html="""
            <table class="listview">
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

    data = [Struct(foo="foo")]

    verify_table_html(table=TestTable(data=data), expected_html="""
            <table class="listview">
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

    Foo.objects.create(a=1)

    def explode(**_):
        assert False

    class TestTable(NoSortTable):
        class Meta:
            model = Foo
            links__template = Template('What links')
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
        table=TestTable(),
        links=[
            Link('foo', attrs__href='bar'),
        ],
        expected_html="""
        What filters
        <div class="table-container">
            <form action="." method="post">
                <table class="listview">
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

    data = [Struct(foo="sentinel")]

    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
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

    data = [Struct(foo="bar")]

    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
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

    data = [Struct(foo="sentinel", bar="schmentinel")]

    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
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

        sentinel2 = Column(cell__value=lambda table, column, row, **_: '%s %s %s' % (table.sentinel1, column.name, row.sentinel3))

    data = [Struct(sentinel3="sentinel3")]

    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
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

    data = [
        Struct(foo=1),
        Struct(foo=1),
        Struct(foo=2),
        Struct(foo=2),
    ]

    expected = """
        <table class="listview">
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

    t = TestTable(data=data)
    verify_table_html(table=t, expected_html=expected)
    verify_table_html(table=t, expected_html=expected)


def test_render_table_to_response():
    class TestTable(NoSortTable):
        foo = Column(display_name="Bar")

    data = [Struct(foo="foo")]

    response = render_table_to_response(RequestFactory().get('/'), table=TestTable(data=data))
    assert isinstance(response, HttpResponse)
    assert b'<table' in response.content


@pytest.mark.django_db
def test_default_formatters():
    class TestTable(NoSortTable):
        foo = Column()

    @python_2_unicode_compatible
    class SomeType(object):
        def __str__(self):
            return 'this should not end up in the table'

    register_cell_formatter(SomeType, lambda value, **_: 'sentinel')

    assert Foo.objects.all().count() == 0

    Foo(a=1, b="3").save()
    Foo(a=2, b="5").save()

    data = [
        Struct(foo=1),
        Struct(foo=True),
        Struct(foo=False),
        Struct(foo=[1, 2, 3]),
        Struct(foo=SomeType()),
        Struct(foo=Foo.objects.all()),
        Struct(foo=None),
    ]

    verify_table_html(table=TestTable(data=data), expected_html="""
        <table class="listview">
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
    assert Foo.objects.all().count() == 0

    Foo.objects.create(a=1)
    Foo.objects.create(a=2)

    class FooTable(Table):
        foo = Column.choice_queryset(query__show=True, query__gui__show=True, bulk__show=True, choices=lambda table, column, **_: Foo.objects.filter(a=1))

        class Meta:
            model = Foo

    foo_table = FooTable(data=Foo.objects.all(), request=RequestFactory().get("/", ''))

    assert repr(foo_table.bound_column_by_name['foo'].choices) == repr(Foo.objects.filter(a=1))
    assert repr(foo_table.bulk_form.fields_by_name['foo'].choices) == repr(Foo.objects.filter(a=1))
    assert repr(foo_table.query_form.fields_by_name['foo'].choices) == repr(Foo.objects.filter(a=1))


@pytest.mark.django_db
def test_multi_choice_queryset():
    assert Foo.objects.all().count() == 0

    Foo.objects.create(a=1)
    Foo.objects.create(a=2)
    Foo.objects.create(a=3)
    Foo.objects.create(a=4)

    class FooTable(Table):
        foo = Column.multi_choice_queryset(query__show=True, query__gui__show=True, bulk__show=True, choices=lambda table, column, **_: Foo.objects.exclude(a=3).exclude(a=4))

        class Meta:
            model = Foo

    foo_table = FooTable(data=Foo.objects.all(), request=RequestFactory().get("/", ''))
    foo_table.prepare()

    assert repr(foo_table.bound_column_by_name['foo'].choices) == repr(Foo.objects.exclude(a=3).exclude(a=4))
    assert repr(foo_table.bulk_form.fields_by_name['foo'].choices) == repr(Foo.objects.exclude(a=3).exclude(a=4))
    assert repr(foo_table.query_form.fields_by_name['foo'].choices) == repr(Foo.objects.exclude(a=3).exclude(a=4))


@pytest.mark.django_db
def test_query_namespace_inject():
    class FooException(Exception):
        pass

    def post_validation(form):
        del form
        raise FooException()

    with pytest.raises(FooException):
        foo = Table(
            data=[],
            model=Foo,
            request=Struct(method='POST', POST={'-': '-'}, GET=Struct(urlencode=lambda: '')),
            columns=[Column(name='foo', query__show=True, query__gui__show=True)],
            query__gui__post_validation=post_validation)
        foo.prepare()


def test_float():
    x = Column.float()
    assert getattr_path(x, 'query__call_target') == Variable.float
    assert getattr_path(x, 'bulk__call_target') == Field.float


def test_integer():
    x = Column.integer()
    assert getattr_path(x, 'query__call_target') == Variable.integer
    assert getattr_path(x, 'bulk__call_target') == Field.integer


def test_date():
    x = Column.date()
    assert getattr_path(x, 'query__call_target') == Variable.date
    assert getattr_path(x, 'bulk__call_target') == Field.date


def test_datetime():
    x = Column.datetime()
    assert getattr_path(x, 'query__call_target') == Variable.datetime
    assert getattr_path(x, 'bulk__call_target') == Field.datetime


def test_email():
    x = Column.email()
    assert getattr_path(x, 'query__call_target') == Variable.email
    assert getattr_path(x, 'bulk__call_target') == Field.email


def test_backwards_compatible_call_target():
    def backwards_compatible_call_target(**kwargs):
        del kwargs
        raise Exception('Hello!')

    class FooTable(Table):
        foo = Column(query__show=True, query__gui__show=True, query__gui=backwards_compatible_call_target)

    with pytest.raises(Exception) as e:
        t = FooTable(data=[], model=Foo)
        t.query.form()

    assert 'Hello!' == str(e.value)


def test_extra():
    class TestTable(Table):
        foo = Column(extra__foo=1, extra__bar=2)

    assert TestTable(data=[]).columns[0].extra.foo == 1
    assert TestTable(data=[]).columns[0].extra.bar == 2


def test_row_extra():
    class TestTable(Table):
        result = Column(cell__value=lambda bound_row, **_: bound_row.extra.foo)

        class Meta:
            row__extra__foo = lambda table, row, **_: row.a + row.b

    bound_row = list(TestTable(request=RequestFactory().get(path='/'), data=[Struct(a=5, b=7)]))[0]
    assert bound_row.extra.foo == 5 + 7
    assert bound_row['result'].value == 5 + 7


def test_row_extra_struct():
    class TestTable(Table):
        result = Column(cell__value=lambda bound_row, **_: bound_row.extra.foo)

        class Meta:
            row__extra = lambda table, row, **_: Namespace(foo=row.a + row.b)

    bound_row = list(TestTable(request=RequestFactory().get(path='/'), data=[Struct(a=5, b=7)]))[0]
    assert bound_row.extra.foo == 5 + 7
    assert bound_row['result'].value == 5 + 7


def test_from_model():
    t = Table.from_model(
        model=Foo,
        data=Foo.objects.all(),
        column__a__display_name='Some a',
        column__a__extra__stuff='Some stuff',
    )
    assert [x.name for x in t.columns] == ['id', 'a', 'b']
    assert [x.name for x in t.columns if x.show] == ['a', 'b']
    assert 'Some a' == t.bound_column_by_name['a'].display_name
    assert 'Some stuff' == t.bound_column_by_name['a'].extra.stuff


@pytest.mark.django_db
def test_ajax_endpoint():
    f1 = Foo.objects.create(a=17, b="Hej")
    f2 = Foo.objects.create(a=42, b="Hopp")

    Bar(foo=f1, c=True).save()
    Bar(foo=f2, c=False).save()

    class TestTable(Table):
        foo = Column.choice_queryset(
            model=Foo,
            choices=lambda table, column, **_: Foo.objects.all(),
            query__gui__extra__endpoint_attr='b',
            query__show=True,
            bulk__show=True,
            query__gui__show=True)

    result = render_table(request=RequestFactory().get("/", {'/query/gui/field/foo': 'hopp'}), table=TestTable(data=Bar.objects.all()))
    assert json.loads(result.content.decode('utf8')) == [{'id': 2, 'text': 'Hopp'}]


@pytest.mark.django_db
def test_ajax_endpoint_empty_response():
    class TestTable(Table):
        class Meta:
            endpoint__foo = lambda **_: []

        bar = Column()

    result = render_table(request=RequestFactory().get("/", {'/foo': ''}), table=TestTable(data=[]))
    assert [] == json.loads(result.content.decode('utf8'))


def test_ajax_data_endpoint():

    class TestTable(Table):
        class Meta:
            endpoint__data = lambda table, key, value: [{cell.bound_column.name: cell.value for cell in row} for row in table]

        foo = Column()
        bar = Column()

    table = TestTable(data=[
        Struct(foo=1, bar=2),
        Struct(foo=3, bar=4),
    ])

    result = render_table(request=RequestFactory().get("/", {'/data': ''}), table=table)
    assert json.loads(result.content.decode('utf8')) == [dict(foo=1, bar=2), dict(foo=3, bar=4)]


def test_ajax_endpoint_namespacing():
    class TestTable(Table):
        class Meta:
            endpoint_dispatch_prefix = 'foo'
            endpoint__bar = lambda **_: 17

        baz = Column()

    result = render_table(request=RequestFactory().get("/", {'/not_foo/bar': ''}), table=TestTable(data=[]))
    assert result is None
    result = render_table(request=RequestFactory().get("/", {'/foo/bar': ''}), table=TestTable(data=[]))
    assert 17 == json.loads(result.content.decode('utf8'))


def test_table_iteration():

    class TestTable(Table):
        class Meta:
            data = [
                Struct(foo='a', bar=1),
                Struct(foo='b', bar=2)
            ]

        foo = Column()
        bar = Column(cell__value=lambda row, **_: row['bar'] + 1)

    table = TestTable(request=RequestFactory().get('/'))

    expected = [
        dict(foo='a', bar=2),
        dict(foo='b', bar=3),
    ]
    assert expected == [{bound_cell.bound_column.name: bound_cell.value for bound_cell in bound_row} for bound_row in table]


def test_ajax_custom_endpoint():
    class TestTable(Table):
        class Meta:
            endpoint__foo = lambda table, key, value: dict(baz=value)
        spam = Column()

    result = render_table(request=RequestFactory().get("/", {'/foo': 'bar'}), table=TestTable(data=[]))
    assert json.loads(result.content.decode('utf8')) == dict(baz='bar')


def test_row_level_additions():
    pass


def test_table_extra_namespace():
    class TestTable(Table):
        class Meta:
            extra__foo = 17

        foo = Column()

    assert 17 == TestTable(request=RequestFactory().get('/'), data=[]).extra.foo


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


def test_blank_on_empty():
    assert render_table(RequestFactory().get('/'), table=Table(data=[], columns=[Column(name='foo')]), blank_on_empty=True) == ''


def test_repr():
    assert repr(Column(name='foo')) == '<tri.table.Column foo>'


@pytest.mark.django_db
def test_ordering():
    Foo.objects.create(a=1, b='d')
    Foo.objects.create(a=2, b='c')
    Foo.objects.create(a=3, b='b')
    Foo.objects.create(a=4, b='a')

    # no ordering
    t = Table.from_model(model=Foo, request=RequestFactory().get('/'))
    t.prepare()
    assert not t.data.query.order_by

    # ordering from GET parameter
    t = Table.from_model(model=Foo, request=RequestFactory().get('/', dict(order='a')))
    t.prepare()
    assert list(t.data.query.order_by) == ['a']

    # default ordering
    t = Table.from_model(model=Foo, default_sort_order='b', request=RequestFactory().get('/'))
    t.prepare()
    assert list(t.data.query.order_by) == ['b']


@pytest.mark.django_db
def test_foreign_key():
    f1 = Foo.objects.create(a=17, b="Hej")
    f2 = Foo.objects.create(a=23, b="Hopp")

    baz = Baz.objects.create()
    f1.baz_set.add(baz)
    f2.baz_set.add(baz)

    expected_html = """
<table class="listview">
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

    verify_table_html(expected_html=expected_html, table__model=Baz)


def test_link_class_backwards_compatibility():
    with pytest.deprecated_call():
        assert Link(title='foo', url='bar').render() == '<a href="bar">foo</a>'
    assert Link(title='foo', attrs__href='bar').render() == '<a href="bar">foo</a>'


@pytest.mark.django_db
def test_preprocess_row_deprecated():
    with pytest.warns(DeprecationWarning):
        Foo.objects.create(a=1, b='d')

        def preprocess(table, row, **_):
            del table
            row.some_non_existent_property = 1

        class PreprocessedTable(Table):
            some_non_existent_property = Column()

            class Meta:
                preprocess_row = preprocess
                data = Foo.objects.all().order_by('pk')

        expected_html = """
        <table class="listview">
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
def test_preprocess_row():
    Foo.objects.create(a=1, b='d')

    def preprocess(table, row, **_):
        del table
        row.some_non_existent_property = 1
        return row

    class PreprocessedTable(Table):
        some_non_existent_property = Column()

        class Meta:
            preprocess_row = preprocess
            data = Foo.objects.all().order_by('pk')

    expected_html = """
    <table class="listview">
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
    f = Foo.objects.create(a=3, b='d')

    def my_preprocess_data(data, **kwargs):
        for row in data:
            yield row
            yield Struct(a=row.a * 5)

    class MyTable(Table):
        a = Column()

        class Meta:
            preprocess_data = my_preprocess_data

    results = list(MyTable(data=Foo.objects.all()))
    assert len(results) == 2
    assert results[0].row == f
    assert results[1].row == Struct(a=15)
