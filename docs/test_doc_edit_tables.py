from django.contrib.auth import get_user_model

import pytest
from docs.models import *
from iommi import *
from iommi.form import save_nested_forms
from tests.helpers import (
    req,
    show_output,
)

pytestmark = pytest.mark.django_db


request = req('get')


def fill_dummy_data(): pass


def test_edit_tables(really_big_discography):
    # language=rst
    """
    .. _edit-tables:

    Edit tables
    ===========

    iommi edit tables builds on top of iommi tables but enable editing of cells too.

    A simple example:
    """

    # @test
    t = (
    # @end

    EditTable(
        auto__model=Album,
        page_size=10,
        # Turn on the edit feature for the year column
        columns__year__field__include=True,
        # Turn on the delete row feature
        columns__delete=EditColumn.delete(),
    )

    # @test
    )

    show_output(t.bind(request=request))
    # @end


def test_orderable_edit_tables(fav_artists):
    # language=rst
    """
    .. _orderable-edit-tables:

    Orderable edit tables
    =====================

    iommi edit tables also support ordering. That can be especially useful for editing reverse FK's in nested forms.
    """

    # language=rst
    """
    The easiest way to make an EditTable orderable is to inherit your model from `iommi.models.Orderable`:

    .. code-block:: python

           class FavoriteArtist(Orderable):
               user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorite_artists')
               artist = ForeignKey(Artist, on_delete=CASCADE, related_name='+')
               comment = CharField(max_length=255)

               def __str__(self):
                   return self.artist.name
    """

    class UserForm(Form):
        class Meta:
            auto__model = get_user_model()
            auto__include = ['username', 'email']
            fields__username__editable = False

    class FavoriteArtists(EditTable):
        class Meta:
            auto__model = FavoriteArtist
            auto__include = ['artist__name', 'comment', 'sort_order']
            columns__comment__field__include = True

    user = get_user_model().objects.get(username='john.doe')

    class ParentForm(Form):
        user_form = UserForm.edit(auto__instance=user)
        favorite_artists = FavoriteArtists(rows=user.favorite_artists.all())

        class Meta:
            actions__submit__post_handler = save_nested_forms

    # @test
    t = (
    # @end

    ParentForm()

    # @test
    )

    show_output(t.bind(request=request))
    # @end

    # language=rst
    """
    If you already have a custom model field for ordering, you can register it as a reorderderin column:

    .. code-block:: python

           from iommi import register_edit_column_factory

           register_edit_column_factory(YourOrderField, shortcut_name='reorder_handle')
    """

    # language=rst
    """
    If you just use any django integer field, you can still make your EditTable orderable with:

    .. code-block:: python

               class MyEditTable(EditTable):
                   class Meta:
                       auto__model = Foo
                       columns__bar = EditColumn.reorder_handle()
    """

    # language=rst
    """
    We use SortableJS and if you want, you can also pass other `options <https://github.com/SortableJS/Sortable?tab=readme-ov-file#options>`__.
    For example this allows multi-drag:

    .. code-block:: python

               class MyEditTable(EditTable):
                   class Meta:
                       auto__model = Foo
                       columns__bar = EditColumn.reorder_handle()
                       reorderable = {
                           "multiDrag": True,  # Enable multi-drag
                           "selectedClass": 'selected',  # The class applied to the selected items
                           "fallbackTolerance": 3,  # So that we can select items on mobile
                       }
    """
