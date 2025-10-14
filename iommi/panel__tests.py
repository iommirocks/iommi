import pytest

from django.utils.translation import gettext_lazy
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.contrib.auth.models import User

from iommi._web_compat import Template
from iommi import html

from iommi import Form, Panel, Fragment, EditTable
from iommi.form import (
    Field,
    FieldNameError,
)
from iommi.table import Table
from tests.helpers import req, verify_part_html, verify_table_html
from docs.models import FavoriteArtist


def get_user_form():
    class UserForm(Form):
        class Meta:
            auto__model = get_user_model()
            auto__exclude = ["password", "user_permissions"]

            # date_joined changes with every test, because it runs new data migration
            fields__date_joined__include = False

            layout = Panel(dict(
                p_main=Panel.card(
                    dict(
                        p_access=Panel.row(dict(
                            username=Panel.field(col__attrs__class__foo=True),  # test also custom col attrs
                            change_password_btn=Panel.part(
                                Fragment(
                                    text="Change password form is somewhere else",
                                    tag="div",
                                ),
                                include=lambda form, **_: form.editable and form.instance,
                            ),
                        )),
                        p_fullname=Panel.row(dict(
                            first_name=Panel.field(),
                            last_name=Panel.field(),
                        )),
                        email=Panel.field(),
                        is_active=Panel.field(),
                        p_dates=Panel.row(dict(
                            last_login=Panel.field(),
                            # date_joined=Panel.field(),
                        )),
                        p_permissions=Panel.fieldset(
                            dict(
                                p_roles=Panel.row(dict(
                                    is_superuser=Panel.field(),
                                    is_staff=Panel.field(),
                                )),
                                groups=Panel.field(),
                            ),
                            legend=gettext_lazy("Permissions")
                        ),
                        p_error=Panel.alert("Error!", level="error"),
                    ),
                    header=lambda form, **_: form.instance.username if form.instance is not None else "New user",
                    footer=Template("<i>Let's put something in the footer</i>"),
                ),
            ))

    return UserForm


@pytest.mark.django_db
def test_structured_user_form(john_doe_user):
    verify_part_html(
        part=get_user_form()(instance=john_doe_user),
        # language=HTML
        expected_html='''
            <form action="" enctype="multipart/form-data" method="post">
                <div class="card">
                    <div class="card-header">john.doe</div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col foo" data-iommi-type="PanelCol">
                                <div>
                                    <label for="id_username">Username</label>
                                    <input id="id_username" name="username" type="text" value="john.doe"/>
                                    <div class="helptext">Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.</div>
                                </div>
                            </div>
                            <div class="col" data-iommi-type="PanelCol">
                                <div>Change password form is somewhere else</div>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col" data-iommi-type="PanelCol">
                                <div>
                                    <label for="id_first_name">First name</label>
                                    <input id="id_first_name" name="first_name" type="text" value=""/>
                                </div>
                            </div>
                            <div class="col" data-iommi-type="PanelCol">
                                <div>
                                    <label for="id_last_name">Last name</label>
                                    <input id="id_last_name" name="last_name" type="text" value=""/>
                                </div>
                            </div>
                        </div>
                        <div>
                            <label for="id_email">Email address</label>
                            <input id="id_email" name="email" type="email" value="john.doe@example.com"/>
                        </div>
                        <div>
                            <input checked="" id="id_is_active" name="is_active" type="checkbox"/>
                            <label for="id_is_active">Active</label>
                            <div class="helptext">Designates whether this user should be treated as active. Unselect this instead of deleting accounts.</div>
                        </div>
                        <div class="row">
                            <div class="col" data-iommi-type="PanelCol">
                                <div>
                                    <label for="id_last_login">Last login</label>
                                    <input id="id_last_login" name="last_login" type="text" value=""/>
                                </div>
                            </div>
                        </div>
                        <fieldset>
                            <legend>Permissions</legend>
                            <div class="row">
                                <div class="col" data-iommi-type="PanelCol">
                                    <div>
                                        <input id="id_is_superuser" name="is_superuser" type="checkbox"/>
                                        <label for="id_is_superuser">Superuser status</label>
                                        <div class="helptext">Designates that this user has all permissions without explicitly assigning them.</div>
                                    </div>
                                </div>
                                <div class="col" data-iommi-type="PanelCol">
                                    <div>
                                        <input id="id_is_staff" name="is_staff" type="checkbox"/>
                                        <label for="id_is_staff">Staff status</label>
                                        <div class="helptext">Designates whether the user can log into this admin site.</div>
                                    </div>
                                </div>
                            </div>
                            <div style="min-width: 200px">
                                <label for="id_groups">Groups</label>
                                <select class="select2_enhance" data-choices-endpoint="/choices" data-placeholder="" id="id_groups" multiple="" name="groups"></select>
                                <div class="helptext">The groups this user belongs to. A user will get all permissions granted to each of their groups.</div>
                            </div>
                        </fieldset>
                        <div class="alert alert-error" role="alert">Error!</div>
                    </div>
                    <div class="card-footer"><i>Let's put something in the footer</i></div>
                </div>
            </form>
        '''
    )


