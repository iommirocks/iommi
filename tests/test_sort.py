from django.conf import settings
import pytest

from .helpers import verify_table_html
from tri.tables import Column, Table, Struct


@pytest.fixture(autouse=True)
def template_debug():
    """
    Cause exceptions during rendering to fail test with traceback
    """
    settings.TEMPLATE_DEBUG = True


def test_sort_list():
    columns = [
        Column(name="foo"),
        Column.number(name="bar", sort_key=lambda row: abs(row.bar))
    ]

    verify_table_html(Table([Struct(foo='c', bar=3),
                             Struct(foo='b', bar=-2),
                             Struct(foo='a', bar=1)], columns),
                      data=dict(order='bar'),
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


def test_sort_query():
    pass
