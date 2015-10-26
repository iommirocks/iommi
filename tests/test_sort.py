import pytest

from .helpers import verify_table_html
from tests.models import Foo
from tri.tables import Column, Table, Struct, order_by_on_list


def test_sort_list():

    class TestTable(Table):
        foo = Column()
        bar = Column.number(sort_key=lambda row: abs(row.bar))

    data = [Struct(foo='c', bar=3),
            Struct(foo='b', bar=-2),
            Struct(foo='a', bar=1)]

    verify_table_html(TestTable(data),
                      query=dict(order='bar'),
                      expected_html="""\
      <table class="listview">
        <thead>
          <tr>
            <th class="subheader first_column">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="subheader sorted_column first_column">
              <a href="?order=-bar"> Bar </a>
            </th>
          </tr>
        </thead>
        <tr class="row1">
          <td> a </td>
          <td class="rj"> 1 </td>
        </tr>
        <tr class="row2">
          <td> b </td>
          <td class="rj"> -2 </td>
        </tr>
        <tr class="row1">
          <td> c </td>
          <td class="rj"> 3 </td>
        </tr>
      </table>
    """)


def test_sort_default_desc_no_sort():

    class TestTable(Table):
        foo = Column()
        bar = Column(sort_default_desc=True)

    verify_table_html(TestTable(data=[]),
                      query=dict(),
                      find=dict(name='thead'),
                      expected_html="""\
        <thead>
          <tr>
            <th class="subheader first_column">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="subheader first_column">
              <a href="?order=-bar"> Bar </a>
            </th>
        </thead>
    """)


def test_sort_default_desc_other_col_sorted():

    class TestTable(Table):
        foo = Column()
        bar = Column(sort_default_desc=True)

    verify_table_html(TestTable([]),
                      query=dict(order='foo'),
                      find=dict(name='thead'),
                      expected_html="""\
        <thead>
          <tr>
            <th class="subheader sorted_column first_column">
              <a href="?order=-foo"> Foo </a>
            </th>
            <th class="subheader first_column">
              <a href="?order=-bar"> Bar </a>
            </th>
        </thead>
    """)


def test_sort_default_desc_already_sorted():

    class TestTable(Table):
        foo = Column()
        bar = Column(sort_default_desc=True)

    verify_table_html(TestTable([]),
                      query=dict(order='bar'),
                      find=dict(name='thead'),
                      expected_html="""\
        <thead>
          <tr>
            <th class="subheader first_column">
              <a href="?order=foo"> Foo </a>
            </th>
            <th class="subheader sorted_column first_column">
              <a href="?order=-bar"> Bar </a>
            </th>
        </thead>
    """)


@pytest.mark.django_db
def test_django_table():

    Foo(a=4711, b="c").save()
    Foo(a=17, b="a").save()
    Foo(a=42, b="b").save()

    class TestTable(Table):
        a = Column.number()
        b = Column()

    verify_table_html(TestTable(Foo.objects.all()),
                      query=dict(order='a'),
                      expected_html="""\
    <table class="listview">
      <thead>
        <tr>
          <th class="subheader sorted_column first_column">
            <a href="?order=-a"> A </a>
          </th>
          <th class="subheader first_column">
            <a href="?order=b"> B </a>
          </th>
        </tr>
      </thead>
      <tr class="row1" data-pk="2">
        <td class="rj"> 17 </td>
        <td> a </td>
      </tr>
      <tr class="row2" data-pk="3">
        <td class="rj"> 42 </td>
        <td> b </td>
      </tr>
      <tr class="row1" data-pk="1">
        <td class="rj"> 4711 </td>
        <td> c </td>
      </tr>
    </table>
    """)


def test_order_by_on_list_nested():
    data = [Struct(foo=Struct(bar='c')),
            Struct(foo=Struct(bar=lambda: 'b')),
            Struct(foo=lambda: Struct(bar='a'))]

    sorted_data = data[:]
    order_by_on_list(sorted_data, 'foo__bar')
    assert sorted_data == list(reversed(data))