@pytest.mark.django_db
def test_missing_fields():
    try:
        get_user_form()(
            instance=None,
            layout=Panel(dict(
                p_main=Panel.card(dict(
                    first_name=Panel.field(),
                    last_name=Panel.field(),
                    email=Panel.field(),
                )),
            ))
        ).bind(request=req("get")).render_to_response()
    except ImproperlyConfigured:
        pass
    else:
        raise Exception("should have raised an ImproperlyConfigured")


@pytest.mark.django_db
def test_unused_fields_at_the_end():
    user_form = get_user_form()(
        instance=None,
        auto__include=["username", "first_name", "last_name", "email", "is_active"],
        layout_render_unused_fields=True,  # add fields missing in layout at the end of the form
        layout=Panel(dict(
            p_main=Panel.card(dict(
                h3_foo__template="test_h3_foo.html",
                username=Panel.field(),
                first_name=Panel.field(),
                last_name=Panel.field(),
                h3_bar=html.h3("Bar"),
                email=Panel.field(),
            )),
        ))
    )

    verify_part_html(
        part=user_form,
        # language=HTML
        expected_html='''
            <form action="" enctype="multipart/form-data" method="post">
                <div class="card">
                    <div class="card-body">
                        <h3>Foo</h3>
                        <div>
                            <label for="id_username">Username</label>
                            <input id="id_username" name="username" type="text" value=""/>
                            <div class="helptext">Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.</div>
                        </div>
                        <div>
                            <label for="id_first_name">First name</label>
                            <input id="id_first_name" name="first_name" type="text" value=""/>
                        </div>
                        <div>
                            <label for="id_last_name">Last name</label>
                            <input id="id_last_name" name="last_name" type="text" value=""/>
                        </div>
                        <h3>Bar</h3>
                        <div>
                            <label for="id_email">Email address</label>
                            <input id="id_email" name="email" type="email" value=""/>
                        </div>
                    </div>
                </div>
                <div>
                    <input checked="" id="id_is_active" name="is_active" type="checkbox"/>
                    <label for="id_is_active">Active</label>
                    <div class="helptext">Designates whether this user should be treated as active. Unselect this instead of deleting accounts.</div>
                </div>
            </form>
        '''
    )


@pytest.mark.django_db
def test_panel_field_of_missing_field():
    try:
        get_user_form()(
            instance=None,
            fields__is_superuser__include=False,
        ).bind(request=req("get")).render_to_response()
    except FieldNameError:
        pass
    else:
        raise Exception("should have raised a FieldNameError")


