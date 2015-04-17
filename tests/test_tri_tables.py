#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.http import HttpResponse

import pytest
from django.test import RequestFactory
from tests.helpers import verify_table_html
from tests.models import Foo, Bar

from tri.tables import Struct, Table, Column, Link, render_table, render_table_to_response


def get_data():
    return [
        Struct(foo="Hello", bar=17),
        Struct(foo="world!", bar=42)
    ]


def explicit_table():

    columns = [
        Column(name="foo"),
        Column.number(name="bar"),
    ]

    return Table(get_data(), columns, attrs=dict(id='table_id'))


def declarative_table():

    class TestTable(Table):

        class Meta:
            attrs = dict(id='table_id')

        foo = Column()
        bar = Column.number()

    return TestTable(get_data())


@pytest.mark.parametrize('table', [
    explicit_table(),
    declarative_table()
])
def test_render(table):

    verify_table_html(table, """
        <table class="listview" id="table_id">
            <thead>
                <tr>
                    <th class="subheader first_column">
                        <a href="?order=foo"> Foo </a>
                    </th>
                    <th class="subheader first_column">
                        <a href="?order=bar"> Bar </a>
                    </th>
                </tr>
            </thead>
            <tr class="row1">
                <td> Hello </td>
                <td class="rj"> 17 </td>
            </tr>
            <tr class="row2">
                <td> world! </td>
                <td class="rj"> 42 </td>
            </tr>
        </table>""")


@pytest.mark.django_db
def test_django_table():

    Foo(a=17, b="Hej").save()
    Foo(a=42, b="Hopp").save()

    class TestTable(Table):
        a = Column.number()
        b = Column()

    verify_table_html(TestTable(Foo.objects.all()), """
        <table class="listview">
            <thead>
                <tr>
                    <th class="subheader first_column">
                        <a href="?order=a"> A </a>
                    </th>
                    <th class="subheader first_column">
                        <a href="?order=b"> B </a>
                    </th>
                </tr>
            </thead>
            <tr class="row1" data-pk="1">
                <td class="rj"> 17 </td>
                <td> Hej </td>
            </tr>
            <tr class="row2" data-pk="2">
                <td class="rj"> 42 </td>
                <td> Hopp </td>
            </tr>
        </table>""")


def test_inheritance():

    class FooTable(Table):
        foo = Column()

    class BarTable(Table):
        bar = Column()

    class TestTable(FooTable, BarTable):
        another = Column()

    t = TestTable([])
    assert [c.name for c in t.columns] == ['foo', 'bar', 'another']


def test_output():

    is_report = False

    class TestTable(Table):

        class Meta:
            attrs = dict(id='table_id')

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

    verify_table_html(TestTable(data), """
        <table class="listview" id="table_id">
            <thead>
                <tr>
                    <th class="superheader first_column" colspan="1"> </th>
                    <th class="superheader" colspan="1"> </th>
                    <th class="superheader" colspan="2"> group </th>
                    <th class="superheader" colspan="1"> </th>
                </tr>
                <tr>
                    <th class="subheader first_column">
                        <a href="?order=foo"> Foo </a>
                    </th>
                    <th class="subheader first_column">
                        <a href="?order=bar"> Bar </a>
                    </th>
                    <th class="thin subheader first_column"> </th>
                    <th class="thin subheader" title="Edit"> </th>
                    <th class="thin subheader first_column" title="Delete"> </th>
                </tr>
            </thead>
            <tr class="row1">
                <td> Hello räksmörgås &gt;&lt;&amp;&gt; </td>
                <td class="rj"> 17 </td>
                <td> <i class="fa fa-lg fa-history"> </i> </td>
                <td> <a href="/somewhere/edit/"> <i class="fa fa-lg fa-pencil-square-o" title="Edit"> </i> </a> </td>
                <td> <a href="/somewhere/delete/"> <i class="fa fa-lg fa-trash-o" title="Delete"> </i> </a> </td>
            </tr>
        </table>
        """)


def test_name_traversal():
    class TestTable(Table):
        foo__bar = Column(sortable=False)

    data = [Struct(foo=Struct(bar="bar"))]

    verify_table_html(TestTable(data), """
        <table class="listview">
            <thead>
                <tr>
                    <th class="subheader first_column"> Bar </th>
                </tr>
            </thead>
            <tr class="row1">
                <td> bar </td>
            </tr>
        </table>""")


