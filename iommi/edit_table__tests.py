import html
import json
import pytest

from docs.models import (
    Album,
    Artist,
    FavoriteArtist,
)
from iommi.declarative.namespace import Namespace
from iommi.edit_table import (
    EditColumn,
    EditTable,
)
from iommi.form import (
    Field,
    Form,
    save_nested_forms,
)
from iommi.struct import Struct
from iommi.table import (
    Column,
)
from tests.helpers import (
    req,
    verify_html,
    verify_table_html,
    verify_part_html,
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


def test_edit_table_rendering():
    edit_table = EditTable(
        sortable=False,
        columns=dict(
            editable_thing=EditColumn(
                field=Namespace(call_target=Field),
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
            <form action="" enctype="multipart/form-data" method="post">
                <div class="iommi-table-plus-paginator">
                    <table class="table" data-new-row-endpoint="/new_row" data-next-virtual-pk="-1">
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
                <div class="links">
                    <button accesskey="s" name="-save"> Save </button>
                    <button data-iommi-edit-table-add-row-button="" data-iommi-edit-table-path="" type="button"> Add row </button>
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
                    field=Namespace(call_target=Field),
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
                field=Namespace(
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
                '-save': '',
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
                '-save': '',
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
            field=dict(
                call_target=Field.many_to_many,
                model_field=TBaz.foo.field,
            )
        ),
    )

    bound = edit_table.bind(
        request=req(
            'POST',
            **{
                f'columns/foo/{baz.pk}': str(foo.pk),
                '-save': '',
            },
        )
    )
    response = bound.render_to_response()
    assert response.status_code == 302
    assert list(baz.foo.all()) == [foo]


def test_edit_table_definition():
    class MyEditTable(EditTable):
        foo = EditColumn(field=None)
        bar = EditColumn(field=Field())
        baz = EditColumn(field=dict(call_target=Field))
        vanilla = Column()

    my_edit_table = MyEditTable(
        columns=dict(
            bing=EditColumn(field=None),
            bang=EditColumn(field=Field()),
            bong=EditColumn(field=dict(call_target=Field)),
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
        columns__a__field__include=True,
        columns__b__field__include=False,
    )
    assert list(table.bind().edit_form.fields) == ['a']


def test_edit_table_from_model_implicit_exclude():
    table = EditTable(
        auto__model=TFoo,
        columns__a__field__include=True,
    )
    assert list(table.bind().edit_form.fields) == ['a']


@pytest.mark.django_db
def test_edit_table_auto_rows():
    table = EditTable(
        auto__rows=TFoo.objects.all(),
        columns__a__field__include=True,
    )
    assert list(table.bind().edit_form.fields) == ['a']


@pytest.mark.django_db
def test_edit_table_post_create():
    foo_pk = TFoo.objects.create(a=1, b='asd').pk
    edit_table = EditTable(auto__model=TBar).refine_done()

    # language=html
    verify_html(
        actual_html=json.loads(
            edit_table.bind(request=req('get', **{'/new_row': ''})).render_to_response().content
        )['html'],
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
                '-save': '',
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
def test_edit_table_post_create_hardcoded():
    foo = TFoo.objects.create(a=1, b='asd')
    edit_table = EditTable(
        auto__model=TFoo,
        columns__a__field__include=True,
        columns__b=EditColumn.hardcoded(field__parsed_data=lambda **_: 'hardcoded'),
    ).refine_done()
    assert edit_table.bind().edit_actions.save.iommi_path == 'save'

    edit_table = edit_table.bind(
        request=req(
            'POST',
            **{
                # edit
                f'columns/a/{foo.pk}': '2',
                f'columns/b/{foo.pk}': 'hardcoded column should be ignored',
                # create
                'columns/a/-2': '4',
                'columns/b/-2': 'hardcoded column should be ignored',
                'columns/a/-1': '3',
                'columns/b/-1': 'hardcoded column should be ignored',
                '-save': '',
            },
        )
    )
    assert not edit_table.get_errors()
    response = edit_table.render_to_response()
    assert response.status_code == 302

    assert [dict(a=x.a, b=x.b) for x in TFoo.objects.all().order_by('pk')] == [
        dict(a=2, b='asd'),
        dict(a=3, b='hardcoded'),
        dict(a=4, b='hardcoded'),
    ]


@pytest.mark.django_db
def test_edit_table_post_delete():
    tfoo = TFoo.objects.create(a=1, b='asd')
    edit_table = EditTable(auto__model=TFoo, columns__delete=EditColumn.delete()).refine_done()

    response = edit_table.bind(request=req('GET')).render_to_response()
    assert f'name="pk_delete_{tfoo.pk}"' in response.content.decode()

    response = edit_table.bind(
        request=req(
            'POST',
            **{
                f'pk_delete_{tfoo.pk}': '',
                '-save': '',
            },
        )
    ).render_to_response()
    assert response.status_code == 302

    assert TFoo.objects.all().count() == 0


@pytest.mark.django_db
def test_edit_table_delete_new_row_and_existing_row():
    existing_foo = TFoo.objects.create(a=1, b='existing')
    another_foo = TFoo.objects.create(a=2, b='another')

    edit_table = EditTable(
        auto__model=TFoo,
        columns__a__field__include=True,
        columns__b__field__include=True,
        columns__delete=EditColumn.delete(),
    ).refine_done()

    response = edit_table.bind(
        request=req(
            'POST',
            **{
                # First new row data (to be deleted)
                'columns/a/-1': '99',
                'columns/b/-1': 'new row to delete',
                'pk_delete_-1': '',

                # Second new row data (to be kept)
                'columns/a/-2': '88',
                'columns/b/-2': 'new row to keep',

                # Mark existing row for deletion
                f'pk_delete_{existing_foo.pk}': '',
                f'columns/a/{existing_foo.pk}': str(existing_foo.a),
                f'columns/b/{existing_foo.pk}': existing_foo.b,

                # Data for the other existing row (unchanged)
                f'columns/a/{another_foo.pk}': str(another_foo.a),
                f'columns/b/{another_foo.pk}': another_foo.b,
                '-save': '',
            },
        )
    ).render_to_response()

    assert response.status_code == 302
    assert not TFoo.objects.filter(pk=existing_foo.pk).exists()
    assert TFoo.objects.filter(pk=another_foo.pk).exists()
    new_row = TFoo.objects.filter(a=88, b='new row to keep').first()
    assert new_row is not None
    assert not TFoo.objects.filter(a=99, b='new row to delete').exists()
    assert TFoo.objects.count() == 2


@pytest.mark.django_db
def test_edit_table_post_row_group(small_discography):
    edit_table = EditTable(
        auto__model=Album,
        columns__artist=dict(
            row_group__include=True,
            render_column=False,
        ),
        columns__year__field__include=True,
    )

    bound = edit_table.bind(
        request=req(
            'POST',
            **{
                f'columns/year/{small_discography[0].pk}': '5',
                f'columns/year/{small_discography[1].pk}': '7',
                '-save': '',
            },
        )
    )
    response = bound.render_to_response()
    assert not edit_table.get_errors()
    assert response.status_code == 302, response.content.decode()
    assert Album.objects.get(pk=small_discography[0].pk).year == 5
    assert Album.objects.get(pk=small_discography[1].pk).year == 7


@pytest.mark.django_db
def test_non_editable():
    TFoo(pk=123, a=1, b='asd').save()
    TFoo(pk=456, a=2, b='fgh').save()

    table = EditTable(
        auto__model=TFoo,
        columns__b__field=dict(
            include=True,
            editable=lambda instance, form, **_: instance and instance.pk == 123,
        ),
    )

    verify_table_html(
        table=table,
        find=dict(name='tbody'),
        # language=html
        expected_html='''
            <tbody>
                <tr data-pk="123">
                    <td class="rj"> 1 </td>
                    <td> <input id="id_columns__b__123" name="columns/b/123" type="text" value="asd"/> </td>
                </tr>
                <tr data-pk="456">
                    <td class="rj"> 2 </td>
                    <td> <input disabled="" id="id_columns__b__456" name="columns/b/456" type="text" value="fgh"/> </td>
                </tr>
            </tbody>
        ''',
    )

    edit_table = table.bind(
        request=req(
            'POST',
            **{
                'columns/a/123': '30',
                'columns/a/456': '40',
                'columns/b/123': 'banana',
                'columns/b/456': 'orange',
                '-save': '',
            },
        )
    )
    assert not edit_table.get_errors()
    response = edit_table.render_to_response()
    assert response.status_code == 302
    assert TFoo.objects.get(pk=123).a == 1
    assert TFoo.objects.get(pk=456).a == 2
    assert TFoo.objects.get(pk=123).b == 'banana'
    assert TFoo.objects.get(pk=456).b == 'fgh'


@pytest.mark.django_db
def test_non_rendered():
    TFoo(pk=321, a=1, b='asd').save()
    TFoo(pk=654, a=2, b='fgh').save()

    table = EditTable(
        auto__model=TFoo,
        columns__a__field=Field.non_rendered(
            initial=lambda instance, **_: 10 if instance and instance.pk == 321 else 20,
        ),
        columns__a__render_column=False,
        columns__b__field__include=True,
    )

    verify_table_html(
        table=table,
        find=dict(name='tbody'),
        # language=html
        expected_html='''
            <tbody>
                <tr data-pk="321">
                    <td> <input id="id_columns__b__321" name="columns/b/321" type="text" value="asd"/> </td>
                </tr>
                <tr data-pk="654">
                    <td> <input id="id_columns__b__654" name="columns/b/654" type="text" value="fgh"/> </td>
                </tr>
            </tbody>
        ''',
    )

    edit_table = table.bind(
        request=req(
            'POST',
            **{
                'columns/a/321': '30',
                'columns/a/654': '40',
                'columns/b/321': 'banana',
                'columns/b/654': 'orange',
                '-save': '',
            },
        )
    )
    assert not edit_table.get_errors()
    response = edit_table.render_to_response()
    assert TFoo.objects.get(pk=321).a == 10
    assert TFoo.objects.get(pk=654).a == 20
    assert TFoo.objects.get(pk=321).b == 'banana'
    assert TFoo.objects.get(pk=654).b == 'orange'


@pytest.mark.django_db
def test_edit_table__auto__rows_1(small_discography):

    edit_table = EditTable(
        auto__rows=Album.objects.all(),
        columns__year__field__include=True,
    )
    edit_table.bind(request=req('get'))


@pytest.mark.django_db
def test_edit_table__auto__rows_2(small_discography):
    edit_table = EditTable(
        auto__rows=Artist.objects.all(),
        auto__include=['name'],
        columns__year__field__include=True,
    )
    edit_table.bind(request=req('get'))

# TODO: attr=None on a column crashes


@pytest.mark.django_db
def test_edit_table_multiple_new_rows_validation_errors_preserved():
    edit_table = EditTable(
        auto__model=Album,
        columns__name__field__include=True,
        columns__name__field__required=True,
        columns__artist__field__include=True,
        columns__year__field__include=True,
    )

    bound_table = edit_table.bind(
        request=req(
            'POST',
            **{
                # First new row - invalid (missing name)
                'columns/name/-1': '',
                'columns/artist/-1': '3',
                'columns/year/-1': '2023',
                # Second new row - valid
                'columns/name/-2': 'Valid Album',
                'columns/artist/-2': '5',
                'columns/year/-2': '2024',
                # Third new row - invalid (missing name)
                'columns/name/-3': '',
                'columns/artist/-3': '3',
                'columns/year/-3': '2025',
                '-save': '',
            }
        )
    )

    response = bound_table.render_to_response()
    assert response.status_code == 200
    assert bound_table.create_errors
    assert not bound_table.is_valid()

    html = response.content.decode()

    # All 3 new rows should still be displayed
    assert 'value="2023"' in html
    assert 'value="2024"' in html
    assert 'value="2025"' in html
    assert 'value="Valid Album"' in html
    assert html.count('This field is required') == 2

    # Verify row order is preserved
    pos_2023 = html.find('value="2023"')
    pos_2024 = html.find('value="2024"')
    pos_2025 = html.find('value="2025"')
    assert pos_2023 < pos_2024 < pos_2025

    assert 'data-next-virtual-pk="-4"' in html
    assert Album.objects.count() == 0


@pytest.mark.django_db
def test_edit_table_create_object_callbacks():
    invoked = []

    def new_instance(form, **_):
        invoked.append('new_instance')
        return form.model()

    edit_table = EditTable(
        auto__model=TFoo,
        columns__a__field__include=True,
        columns__b__field__include=True,
        create_form__extra__new_instance=new_instance,
    ).refine_done()

    edit_table.bind(
        request=req(
            'POST',
            **{
                # create
                'columns/a/-1': '3',
                'columns/b/-1': 'foo bar baz',
                '-save': '',
            },
        )
    ).render_to_response()

    assert 'new_instance' in invoked


@pytest.mark.django_db
def test_lazy_tbody_on_fail():
    dark_funeral = Artist.objects.create(name='Dark Funeral')
    album_2016 = Album.objects.create(name='Where Shadows Forever Reign', artist=dark_funeral, year=2016)

    class ArtistForm(Form):
        class Meta:
            auto__instance = dark_funeral
            auto__include = ['id', 'name']
            fields__name__required = True

    class AlbumsEditTable(EditTable):
        class Meta:
            auto__model = Album
            auto__include = ['name', 'artist', 'year']
            columns__name__field__include = True
            columns__name__field__required = True
            columns__year__field__include = True
            columns__artist__field = Field.non_rendered(initial=dark_funeral)
            columns__artist__render_column = False

    class ParentForm(Form):
        artist = ArtistForm.edit()
        albums = AlbumsEditTable()
        class Meta:
            actions__submit__post_handler = save_nested_forms

    def test_parent_form_save(abort_on_fail):
        parent_form = ParentForm(extra_evaluated__nested_forms_abort_save_on_fail=abort_on_fail).refine_done()
        parent_form = parent_form.bind(
            request=req(
                'POST',
                **{
                    # existing objects
                    'name': dark_funeral.name if not abort_on_fail else '',
                    f'albums/name/{album_2016.pk}': album_2016.name if abort_on_fail else '',
                    f'albums/year/{album_2016.pk}': album_2016.year,
                    # create new
                    'albums/name/-1': 'We Are the Apocalypse',
                    'albums/year/-1': 2021,
                    'albums/name/-2': 'Angelus Exuro pro Eternus' if abort_on_fail else '',
                    'albums/year/-2': 2009,
                    '-submit': '',
                },
            )
        )
        assert not abort_on_fail or parent_form.nested_forms.artist.get_errors()

        parent_form.render_to_response()

        # edit_errors and create_errors are None before render_to_response(),
        # because they get checked in edit_table__post_handler
        assert abort_on_fail or parent_form.nested_forms.albums.edit_errors
        assert abort_on_fail or parent_form.nested_forms.albums.create_errors

        return parent_form

    _form = test_parent_form_save(abort_on_fail=True)
    verify_part_html(
        part=_form,
        # language=HTML
        expected_html=f"""
            <form action="" enctype="multipart/form-data" method="post">
                <div action="" enctype="multipart/form-data" method="post">
                    <h1>Edit artist</h1>
                    <div><label for="id_id">ID</label><input id="id_id" name="id" type="text" value=""></div>
                    <div><label for="id_name">Name</label><input id="id_name" name="name" type="text" value=""><ul><li>This field is required</li></ul></div>
                </div>
            
                <h1>Albums</h1>
                <div class="iommi-table-container" data-endpoint="/albums/tbody" data-iommi-id="albums">
                    <div action="" enctype="multipart/form-data" method="post">
                        <div class="iommi-table-plus-paginator">
                            <table class="table" data-new-row-endpoint="/new_row" data-next-virtual-pk="-3">
                                <thead>
                                    <tr>
                                        <th class="first_column iommi_sort_header subheader"><a href="?albums%2Forder=name">Name</a></th>
                                        <th class="first_column iommi_sort_header subheader"><a href="?albums%2Forder=year">Year</a></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr data-pk="{album_2016.pk}">
                                        <td><input id="id_albums__name__{album_2016.pk}" name="albums/name/{album_2016.pk}" type="text" value="Where Shadows Forever Reign"></td>
                                        <td class="rj"><input id="id_albums__year__{album_2016.pk}" name="albums/year/{album_2016.pk}" type="text" value="2016"></td>
                                    </tr>
                                    <tr data-pk="-1">
                                        <td><input id="id_albums__name__-1" name="albums/name/-1" type="text" value="We Are the Apocalypse"></td>
                                        <td class="rj"><input id="id_albums__year__-1" name="albums/year/-1" type="text" value="2021"></td>
                                    </tr>
                                    <tr data-pk="-2">
                                        <td><input id="id_albums__name__-2" name="albums/name/-2" type="text" value="Angelus Exuro pro Eternus"></td>
                                        <td class="rj"><input id="id_albums__year__-2" name="albums/year/-2" type="text" value="2009"></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <div class="links">
                            <button data-iommi-edit-table-add-row-button data-iommi-edit-table-path="fields__albums" type="button">Add row</button>
                        </div>
                    </div>
                </div>
                <div class="links">
                        <button accesskey="s" name="-submit">Submit</button>
                </div>
            </form>
        """,
    )

    _form = test_parent_form_save(abort_on_fail=False)
    verify_part_html(
        part=_form,
        # language=HTML
        expected_html=f"""
            <form action="" enctype="multipart/form-data" method="post">
                <div action="" enctype="multipart/form-data" method="post">
                    <h1>Edit artist</h1>
                    <div><label for="id_id">ID</label><input id="id_id" name="id" type="text" value=""/></div>
                    <div><label for="id_name">Name</label><input id="id_name" name="name" type="text" value="Dark Funeral"/></div>
                </div>
                <h1>Albums</h1>
                <div class="iommi-table-container" data-endpoint="/albums/tbody" data-iommi-id="albums">
                    <div action="" enctype="multipart/form-data" method="post">
                        <div class="iommi-table-plus-paginator">
                            <table class="table" data-new-row-endpoint="/new_row" data-next-virtual-pk="-3">
                                <thead>
                                    <tr>
                                        <th class="first_column iommi_sort_header subheader"><a href="?albums%2Forder=name">Name</a></th>
                                        <th class="first_column iommi_sort_header subheader"><a href="?albums%2Forder=year">Year</a></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr data-pk="{album_2016.pk}">
                                        <td>
                                            <input id="id_albums__name__{album_2016.pk}" name="albums/name/{album_2016.pk}" type="text" value=""/>
                                            <br/>
                                            <span class="text-danger">
                                                <ul class="errors">
                                                    <li>This field is required</li>
                                                </ul>
                                            </span>
                                        </td>
                                        <td class="rj"><input id="id_albums__year__{album_2016.pk}" name="albums/year/{album_2016.pk}" type="text" value="2016"/></td>
                                    </tr>
                                    <tr data-pk="-1">
                                        <td><input id="id_albums__name__-1" name="albums/name/-1" type="text" value="We Are the Apocalypse"/></td>
                                        <td class="rj"><input id="id_albums__year__-1" name="albums/year/-1" type="text" value="2021"/></td>
                                    </tr>
                                    <tr data-pk="-2">
                                        <td>
                                            <input id="id_albums__name__-2" name="albums/name/-2" type="text" value=""/>
                                            <br/>
                                            <span class="text-danger">
                                                <ul class="errors">
                                                    <li>This field is required</li>
                                                </ul>
                                            </span>
                                        </td>
                                        <td class="rj"><input id="id_albums__year__-2" name="albums/year/-2" type="text" value="2009"/></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <div class="links">
                            <button data-iommi-edit-table-add-row-button="" data-iommi-edit-table-path="fields__albums" type="button">Add row</button>
                        </div>
                    </div>
                </div>
                <div class="links">
                    <button accesskey="s" name="-submit">Submit</button>
                </div>
            </form>
        """,
    )


@pytest.mark.django_db
def test_orderable_edit_table(fav_artists):
    class FavoriteArtists(EditTable):
        class Meta:
            auto__model = FavoriteArtist
            auto__include = ['artist__name', 'comment', 'sort_order']
            columns__comment__field__include = True
            sortable = False

    verify_table_html(
        table=FavoriteArtists().bind(request=req('get')),
        # language=html
        expected_html=f"""
            <table class="table" data-new-row-endpoint="/new_row" data-next-virtual-pk="-1">
                <thead>
                    <tr>
                        <th class="first_column subheader">Name</th>
                        <th class="first_column subheader">Comment</th>
                        <th class="first_column subheader">Sort order</th>
                    </tr>
                </thead>
                <tbody data-iommi-reorderable data-iommi-reorderable-field-selector="[data-reordering-value]" data-iommi-reorderable-handle-selector="[data-iommi-path=&quot;columns__sort_order__cell&quot;]">
                    <tr data-pk="{fav_artists[0].pk}">
                        <td>Black Sabbath</td>
                        <td><input id="id_columns__comment__{fav_artists[0].pk}" name="columns/comment/{fav_artists[0].pk}" type="text" value="Love it!"></td>
                        <td class="reordering-handle-cell" title="Drag and drop to reorder"><input data-reordering-value id="id_columns__sort_order__{fav_artists[0].pk}" name="columns/sort_order/{fav_artists[0].pk}" type="hidden" value="0"></td>
                    </tr>
                    <tr data-pk="{fav_artists[1].pk}">
                        <td>Ozzy Osbourne</td>
                        <td><input id="id_columns__comment__{fav_artists[1].pk}" name="columns/comment/{fav_artists[1].pk}" type="text" value="I love this too!"></td>
                        <td class="reordering-handle-cell" title="Drag and drop to reorder"><input data-reordering-value id="id_columns__sort_order__{fav_artists[1].pk}" name="columns/sort_order/{fav_artists[1].pk}" type="hidden" value="1"></td>
                    </tr>
                    <tr data-pk="{fav_artists[2].pk}">
                        <td>Damnation</td>
                        <td><input id="id_columns__comment__{fav_artists[2].pk}" name="columns/comment/{fav_artists[2].pk}" type="text" value="And this as well"></td>
                        <td class="reordering-handle-cell" title="Drag and drop to reorder"><input data-reordering-value id="id_columns__sort_order__{fav_artists[2].pk}" name="columns/sort_order/{fav_artists[2].pk}" type="hidden" value="2"></td>
                    </tr>
                </tbody>
            </table>
        """,
    )


@pytest.mark.django_db
def test_orderable_edit_table_sortablejs_options(fav_artists):
    sortablejs_options = {
        "multiDrag": True,  # Enable multi-drag
        "selectedClass": 'selected',  # The class applied to the selected items
        "fallbackTolerance": 3,  # So that we can select items on mobile
    }
    class FavoriteArtists(EditTable):
        class Meta:
            auto__model = FavoriteArtist
            auto__include = ['artist__name', 'comment', 'sort_order']
            columns__comment__field__include = True
            reorderable = sortablejs_options
            sortable = False

    verify_table_html(
        table=FavoriteArtists().bind(request=req('get')),
        # language=html
        expected_html=f"""
            <table class="table" data-new-row-endpoint="/new_row" data-next-virtual-pk="-1">
                <thead>
                    <tr>
                        <th class="first_column subheader">Name</th>
                        <th class="first_column subheader">Comment</th>
                        <th class="first_column subheader">Sort order</th>
                    </tr>
                </thead>
                <tbody data-iommi-reorderable="{html.escape(json.dumps(sortablejs_options, separators=(',', ':')))}" data-iommi-reorderable-field-selector="[data-reordering-value]" data-iommi-reorderable-handle-selector="[data-iommi-path=&quot;columns__sort_order__cell&quot;]">
                    <tr data-pk="{fav_artists[0].pk}">
                        <td>Black Sabbath</td>
                        <td><input id="id_columns__comment__{fav_artists[0].pk}" name="columns/comment/{fav_artists[0].pk}" type="text" value="Love it!"></td>
                        <td class="reordering-handle-cell" title="Drag and drop to reorder"><input data-reordering-value id="id_columns__sort_order__{fav_artists[0].pk}" name="columns/sort_order/{fav_artists[0].pk}" type="hidden" value="0"></td>
                    </tr>
                    <tr data-pk="{fav_artists[1].pk}">
                        <td>Ozzy Osbourne</td>
                        <td><input id="id_columns__comment__{fav_artists[1].pk}" name="columns/comment/{fav_artists[1].pk}" type="text" value="I love this too!"></td>
                        <td class="reordering-handle-cell" title="Drag and drop to reorder"><input data-reordering-value id="id_columns__sort_order__{fav_artists[1].pk}" name="columns/sort_order/{fav_artists[1].pk}" type="hidden" value="1"></td>
                    </tr>
                    <tr data-pk="{fav_artists[2].pk}">
                        <td>Damnation</td>
                        <td><input id="id_columns__comment__{fav_artists[2].pk}" name="columns/comment/{fav_artists[2].pk}" type="text" value="And this as well"></td>
                        <td class="reordering-handle-cell" title="Drag and drop to reorder"><input data-reordering-value id="id_columns__sort_order__{fav_artists[2].pk}" name="columns/sort_order/{fav_artists[2].pk}" type="hidden" value="2"></td>
                    </tr>
                </tbody>
            </table>
        """,
    )


@pytest.mark.django_db
def test_orderable_edit_table_reorder_handle():
    obj1 = TFoo.objects.create(a=1, b='test_reorder_handle')
    obj2 = TFoo.objects.create(a=2, b='test_reorder_handle')

    class MyEditTable(EditTable):
        class Meta:
            auto__model = TFoo
            rows = TFoo.objects.filter(b='test_reorder_handle')
            auto__include = ['a', 'b']
            columns__a = EditColumn.reorder_handle()
            sortable = False

    verify_table_html(
        table=MyEditTable().bind(request=req('get')),
        # language=html
        expected_html=f"""
            <table class="table" data-new-row-endpoint="/new_row" data-next-virtual-pk="-1">
                <thead>
                    <tr>
                        <th class="first_column subheader">B</th>
                        <th class="first_column subheader">A</th>
                    </tr>
                </thead>
                <tbody data-iommi-reorderable data-iommi-reorderable-field-selector="[data-reordering-value]" data-iommi-reorderable-handle-selector="[data-iommi-path=&quot;columns__a__cell&quot;]">
                    <tr data-pk="{obj1.pk}">
                        <td>test_reorder_handle</td>
                        <td class="reordering-handle-cell" title="Drag and drop to reorder"><input data-reordering-value id="id_columns__a__{obj1.pk}" name="columns/a/{obj1.pk}" type="hidden" value="1"></td>
                    </tr>
                    <tr data-pk="{obj2.pk}">
                        <td>test_reorder_handle</td>
                        <td class="reordering-handle-cell" title="Drag and drop to reorder"><input data-reordering-value id="id_columns__a__{obj2.pk}" name="columns/a/{obj2.pk}" type="hidden" value="2"></td>
                    </tr>
                </tbody>
            </table>
        """,
    )


@pytest.mark.django_db
def test_orderable_sortable_edit_table(fav_artists):
    """
    when sorted by any column, the reordering turns off
    """
    class FavoriteArtists(EditTable):
        class Meta:
            auto__model = FavoriteArtist
            auto__include = ['artist__name', 'comment', 'sort_order']
            columns__comment__field__include = True

    fav_artists_data = FavoriteArtist.objects.order_by('artist__name')

    verify_table_html(
        table=FavoriteArtists().bind(request=req('get', order='artist_name')),
        # language=html
        expected_html=f"""
            <table class="table" data-new-row-endpoint="/new_row" data-next-virtual-pk="-1">
                <thead>
                    <tr>
                        <th class="ascending first_column iommi_sort_header sorted subheader">
                            <a href="?order=-artist_name">Name</a>
                        </th>
                        <th class="first_column iommi_sort_header subheader">
                            <a href="?order=comment">Comment</a>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr data-pk="{fav_artists_data[0].pk}">
                        <td>{fav_artists_data[0].artist.name}</td>
                        <td><input id="id_columns__comment__{fav_artists_data[0].pk}" name="columns/comment/{fav_artists_data[0].pk}" type="text" value="{fav_artists_data[0].comment}"></td>
                    </tr>
                    <tr data-pk="{fav_artists_data[1].pk}">
                        <td>{fav_artists_data[1].artist.name}</td>
                        <td><input id="id_columns__comment__{fav_artists_data[1].pk}" name="columns/comment/{fav_artists_data[1].pk}" type="text" value="{fav_artists_data[1].comment}"></td>
                    </tr>
                    <tr data-pk="{fav_artists_data[2].pk}">
                        <td>{fav_artists_data[2].artist.name}</td>
                        <td><input id="id_columns__comment__{fav_artists_data[2].pk}" name="columns/comment/{fav_artists_data[2].pk}" type="text" value="{fav_artists_data[2].comment}"></td>
                    </tr>
                </tbody>
            </table>
        """,
    )