@pytest.mark.django_db
def test_nested_forms(john_doe_user, fav_artists):
    class UserForm(Form):
        class Meta:
            auto__model = get_user_model()
            auto__include = ["username", "email", "last_login"]
            fields__last_login__include = lambda form, **_: form.instance is not None

    class FavoriteArtistsEditTable(EditTable):
        class Meta:
            auto__model = FavoriteArtist
            auto__include = ['artist__name', 'comment', 'sort_order']
            columns__comment__field__include = True
            sortable = False

    class NestedEditForm(Form):
        user_edit = UserForm(instance=john_doe_user)
        favorite_artists = FavoriteArtistsEditTable(rows=john_doe_user.favorite_artists.all())

        class Meta:
            layout = Panel(dict(
                p_main=Panel.card(dict(
                    username=Panel.field(),
                    favorite_artists=Panel.nested_form(),
                    email=Panel.field(),
                    last_login=Panel.field(include=lambda form, **_: form.nested_forms.user_edit.instance is not None),
                )),
            ))
            layout__children__p_main__attrs__class__test = True

    verify_part_html(
        part=NestedEditForm(),
        # language=HTML
        expected_html=f'''
            <form action="" enctype="multipart/form-data" method="post">
                <div class="card">
                    <div class="card-body">
                        <div>
                            <label for="id_username">Username</label>
                            <input id="id_username" name="username" type="text" value="john.doe"/>
                            <div class="helptext">Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.</div>
                        </div>
                        <h1>Favorite artists</h1>
                        <div class="iommi-table-container" data-endpoint="/favorite_artists/tbody" data-iommi-id="favorite_artists">
                            <div action="" enctype="multipart/form-data" method="post">
                                <div class="iommi-table-plus-paginator">
                                    <table class="table" data-new-row-endpoint="/new_row" data-next-virtual-pk="-1">
                                        <thead>
                                            <tr>
                                                <th class="first_column subheader">Name</th>
                                                <th class="first_column subheader">Comment</th>
                                                <th class="first_column subheader">Sort order</th>
                                            </tr>
                                        </thead>
                                        <tbody data-iommi-reorderable="" data-iommi-reorderable-field-selector="[data-reordering-value]" data-iommi-reorderable-handle-selector='[data-iommi-path="fields__favorite_artists__columns__sort_order__cell"]'>
                                            <tr data-pk="{fav_artists[0].pk}">
                                                <td>Black Sabbath</td>
                                                <td><input id="id_favorite_artists__comment__{fav_artists[0].pk}" name="favorite_artists/comment/{fav_artists[0].pk}" type="text" value="Love it!"/></td>
                                                <td class="reordering-handle-cell" title="Drag and drop to reorder">
                                                    <input data-reordering-value="" id="id_favorite_artists__sort_order__{fav_artists[0].pk}" name="favorite_artists/sort_order/{fav_artists[0].pk}" type="hidden" value="0"/>
                                                </td>
                                            </tr>
                                            <tr data-pk="{fav_artists[1].pk}">
                                                <td>Ozzy Osbourne</td>
                                                <td><input id="id_favorite_artists__comment__{fav_artists[1].pk}" name="favorite_artists/comment/{fav_artists[1].pk}" type="text" value="I love this too!"/></td>
                                                <td class="reordering-handle-cell" title="Drag and drop to reorder">
                                                    <input data-reordering-value="" id="id_favorite_artists__sort_order__{fav_artists[1].pk}" name="favorite_artists/sort_order/{fav_artists[1].pk}" type="hidden" value="1"/>
                                                </td>
                                            </tr>
                                            <tr data-pk="{fav_artists[2].pk}">
                                                <td>Damnation</td>
                                                <td><input id="id_favorite_artists__comment__{fav_artists[2].pk}" name="favorite_artists/comment/{fav_artists[2].pk}" type="text" value="And this as well"/></td>
                                                <td class="reordering-handle-cell" title="Drag and drop to reorder">
                                                    <input data-reordering-value="" id="id_favorite_artists__sort_order__{fav_artists[2].pk}" name="favorite_artists/sort_order/{fav_artists[2].pk}" type="hidden" value="2"/>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                                <div class="links">
                                    <button data-iommi-edit-table-add-row-button="" data-iommi-edit-table-path="fields__favorite_artists" type="button">Add row</button>
                                </div>
                            </div>
                        </div>
                        <div>
                            <label for="id_email">Email address</label>
                            <input id="id_email" name="email" type="email" value="john.doe@example.com"/>
                        </div>
                        <div>
                            <label for="id_last_login">Last login</label>
                            <input id="id_last_login" name="last_login" type="text" value=""/>
                        </div>
                    </div>
                </div>
            </form>
        '''
    )

    class NestedCreateForm(Form):
        user_edit = UserForm.create()
        favorite_artists = FavoriteArtistsEditTable(rows=[])

        class Meta:
            layout = {
                'children': {
                    'p_main': {
                        'children': {
                            'username': {'call_target': Panel.field},
                            'favorite_artists': {'call_target': Panel.nested_form},
                            'email': {'call_target': Panel.field},
                            'last_login': {
                                'call_target': Panel.field,
                                'include': lambda form, **_: form.nested_forms.user_edit.instance is not None,
                            },
                        },
                        'call_target': Panel.card,
                    },
                },
                'call_target': Panel,
            }
            layout__children__p_main__attrs__class__test = True

    verify_part_html(
        part=NestedCreateForm(),
        # language=HTML
        expected_html='''
            <form action="" enctype="multipart/form-data" method="post">
                <div class="card test">
                    <div class="card-body">
                        <div>
                            <label for="id_username">Username</label>
                            <input id="id_username" name="username" type="text" value=""/>
                            <div class="helptext">Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.</div>
                        </div>
                        <h1>Favorite artists</h1>
                        <div class="iommi-table-container" data-endpoint="/favorite_artists/tbody" data-iommi-id="favorite_artists">
                            <div action="" enctype="multipart/form-data" method="post">
                                <div class="iommi-table-plus-paginator">
                                    <table class="table" data-new-row-endpoint="/new_row" data-next-virtual-pk="-1">
                                        <thead>
                                            <tr>
                                                <th class="first_column subheader">Name</th>
                                                <th class="first_column subheader">Comment</th>
                                                <th class="first_column subheader">Sort order</th>
                                            </tr>
                                        </thead>
                                        <tbody data-iommi-reorderable="" data-iommi-reorderable-field-selector="[data-reordering-value]" data-iommi-reorderable-handle-selector='[data-iommi-path="fields__favorite_artists__columns__sort_order__cell"]'>
                                        </tbody>
                                    </table>
                                </div>
                                <div class="links">
                                    <button data-iommi-edit-table-add-row-button="" data-iommi-edit-table-path="fields__favorite_artists" type="button">Add row</button>
                                </div>
                            </div>
                        </div>
                        <div>
                            <label for="id_email">Email address</label>
                            <input id="id_email" name="email" type="email" value=""/>
                        </div>
                    </div>
                </div>
            </form>
        '''
    )