def test_tuple_data():
    class TestTable(Table):

        class Meta:
            sortable = False

        a = Column()
        b = Column()
        c = Column()

    data = [('a', 'b', 'c')]

    verify_table_html(TestTable(data), """
        <table class="listview">
            <thead>
                <tr>
                    <th class="subheader first_column"> A </th>
                    <th class="subheader first_column"> B </th>
                    <th class="subheader first_column"> C </th>
                </tr>
            </thead>
            <tr class="row1">
                <td> a </td>
                <td> b </td>
                <td> c </td>
            </tr>
        </table>""")


def test_dict_data():
    class TestTable(Table):
        class Meta:
            sortable = False
        a = Column()
        b = Column()
        c = Column()

    data = [{'a': 'a', 'b': 'b', 'c': 'c'}]

    verify_table_html(TestTable(data), """
        <table class="listview">
             <thead>
                 <tr>
                     <th class="subheader first_column"> A </th>
                     <th class="subheader first_column"> B </th>
                     <th class="subheader first_column"> C </th>
                 </tr>
             </thead>
             <tr class="row1">
                 <td> a </td>
                 <td> b </td>
                 <td> c </td>
             </tr>
         </table>""")


class NoSortTable(Table):
    class Meta:
        sortable = False


def test_display_name():
    class TestTable(NoSortTable):
        foo = Column(display_name="Bar")

    data = [Struct(foo="foo")]

    verify_table_html(TestTable(data), """
        <table class="listview">
            <thead>
                <tr>
                    <th class="subheader first_column"> Bar </th>
                </tr>
            </thead>
            <tr class="row1">
                <td> foo </td>
            </tr>
        </table>""")


def test_css_class():
    class TestTable(NoSortTable):
        foo = Column(css_class="some_class")

    data = [Struct(foo="foo")]

    verify_table_html(TestTable(data), """
    <table class="listview">
        <thead>
            <tr><th class="some_class subheader first_column"> Foo </th></tr>
        </thead>
        <tr class="row1">
            <td> foo </td>
        </tr>
    </table>""")


def test_header_url():
    class TestTable(NoSortTable):
        foo = Column(url="/some/url")

    data = [Struct(foo="foo")]

    verify_table_html(TestTable(data), """
    <table class="listview">
        <thead>
            <tr><th class="subheader first_column">
                <a href="/some/url"> Foo </a>
            </th></tr>
        </thead>
        <tr class="row1">
            <td> foo </td>
        </tr>
    </table>""")


def test_title():
    class TestTable(NoSortTable):
        foo = Column(title="Some title")

    data = [Struct(foo="foo")]

    verify_table_html(TestTable(data), """
    <table class="listview">
        <thead>
            <tr><th class="subheader first_column" title="Some title"> Foo </th></tr>
        </thead>
        <tr class="row1">
            <td> foo </td>
        </tr>
    </table>""")


def test_show():
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column(show=False)

    data = [Struct(foo="foo", bar="bar")]

    verify_table_html(TestTable(data), """
    <table class="listview">
        <thead>
            <tr><th class="subheader first_column"> Foo </th></tr>
        </thead>
        <tr class="row1">
            <td> foo </td>
        </tr>
    </table>""")


def test_attr():
    class TestTable(NoSortTable):
        foo = Column()
        bar = Column(attr='foo')

    data = [Struct(foo="foo")]

    verify_table_html(TestTable(data), """
    <table class="listview">
        <thead>
            <tr>
                <th class="subheader first_column"> Foo </th>
                <th class="subheader first_column"> Bar </th>
            </tr>
        </thead>
        <tr class="row1">
            <td> foo </td>
            <td> foo </td>
        </tr>
    </table>""")


