import pytest

from tests.helpers import verify_table_html
from tests.models import TFoo
from iommi.table import Column, Table, Struct, order_by_on_list


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
      <table class="table" data-endpoint="/tbody">
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
    """)

    # now reversed
    verify_table_html(
        table=TestTable(rows=rows),
        query=dict(order='-bar'),
        expected_html="""\
      <table class="table" data-endpoint="/tbody">
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
    """)


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
      <table class="table" data-endpoint="/tbody">
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
    """)


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
      <table class="table" data-endpoint="/tbody">
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
    """)


def test_sort_list_bad_parameter():

    class TestTable(Table):
        foo = Column()
        bar = Column.number(sort_key='bar')

    rows = [
        Struct(foo='b', bar=2),
        Struct(foo='a', bar=1),
    ]

    verify_table_html(table=TestTable(rows=rows),
                      query=dict(order='barfology'),
                      expected_html="""\
      <table class="table" data-endpoint="/tbody">
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
    <table class="table" data-endpoint="/tbody">
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
    """)

    # now reversed
    verify_table_html(
        table=TestTable(rows=TFoo.objects.all()),
        query=dict(order='-a'),
        expected_html="""\
    <table class="table" data-endpoint="/tbody">
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
    """)


def test_order_by_on_list_nested():
    rows = [
        Struct(foo=Struct(bar='c')),
        Struct(foo=Struct(bar='b')),
        Struct(foo=Struct(bar='a')),
    ]

    sorted_rows = rows[:]
    order_by_on_list(sorted_rows, 'foo__bar')
    assert sorted_rows == list(reversed(rows))

    order_by_on_list(sorted_rows, lambda x: x.foo.bar)
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
    """)


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
    """)


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
    """)


@pytest.mark.django_db
def test_sort_django_table_from_model():

    TFoo(a=4711, b="c").save()
    TFoo(a=17, b="a").save()
    TFoo(a=42, b="b").save()

    verify_table_html(
        table__auto__rows=TFoo.objects.all(),
        query=dict(order='a'),
        expected_html="""\
    <table class="table" data-endpoint="/tbody">
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
    """)