def test_basic_refining():
    class MyForm(Form):
        class Meta:
            auto__model = User
            auto__include = ['username']

            layout = Panel(dict(
                p_main=Panel.card(dict(
                    username=Panel.field(),
                )),
            ))
            layout__children__p_main__attrs__class__test = True

    assert MyForm().bind(request=req('get')).layout.children.p_main.attrs['class'].test


def test_basic_refining2():
    class MyForm(Form):
        class Meta:
            auto__model = User
            auto__include = ['username']

            layout = Panel(dict(
                p_main=Panel.card(dict(
                    username=Panel.field(),
                )),
            ))

    assert MyForm(layout__children__p_main__attrs__class__test=True).bind(request=req('get')).layout.children.p_main.attrs['class'].test


def test_foo():
    class MyForm(Form):
        class Meta:
            auto__model = User
            auto__include = []

            fields__username = Field()
            fields__username__attrs__class__test = True

    assert MyForm().bind(request=req('get')).fields.username.attrs['class'].test


@pytest.mark.django_db
def test_filter_form_layout(john_doe_user, fav_artists):
    class FavoriteArtistsTable(Table):
        class Meta:
            auto__model = FavoriteArtist
            auto__include = ['user', 'artist', 'comment']
            columns__user__filter__include = True
            columns__artist__filter__include = True
            columns__comment__filter__include = True
            columns__comment__filter__freetext = True
            query__advanced__include = False
            query__form__layout = Panel(dict(
                freetext_search=Panel.field(),
                p_abc=Panel.row(dict(
                    user=Panel.field(),
                    artist=Panel.field(),
                ))
            ))

    verify_part_html(
        part=FavoriteArtistsTable().bind(request=req('get')),
        find__class='iommi_query_form_simple',
        # language=html
        expected_html='''
            <span class="iommi_query_form_simple">
                <div>
                    <label for="id_freetext_search">Search</label>
                    <input id="id_freetext_search" name="freetext_search" type="text" value=""/>
                </div>
                <div class="row">
                    <div class="col" data-iommi-type="PanelCol">
                        <div style="min-width: 200px">
                            <label for="id_user">User</label>
                            <select class="select2_enhance" data-choices-endpoint="/choices" data-placeholder="" id="id_user" name="user">
                            </select>
                        </div>
                    </div>
                    <div class="col" data-iommi-type="PanelCol">
                        <div style="min-width: 200px">
                            <label for="id_artist">Artist</label>
                            <select class="select2_enhance" data-choices-endpoint="/artist/choices" data-placeholder="" id="id_artist" name="artist">
                            </select>
                        </div>
                    </div>
                </div>
            </span>
        '''
    )