def test_attrs():
    class TestTable(NoSortTable):
        class Meta:
            attrs = {
                'class': 'classy',
                'foo': 'bar'
            }
            row_attrs = {
                'class': 'classier',
                'foo': lambda row: "barier"
            }

        yada = Column()

    verify_table_html(TestTable([(1,), (2,)]), """
        <table class="classy" foo="bar">
            <thead>
                <tr>
                  <th class="subheader first_column"> Yada </th>
                </tr>
            </thead>
                <tr class="row1 classier" foo="barier">
                    <td> 1 </td>
                </tr>
                <tr class="row2 classier" foo="barier">
                    <td> 2 </td>
                </tr>
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
        check = Column.check(is_report)
        link = Column.link(cell_format="Yadahada name")
        number = Column.number()

    data = [Struct(pk=123,
                   get_absolute_url=lambda: "http://yada/",
                   check=lambda: True,
                   link=Struct(get_absolute_url=lambda: "http://yadahada/"),
                   number=123)]
    verify_table_html(TestTable(data), """
        <table class="listview">
            <thead>
                <tr>
                    <th class="thin subheader first_column" />
                    <th class="thin subheader first_column" title="Edit" />
                    <th class="thin subheader first_column" title="Delete" />
                    <th class="thin subheader first_column" title="Download" />
                    <th class="thin subheader first_column" title="Run"> Run </th>
                    <th class="thin nopad subheader first_column" title="Select all">
                        <i class="fa fa-check-square-o" />
                    </th>
                    <th class="subheader first_column"> Check </th>
                    <th class="subheader first_column"> Link </th>
                    <th class="subheader first_column"> Number </th>
                </tr>
            </thead>
            <tr class="row1" data-pk="123">
                <td> <i class="fa fa-lg fa-False" /> </td>
                <td> <a href="http://yada/edit/"> <i class="fa fa-lg fa-pencil-square-o" title="Edit" /> </a> </td>
                <td> <a href="http://yada/delete/"> <i class="fa fa-lg fa-trash-o" title="Delete" /> </a> </td>
                <td> <a href="http://yada/download/"> <i class="fa fa-lg fa-download" title="Download" /> </a> </td>
                <td> <a href="http://yada/run/"> Run </a> </td>
                <td> <input class="checkbox" name="pk_123" type="checkbox"/> </td> <td class="cj"> <i class="fa fa-check" title="Yes" /> </td>
                <td> <a href="http://yadahada/"> Yadahada name </a> </td>
                <td class="rj"> 123 </td>
            </tr>
        </table>""")


@pytest.mark.django_db
def test_django_table_pagination():

    for x in xrange(30):
        Foo(a=x, b="").save()

    class TestTable(Table):
        a = Column.number(sortable=False)  # turn off sorting to not get the link with random query params

    verify_table_html(TestTable(Foo.objects.all()),
                      query=dict(page_size=2, page=2),
                      expected_html="""
        <table class="listview">
            <thead>
                <tr>
                    <th class="subheader first_column"> A </th>
                </tr>
            </thead>
            <tr class="row1" data-pk="3">
                <td class="rj"> 2 </td>
            </tr>
            <tr class="row2" data-pk="4">
                <td class="rj"> 3 </td>
            </tr>
        </table>""")


def test_links():
    class TestTable(NoSortTable):
        foo = Column(title="Some title")

    links = [
        Link('Foo', url='/foo/', show=False),
        Link('Bar', url='/bar/'),
        Link('Baz', url='/bar/', group='Other'),
        Link('Qux', url='/bar/', group='Other'),
        Link.icon('icon_foo', title='Icon foo', url='/icon_foo/'),
    ]

    data = [Struct(foo="foo")]

    verify_table_html(TestTable(data),
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

            <a href="/icon_foo/"> <i class="fa fa-icon_foo" /> Icon foo </a>
        </div>""")


@pytest.mark.django_db
def test_bulk_edit():

    Foo(a=1, b="").save()
    Foo(a=2, b="").save()
    Foo(a=3, b="").save()
    Foo(a=4, b="").save()

    class TestTable(Table):
        a = Column.number(sortable=False, bulk=True)  # turn off sorting to not get the link with random query params
        b = Column(bulk=True)

    render_table(request=RequestFactory(HTTP_REFERER='/').post("/", dict(pk_1='', pk_2='', a='0', b='changed')), table=TestTable(Foo.objects.all()))

    assert [(x.pk, x.a, x.b) for x in Foo.objects.all()] == [
        (1, 0, u'changed'),
        (2, 0, u'changed'),
        (3, 3, u''),
        (4, 4, u''),
    ]


def test_cell_template():
    class TestTable(NoSortTable):
        foo = Column(cell_template='test_cell_template.html')

    data = [Struct(foo="foo")]

    verify_table_html(TestTable(data), """
        <table class="listview">
            <thead>
                <tr><th class="subheader first_column"> Foo </th></tr>
            </thead>
            <tr class="row1">
                <td>
                    test_cell_template.html contents
                </td>
            </tr>
        </table>""")


def test_auto_rowspan():
    class TestTable(NoSortTable):
        foo = Column(auto_rowspan=True)

    data = [
        Struct(foo=1),
        Struct(foo=1),
        Struct(foo=2),
        Struct(foo=2),
    ]

    verify_table_html(TestTable(data), """
        <table class="listview">
            <thead>
                <tr><th class="subheader first_column"> Foo </th></tr>
            </thead>
            <tr class="row1">
                <td rowspan="2"> 1 </td>
            </tr>
            <tr class="row2">
                <td style="display: none"> 1 </td>
            </tr>
            <tr class="row1">
                <td rowspan="2"> 2 </td>
            </tr>
            <tr class="row2">
                <td style="display: none"> 2 </td>
            </tr>
        </table>""")


