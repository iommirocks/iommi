import pytest
from iommi.struct import Struct

from iommi.declarative.namespace import Namespace
from iommi.edit_table import (
    EditColumn,
    EditTable,
)
from iommi.form import (
    Field,
    Form,
)
from iommi.table import (
    Column,
)
from tests.helpers import (
    req,
    verify_html,
    verify_table_html,
)
from tests.models import (
    TBar,
    TBaz,
    TFoo,
)


def test_no_longer_experimental():
    with pytest.raises(
        Exception,
        match='EditTable/EditColumn has moved out of iommi.experimental. '
        'Update imports and remove the .experimental part.',
    ):
        # noinspection PyUnresolvedReferences
        import iommi.experimental.edit_table  # noqa


@pytest.mark.django_db
def test_edit_table():
    edit_table = EditTable(
        sortable=False,
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
        find__method='post',
        # language=html
        expected_html="""
            <form enctype="multipart/form-data" method="post">
                <div class="iommi-table-container">
                    <div class="iommi-table-plus-paginator">
                        <table class="table" data-add-template=\'&lt;tr data-pk="#sentinel#"&gt;&lt;td&gt;&lt;input id="id_editable_thing__#sentinel#" name="editable_thing/#sentinel#" type="text" value=""&gt;&lt;/td&gt;
&lt;td&gt;&lt;/td&gt;&lt;/tr&gt;\' data-endpoint="/endpoints/tbody" data-iommi-id="" data-next-virtual-pk="-1">
                            <thead>
                                <tr>
                                    <th class="first_column subheader"> Editable thing </th>
                                    <th class="first_column subheader"> Readonly thing </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr data-pk="1">
                                    <td> <input id="id_editable_thing__1" name="editable_thing/1" type="text" value="foo"/> </td>
                                    <td> bar </td>
                                </tr>
                                <tr data-pk="2">
                                    <td> <input id="id_editable_thing__2" name="editable_thing/2" type="text" value="baz"/> </td>
                                    <td> buzz </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="links">
                    <button accesskey="s" name="-submit"> Save </button>
                    <div style="display: none"> Csrf </div>
                    <button onclick="iommi_add_row(this); return false"> Add row </button>
                </div>
            </form>
        """,
    )


@pytest.mark.django_db
def test_edit_table_nested():
    form = Form(
        fields__edit_table=EditTable(
            sortable=False,
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
        ),
    )

    html = form.bind(request=req('get')).__html__()
    assert html.count('<form') == 1


@pytest.mark.django_db
def test_edit_table_post():
    rows = [
        Struct(
            pk=1,
            editable_thing='foo',
            readonly_thing='bar',
            save=lambda **_: None,
        ),
        Struct(
            pk=2,
            editable_thing='baz',
            readonly_thing='buzz',
            save=lambda **_: None,
        ),
    ]

    post_save_was_called = False

    def post_save(**_):
        nonlocal post_save_was_called
        post_save_was_called = True

    edit_table = EditTable(
        columns=dict(
            editable_thing=EditColumn(
                edit=Namespace(
                    call_target=Field,
                    is_valid=lambda parsed_data, **_: (parsed_data != 'invalid', 'error-string'),
                ),
            ),
            readonly_thing=EditColumn(),
        ),
        rows=rows,
        extra__post_save=post_save,
    )

    # Check validation errors
    bound = edit_table.bind(
        request=req(
            'POST',
            **{
                'editable_thing/1': 'invalid',
                'editable_thing/2': 'fusk',
                '-submit': '',
            },
        )
    )
    response = bound.render_to_response()
    assert response.status_code == 200
    assert 'error-string' in response.content.decode()

    # No rows should be modified
    assert rows[0].editable_thing == 'foo'
    assert rows[1].editable_thing == 'baz'

    # Now edit for real
    bound = edit_table.bind(
        request=req(
            'POST',
            **{
                'editable_thing/1': 'fisk',
                'editable_thing/2': 'fusk',
                '-submit': '',
            },
        )
    )
    response = bound.render_to_response()
    assert response.status_code == 302

    assert rows[0].editable_thing == 'fisk'
    assert rows[1].editable_thing == 'fusk'

    assert post_save_was_called


