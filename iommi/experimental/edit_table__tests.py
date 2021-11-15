import pytest
from tri_declarative import Namespace
from tri_struct import Struct

from iommi import Field
from iommi.experimental.edit_table import (
    EditColumn,
    EditTable,
)
from tests.helpers import (
    req,
    verify_table_html,
)


@pytest.mark.django_db
def test_formset_table():
    edit_table = EditTable(
        columns=dict(
            editable_thing=EditColumn(
                edit=Namespace(call_target=Field),
            ),
            readonly_thing=EditColumn(),
        ),
        rows=[
            Struct(pk=1, editable_thing='foo', readonly_thing='bar'),
            Struct(pk=2, editable_thing='baz', readonly_thing='buzz'),
        ],
    )

    verify_table_html(
        table=edit_table.bind(request=req('get')),
        # language=html
        expected_html="""
            <table class="table" data-endpoint="/endpoints/tbody" data-iommi-id="">
                <thead>
                    <tr>
                        <th class="first_column subheader">
                            <a href="?order=editable_thing">
                                Editable thing
                            </a>
                        </th>
                        <th class="first_column subheader">
                            <a href="?order=readonly_thing">
                                Readonly thing
                            </a>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr data-pk="1">
                        <td>
                             <input id="id_edit_form__editable_thing__1" name="edit_form/editable_thing/1" type="text" value="foo"/>
                        </td>
                        <td>
                            bar
                        </td>
                    </tr>
                    <tr data-pk="2">
                        <td>
                            <input id="id_edit_form__editable_thing__2" name="edit_form/editable_thing/2" type="text" value="baz"/>
                        </td>
                        <td>
                            buzz
                        </td>
                    </tr>
                </tbody>
            </table>
        """
    )