@pytest.mark.django_db
def test_django_filters():

    a = Foo.objects.create(a=1, b="a")
    b = Foo.objects.create(a=2, b="b")
    c = Foo.objects.create(a=3, b="c")
    d = Foo.objects.create(a=4, b="d")

    Bar(foo=a, foo2=a, foo3=a, c=True).save()
    Bar(foo=b, foo2=b, foo3=b, c=False).save()
    Bar(foo=c, foo2=c, foo3=c, c=False).save()
    Bar(foo=d, foo2=d, foo3=d, c=False).save()

    class TestTable(Table):
        foo = Column()
        foo2 = Column(filter_choices=[('a', 'a'), ('b', 'b')])
        foo3 = Column(show=False, filter_choices=Foo.objects.all())
        c = Column()
        foo__a = Column.number()
        foo__b = Column(filter_type=Column.FILTER_TYPES.CONTAINS)

        class Meta:
            # turn off sorting to not get the link with random query params
            sortable = False

    verify_table_html(TestTable(Bar.objects.all()), """
        <form action="." method="get">
            <div class="compact">
                <div class="key-value">
                    <div>
                        <label for="id_foo">
                            Foo:
                        </label>
                    </div>
                    <select id="id_foo" name="foo">
                        <option selected="selected" value="">
                            ---------
                        </option>
                        <option value="1">
                            Foo(1, a)
                        </option>
                        <option value="2">
                            Foo(2, b)
                        </option>
                        <option value="3">
                            Foo(3, c)
                        </option>
                        <option value="4">
                            Foo(4, d)
                        </option>
                    </select>
                </div>
                <div class="key-value">
                    <div>
                        <label for="id_foo2">
                            Foo2:
                        </label>
                    </div>
                    <select id="id_foo2" name="foo2">
                        <option selected="selected" value="">
                        </option>
                        <option value="a">
                            a
                        </option>
                        <option value="b">
                            b
                        </option>
                    </select>
                </div>
                <div class="key-value">
                    <div>
                        <label for="id_foo3">
                            Foo3:
                        </label>
                    </div>
                    <select id="id_foo3" name="foo3">
                        <option selected="selected" value="">
                        </option>
                        <option value="1">
                            Foo(1, a)
                        </option>
                        <option value="2">
                            Foo(2, b)
                        </option>
                        <option value="3">
                            Foo(3, c)
                        </option>
                        <option value="4">
                            Foo(4, d)
                        </option>
                    </select>
                </div>
                <div class="key-value">
                    <div>
                        <label for="id_c">
                            C:
                        </label>
                    </div>
                    <select id="id_c" name="c">
                        <option selected="selected" value="">
                        </option>
                        <option value="1">
                            Yes
                        </option>
                        <option value="0">
                            No
                        </option>
                    </select>
                </div>
                <div class="key-value">
                    <div>
                        <label for="id_foo__a">
                            A:
                        </label>
                    </div>
                    <input id="id_foo__a" name="foo__a" type="number" value="1"/>
                </div>
                <div class="key-value">
                    <div>
                        <label for="id_foo__b">
                            B:
                        </label>
                    </div>
                    <input id="id_foo__b" maxlength="255" name="foo__b" type="text"/>
                </div>
                <div class="submit">
                    <input class="button" type="submit" value="Filter"/>
                </div>
            </div>
        </form>""",
        query=dict(foo__a=1),
        find=dict(),
    )

    # case insensitive search
    verify_table_html(TestTable(Bar.objects.all()), """
        <table class="listview">
            <thead>
                <tr>
                    <th class="subheader first_column">
                        Foo
                    </th>
                    <th class="subheader first_column">
                        Foo2
                    </th>
                    <th class="subheader first_column">
                        C
                    </th>
                    <th class="subheader first_column">
                        A
                    </th>
                    <th class="subheader first_column">
                        B
                    </th>
                </tr>
            </thead>
            <tr class="row1" data-pk="1">
                <td>
                    Foo(1, a)
                </td>
                <td>
                    Foo(1, a)
                </td>
                <td>
                    Yes
                </td>
                <td class="rj">
                    1
                </td>
                <td>
                    a
                </td>
            </tr>
        </table>""",
        query=dict(foo__b='A'),
    )


def test_render_table_to_response():
    class TestTable(NoSortTable):
        foo = Column(display_name="Bar")

    data = [Struct(foo="foo")]

    response = render_table_to_response(RequestFactory().get('/'), TestTable(data))
    assert isinstance(response, HttpResponse)
    assert '<table' in response.content