@pytest.mark.django_db
def test_edit_table_related_objects():
    baz = TBaz.objects.create()
    foo = TFoo.objects.create(a=1)
    baz.foo.set([foo, TFoo.objects.create(a=2)])

    edit_table = EditTable(
        rows=TBaz.objects.all(),
        columns__foo=EditColumn(
            edit=Namespace(
                call_target=Field.many_to_many,
                model_field=TBaz.foo.field,
            )
        ),
    )

    bound = edit_table.bind(
        request=req(
            'POST',
            **{
                'columns/foo/1': str(baz.pk),
                '-actions/submit': '',
            },
        )
    )
    response = bound.render_to_response()
    assert response.status_code == 302
    assert list(baz.foo.all()) == [foo]


def test_edit_table_definition():
    class MyEditTable(EditTable):
        foo = EditColumn(edit=None)
        bar = EditColumn(edit=Field())
        baz = EditColumn(edit=dict(call_target=Field))
        vanilla = Column()

    my_edit_table = MyEditTable(
        columns=dict(
            bing=EditColumn(edit=None),
            bang=EditColumn(edit=Field()),
            bong=EditColumn(edit=dict(call_target=Field)),
        )
    ).bind()

    assert list(my_edit_table.columns) == [
        'foo',
        'bar',
        'baz',
        'vanilla',
        'bing',
        'bang',
        'bong',
    ]

    assert set(my_edit_table.edit_form.fields) == {
        'bar',
        'baz',
        'bang',
        'bong',
    }


def test_edit_table_from_model():
    table = EditTable(
        auto__model=TFoo,
        columns__a__edit__include=True,
        columns__b__edit__include=False,
    )
    assert list(table.bind().edit_form.fields) == ['a']


def test_edit_table_from_model_implicit_exclude():
    table = EditTable(
        auto__model=TFoo,
        columns__a__edit__include=True,
    )
    assert list(table.bind().edit_form.fields) == ['a']


@pytest.mark.django_db
def test_edit_table_auto_rows():
    table = EditTable(
        auto__rows=TFoo.objects.all(),
        columns__a__edit__include=True,
    )
    assert list(table.bind().edit_form.fields) == ['a']


@pytest.mark.django_db
def test_edit_table_post_create():
    foo_pk = TFoo.objects.create(a=1, b='asd').pk
    edit_table = EditTable(auto__model=TBar).refine_done()
    assert edit_table.bind().actions.submit.iommi_path == 'actions/submit'
    # language=html
    verify_html(
        actual_html=edit_table.bind().attrs['data-add-template'],
        # language=html
        expected_html='''
            <tr data-pk="#sentinel#">
                <td>
                    <select class="select2_enhance" id="id_columns__foo__#sentinel#" name="columns/foo/#sentinel#" data-placeholder="" data-choices-endpoint="/create_form/foo/choices"></select>
                </td>
                <td>
                    <input id="id_columns__c__#sentinel#" name="columns/c/#sentinel#" type="checkbox">
                </td>
            </tr>
        ''',
    )

    assert not TBar.objects.exists()

    edit_table = edit_table.bind(
        request=req(
            'POST',
            **{
                'columns/foo/-1': f'{foo_pk}',
                'columns/c/-1': 'true',
                '-actions/submit': '',
            },
        )
    )
    assert not edit_table.get_errors()
    response = edit_table.render_to_response()
    assert response.status_code == 302

    obj = TBar.objects.get()
    assert obj.pk >= 0
    assert obj.foo.pk == foo_pk
    assert obj.c is True


@pytest.mark.django_db
def test_edit_table_post_delete():
    tfoo = TFoo.objects.create(a=1, b='asd')
    edit_table = EditTable(auto__model=TFoo, columns__delete=EditColumn.delete()).refine_done()
    assert edit_table.bind().actions.submit.iommi_path == 'actions/submit'

    response = edit_table.bind(request=req('GET')).render_to_response()
    assert f'name="pk_delete_{tfoo.pk}"' in response.content.decode()

    response = edit_table.bind(
        request=req(
            'POST',
            **{
                f'pk_delete_{tfoo.pk}': '',
                '-actions/submit': '',
            },
        )
    ).render_to_response()
    assert response.status_code == 302

    assert TFoo.objects.all().count() == 0


# TODO: attr=None on a column crashes