@pytest.mark.django_db
def test_table_row_layout(john_doe_user, fav_artists):
    class FavoriteArtistsTable(Table):
        class Meta:
            auto__rows = john_doe_user.favorite_artists.all()
            auto__include = ['user__username', 'artist', 'comment']
            columns__artist__cell__url = None
            columns__comment__cell__url = lambda row, **_: f'/favorite_artist/{row.pk}/'
            row__layout = Panel.div(
                dict(
                    artist=Panel.cell(),
                    p_abc=Panel.row(dict(
                        user_username=Panel.cell(),
                        comment=Panel.cell(),
                    )),
                ),
                **{
                    # test if both attrs (panel+cells) get rendered
                    'attrs__data-comment': lambda row, **_: row.comment,
                    'attrs__style__border-bottom': '1px solid #6ea8fe',
                }
            )

    verify_table_html(
        table=FavoriteArtistsTable.div().bind(request=req('get')),
        # language=html
        expected_html=f'''
            <div class="table">
                <div>
                    <div data-pk="{fav_artists[0].pk}" data-comment="Love it!" style="border-bottom: 1px solid #6ea8fe">
                        Black Sabbath
                        <div class="row">
                            <div class="col" data-iommi-type="PanelCol">john.doe</div>
                            <div class="col" data-iommi-type="PanelCol"><a href="/favorite_artist/{fav_artists[0].pk}/">Love it!</a></div>
                        </div>
                    </div>
                    <div data-pk="{fav_artists[1].pk}" data-comment="I love this too!" style="border-bottom: 1px solid #6ea8fe">
                        Ozzy Osbourne
                        <div class="row">
                            <div class="col" data-iommi-type="PanelCol">john.doe</div>
                            <div class="col" data-iommi-type="PanelCol"><a href="/favorite_artist/{fav_artists[1].pk}/">I love this too!</a></div>
                        </div>
                    </div>
                    <div data-pk="{fav_artists[2].pk}" data-comment="And this as well" style="border-bottom: 1px solid #6ea8fe">
                        Damnation
                        <div class="row">
                            <div class="col" data-iommi-type="PanelCol">john.doe</div>
                            <div class="col" data-iommi-type="PanelCol"><a href="/favorite_artist/{fav_artists[2].pk}/">And this as well</a></div>
                        </div>
                    </div>
                </div>
            </div>
        ''',
    )


