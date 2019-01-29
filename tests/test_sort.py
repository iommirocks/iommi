from __future__ import unicode_literals

import pytest

from tests.helpers import verify_table_html
from tests.models import Foo
from tri.table import Column, Table, Struct, order_by_on_list


def test_sort_list():

    class TestTable(Table):
        foo = Column()
        bar = Column.number(sort_key='bar')

    data = [Struct(foo='c', bar=3),
            Struct(foo='b', bar=2),
            Struct(foo='a', bar=1)]

    verify_table_html(table=TestTable(data=data),
                      query=dict(order='bar'),
                      expected_html="""\
      <table class="listview">
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="ascending first_column sorted_column subheader">
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
    """)

    # now reversed
    verify_table_html(table=TestTable(data=data),
                      query=dict(order='-bar'),
                      expected_html="""\
      <table class="listview">
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="descending first_column sorted_column subheader">
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
    """)


def test_sort_with_name():

    class TestTable(Table):
        class Meta:
            name = 'my_table'

        foo = Column()
        bar = Column.number(sort_key='bar')

    data = [Struct(foo='c', bar=3),
            Struct(foo='b', bar=2),
            Struct(foo='a', bar=1)]

    verify_table_html(table=(TestTable(data=data)),
                      query={'my_table/order': 'bar'},
                      expected_html="""\
      <table class="listview">
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?my_table%2Forder=foo"> Foo </a>
            </th>
            <th class="ascending first_column sorted_column subheader">
              <a href="?my_table%2Forder=-bar"> Bar </a>
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
    """)


def test_sort_list_with_none_values():
    class TestTable(Table):
        foo = Column()
        bar = Column.number(sort_key='bar')

    data = [Struct(foo='c', bar=3),
            Struct(foo='b', bar=2),
            Struct(foo='a', bar=None),
            Struct(foo='a', bar=None)]

    verify_table_html(table=TestTable(data=data),
                      query=dict(order='bar'),
                      expected_html="""\
      <table class="listview">
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="ascending first_column sorted_column subheader">
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
    """)


def test_sort_list_bad_parameter():

    class TestTable(Table):
        foo = Column()
        bar = Column.number(sort_key='bar')

    data = [Struct(foo='b', bar=2),
            Struct(foo='a', bar=1)]

    verify_table_html(table=TestTable(data=data),
                      query=dict(order='barfology'),
                      expected_html="""\
      <table class="listview">
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
    """)


@pytest.mark.django_db
def test_sort_django_table():

    Foo(a=4711, b="c").save()
    Foo(a=17, b="a").save()
    Foo(a=42, b="b").save()

    class TestTable(Table):
        a = Column.number()
        b = Column()

    verify_table_html(table=TestTable(data=Foo.objects.all()),
                      query=dict(order='a'),
                      expected_html="""\
    <table class="listview">
      <thead>
        <tr>
          <th class="ascending first_column sorted_column subheader">
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
    """)

    # now reversed
    verify_table_html(table=TestTable(data=Foo.objects.all()),
                      query=dict(order='-a'),
                      expected_html="""\
    <table class="listview">
      <thead>
        <tr>
          <th class="descending first_column sorted_column subheader">
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
    """)


def test_order_by_on_list_nested():
    data = [Struct(foo=Struct(bar='c')),
            Struct(foo=Struct(bar='b')),
            Struct(foo=Struct(bar='a'))]

    sorted_data = data[:]
    order_by_on_list(sorted_data, 'foo__bar')
    assert sorted_data == list(reversed(data))

    order_by_on_list(sorted_data, lambda x: x.foo.bar)
    assert sorted_data == list(reversed(data))


def test_sort_default_desc_no_sort():

    class TestTable(Table):
        foo = Column()
        bar = Column(sort_default_desc=True)

    verify_table_html(table=TestTable(data=[]),
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
    """)


def test_sort_default_desc_other_col_sorted():

    class TestTable(Table):
        foo = Column()
        bar = Column(sort_default_desc=True)

    verify_table_html(table=TestTable([]),
                      query=dict(order='foo'),
                      find=dict(name='thead'),
                      expected_html="""\
        <thead>
          <tr>
            <th class="ascending first_column sorted_column subheader">
              <a href="?order=-foo"> Foo </a>
            </th>
            <th class="first_column subheader">
              <a href="?order=-bar"> Bar </a>
            </th>
        </thead>
    """)


def test_sort_default_desc_already_sorted():

    class TestTable(Table):
        foo = Column()
        bar = Column(sort_default_desc=True)

    verify_table_html(table=TestTable([]),
                      query=dict(order='bar'),
                      find=dict(name='thead'),
                      expected_html="""\
        <thead>
          <tr>
            <th class="first_column subheader">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="ascending first_column sorted_column subheader">
              <a href="?order=-bar"> Bar </a>
            </th>
        </thead>
    """)


@pytest.mark.django_db
def test_sort_django_table_from_model():

    Foo(a=4711, b="c").save()
    Foo(a=17, b="a").save()
    Foo(a=42, b="b").save()

    verify_table_html(table__data=Foo.objects.all(),
                      query=dict(order='a'),
                      expected_html="""\
    <table class="listview">
      <thead>
        <tr>
          <th class="ascending first_column sorted_column subheader">
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
    """)