@pytest.mark.django_db
def test_edit_table_row_layout(john_doe_user, fav_artists):
    class FavoriteArtistsEditTable(EditTable):
        class Meta:
            auto__model = FavoriteArtist
            auto__rows = john_doe_user.favorite_artists.all()
            auto__include = ['user', 'artist__name', 'comment', 'sort_order']
            columns__comment__field__include = True
            columns__user__field__include = True
            row__layout = Panel.div(dict(
                artist_name=Panel.cell(),
                p_abc=Panel.row(dict(
                    user=Panel.cell(),
                    comment=Panel.cell(),
                )),
                sort_order=Panel.reorder_handle(),
            ))

    verify_part_html(
        part=FavoriteArtistsEditTable.div().bind(request=req('get')),
        # language=HTML
        expected_html=f'''
            <h1>Favorite artists</h1>
            <div class="iommi-table-container" data-endpoint="/endpoints/tbody" data-iommi-id="">
                <form action="" enctype="multipart/form-data" method="post">
                    <div class="iommi-table-plus-paginator">
                        <div class="table" data-new-row-endpoint="/new_row" data-next-virtual-pk="-1">
                            <div data-iommi-reorderable="" data-iommi-reorderable-field-selector="[data-reordering-value]" data-iommi-reorderable-handle-selector='[data-iommi-path="columns__sort_order__cell"]'>
                                <div data-pk="{fav_artists[0].pk}">
                                    Black Sabbath
                                    <div class="row">
                                        <div class="col" data-iommi-type="PanelCol">
                                            <div style="min-width: 200px">
                                                <label for="id_columns__user__{fav_artists[0].pk}">User</label>
                                                <select class="select2_enhance" data-choices-endpoint="/user/choices" data-placeholder="" id="id_columns__user__{fav_artists[0].pk}" name="columns/user/{fav_artists[0].pk}">
                                                    <option label="john.doe" selected="selected" value="{john_doe_user.pk}">
                                                        john.doe
                                                    </option>
                                                </select>
                                            </div>
                                       </div>
                                        <div class="col" data-iommi-type="PanelCol">
                                            <div>
                                                <label for="id_columns__comment__{fav_artists[0].pk}">Comment</label>
                                                <input id="id_columns__comment__{fav_artists[0].pk}" name="columns/comment/{fav_artists[0].pk}" type="text" value="Love it!"/>
                                            </div>
                                        </div>
                                    </div>
                                    <span class="reordering-handle-cell" title="Drag and drop to reorder">
                                        <input data-reordering-value="" id="id_columns__sort_order__{fav_artists[0].pk}" name="columns/sort_order/{fav_artists[0].pk}" type="hidden" value="0"/>
                                    </span>
                                </div>
                                <div data-pk="{fav_artists[1].pk}">
                                    Ozzy Osbourne
                                    <div class="row">
                                        <div class="col" data-iommi-type="PanelCol">
                                            <div style="min-width: 200px">
                                                <label for="id_columns__user__{fav_artists[1].pk}">User</label>
                                                <select class="select2_enhance" data-choices-endpoint="/user/choices" data-placeholder="" id="id_columns__user__{fav_artists[1].pk}" name="columns/user/{fav_artists[1].pk}">
                                                    <option label="john.doe" selected="selected" value="{john_doe_user.pk}">
                                                        john.doe
                                                    </option>
                                                </select>
                                            </div>
                                       </div>
                                        <div class="col" data-iommi-type="PanelCol">
                                            <div>
                                                <label for="id_columns__comment__{fav_artists[1].pk}">Comment</label>
                                                <input id="id_columns__comment__{fav_artists[1].pk}" name="columns/comment/{fav_artists[1].pk}" type="text" value="I love this too!"/>
                                            </div>
                                        </div>
                                    </div>
                                    <span class="reordering-handle-cell" title="Drag and drop to reorder">
                                        <input data-reordering-value="" id="id_columns__sort_order__{fav_artists[1].pk}" name="columns/sort_order/{fav_artists[1].pk}" type="hidden" value="1"/>
                                    </span>
                                </div>
                                <div data-pk="{fav_artists[2].pk}">
                                    Damnation
                                    <div class="row">
                                        <div class="col" data-iommi-type="PanelCol">
                                            <div style="min-width: 200px">
                                                <label for="id_columns__user__{fav_artists[2].pk}">User</label>
                                                <select class="select2_enhance" data-choices-endpoint="/user/choices" data-placeholder="" id="id_columns__user__{fav_artists[2].pk}" name="columns/user/{fav_artists[2].pk}">
                                                    <option label="john.doe" selected="selected" value="{john_doe_user.pk}">
                                                        john.doe
                                                    </option>
                                                </select>
                                            </div>
                                       </div>
                                        <div class="col" data-iommi-type="PanelCol">
                                            <div>
                                                <label for="id_columns__comment__{fav_artists[2].pk}">Comment</label>
                                                <input id="id_columns__comment__{fav_artists[2].pk}" name="columns/comment/{fav_artists[2].pk}" type="text" value="And this as well"/>
                                            </div>
                                        </div>
                                    </div>
                                    <span class="reordering-handle-cell" title="Drag and drop to reorder">
                                        <input data-reordering-value="" id="id_columns__sort_order__{fav_artists[2].pk}" name="columns/sort_order/{fav_artists[2].pk}" type="hidden" value="2"/>
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="links">
                        <button accesskey="s" name="-save">Save</button>
                        <button data-iommi-edit-table-add-row-button="" data-iommi-edit-table-path="" type="button">Add row</button>
                    </div>
                </form>
            </div>
        ''',
    )


@pytest.mark.django_db
@override_settings(IOMMI_DEBUG=True)
def test_row_layout_attrs(john_doe_user, fav_artists):
    class FavoriteArtistsEditTable(EditTable):
        class Meta:
            auto__model = FavoriteArtist
            auto__rows = john_doe_user.favorite_artists.all()[:1]
            auto__include = ['comment']
            columns__comment__field__include = True
            row__layout = Panel.div(dict(
                p_abc=Panel.row(dict(
                    comment=Panel.cell(),
                )),
            ))

    form = FavoriteArtistsEditTable.div().bind(request=req('get'))
    row_layout_attrs = next(form.cells_for_rows()).layout.attrs
    assert row_layout_attrs['data-pk'] == john_doe_user.favorite_artists.first().pk
    assert row_layout_attrs['data-iommi-type'] == 'Panel'
    assert row_layout_attrs['data-iommi-path'] == 'row__layout'
