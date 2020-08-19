from iommi import *
from tests.helpers import req
from django.template import Template
from tri_declarative import Namespace
from iommi.attrs import render_attrs
from django.http import HttpResponseRedirect
from django.db import models
from .models import Artist, Album, Track
import pytest
pytestmark = pytest.mark.django_db


def test_how_do_i_find_the_path_to_a_parameter():
    IOMMI_DEBUG = True
    IOMMI_DEBUG_URL_BUILDER = lambda filename, lineno: f'my_editor://{filename}:{lineno}'
    assert True  # Until I come up with a nice way to test this


def test_how_do_i_supply_a_custom_parser_for_a_field():
    form = Form(
        auto__model=Track,
        fields__index__parse=
            lambda field, string_value, **_: int(string_value[:-3]),
    )
    form = form.bind(request=req('get', index='123abc'))
    assert not form.get_errors()
    assert form.fields.index.value == 123


def test_how_do_i_make_a_field_non_editable():
    form = Form(
        auto__model=Album,
        fields__name__editable=
            lambda request, **_: request.user.is_staff,
        fields__artist__editable=False,
    )


def test_how_do_i_make_an_entire_form_non_editable():
    form = Form(
        auto__model=Album,
        editable=False,
    )


def test_how_do_i_supply_a_custom_validator():
    form = Form(
        auto__model=Album,
        fields__name__is_valid=
            lambda form, field, parsed_data: (False, 'invalid!'),
    )


def test_how_do_i_exclude_a_field():
    pass


def test_how_do_i_say_which_fields_to_include_when_creating_a_form_from_a_model():
    pass


def test_how_do_i_supply_a_custom_initial_value():
    form = Form(
        auto__model=Album,
        fields__name__initial='Paranoid',
        fields__year__initial=lambda field, form, **_: 1970,
    )


def test_how_do_i_set_if_a_field_is_required():
    form = Form(
        auto__model=Album,
        fields__name__required=True,
        fields__year__required=lambda field, form, **_: True,
    )


def test_how_do_i_change_the_order_of_the_fields():
    from tri_declarative import LAST
    form = Form(
        auto__model=Album,
        fields__name__after=LAST,
        fields__year__after='artist',
        fields__artist__after=0,
    )


def test_how_do_i_specify_which_model_fields_the_search_of_a_choice_queryset_use():
    form = Form(
        auto__model=Album,
        fields__name__search_fields=('name', 'year'),
    )


def test_how_do_i_insert_a_css_class_or_html_attribute():
    pass


def test_how_do_i_override_rendering_of_an_entire_field():
    form = Form(
        auto__model=Album,
        fields__year__template='my_template.html',
    )
    form = Form(
        auto__model=Album,
        fields__year__template=Template('{{ field.attrs }}'),
    )


def test_how_do_i_override_rendering_of_the_input_field():
    form = Form(
        auto__model=Album,
        fields__year__input__template='my_template.html',
    )
    form = Form(
        auto__model=Album,
        fields__year__input__template=Template('{{ field.attrs }}'),
    )


def test_how_do_i_customize_the_rendering_of_a_table():
    pass


def test_how_do_you_turn_off_pagination():
    Table(
        auto__model=Album,
        page_size=None,
    )
    class MyTable(Table):
        a = Column()
        class Meta:
            page_size = None


def test_how_do_i_create_a_column_based_on_computed_data_():
    class Foo(models.Model):
        value = models.IntegerField()
        class Meta:
            app_label = 'docs_computed'
    Table(
        auto__model=Foo,
        columns__square=Column(
            # computed value:
            cell__value=lambda row, **_: row.value * row.value,
        )
    )
    Table(
        auto__model=Foo,
        columns__square=Column(
            attr='value',
            cell__format=lambda value, **_: value * value,
        )
    )


def test_how_do_i_get_iommi_tables_to_understand_my_django_modelfield_subclasses():
    pass


def test_how_do_i_reorder_columns():
    class Foo(models.Model):
        a = models.IntegerField()
        b = models.IntegerField()
        c = models.IntegerField()
        class Meta:
            app_label = 'docs_reorder'
    Table(auto__model=Foo, columns__c__after=-1)
    Table(auto__model=Foo, columns__c__after='a')


def test_how_do_i_enable_searching_filter_on_columns():
    Table(
        auto__model=Album,
        columns__name__filter__include=True,
    )


def test_how_do_i_customize_html_attributes__css_classes_or_css_style_specifications():
    tmp = render_attrs(Namespace(foo='bar'))
    assert tmp == ' foo="bar"'
    tmp = render_attrs(Namespace(class__foo=True, class__bar=True))
    assert tmp == ' class="bar foo"'
    tmp = render_attrs(Namespace(style__font='Arial'))
    assert tmp == ' style="font: Arial"'
    tmp = render_attrs(Namespace(**{'style__font-family': 'sans-serif'}))
    assert tmp == ' style="font-family: sans-serif"'
    tmp = render_attrs(
         Namespace(
             foo='bar',
             class__foo=True,
             class__bar=True,
             style__font='Arial',
             **{'style__font-family': 'serif'}
         )
     )
    assert tmp == ' class="bar foo" foo="bar" style="font-family: serif; font: Arial"'


def test_how_do_i_customize_the_rendering_of_a_cell():
    pass


def test_how_do_i_customize_the_rendering_of_a_row():
    pass


def test_how_do_i_customize_the_rendering_of_a_header():
    pass


def test_how_do_i_turn_off_the_header():
    pass


def test_how_do_i_add_fields_to_a_table_that_is_generated_from_a_model():
    pass


def test_how_do_i_specify_which_columns_to_show():
    Table(
        auto__model=Album,
        columns__name__include=
            lambda request, **_: request.GET.get('some_parameter') == 'hello!',
    )


def test_how_do_i_access_table_data_programmatically_():
    table = Table(auto__model=Track).bind(request=req('get'))
    for row in table.cells_for_rows():
        for cell in row:
            print(cell.render_formatted(), end='')
        print()


def test_how_do_i_make_a_link_in_a_cell():
    Column(
        cell__url='http://example.com',
        cell__url_title='go to example',
    )


def test_how_do_i_access_foreign_key_related_data_in_a_column():
    class Foo(models.Model):
        a = models.IntegerField()
        class Meta:
            app_label = 'docs_fk'
    class Bar(models.Model):
        b = models.IntegerField()
        c = models.ForeignKey(Foo, on_delete=models.CASCADE)
        class Meta:
            app_label = 'docs_fk'
    Table(
        auto__model=Bar,
        columns__a__attr='c__a',
    )


def test_how_do_i_turn_off_sorting_():
    Table(
        auto__model=Album,
        columns__name__sortable=False,
    )
    Table(
        auto__model=Album,
        sortable=False,
    )


def test_how_do_i_specify_the_title_of_a_header():
    Table(
        auto__model=Album,
        columns__name__display_name='header title',
    )


def test_how_do_i_set_the_default_sort_order_of_a_column_to_be_descending_instead_of_ascending():
    Table(
        auto__model=Album,
        columns__name__sort_default_desc=True,  # or a lambda!
    )


def test_how_do_i_group_columns():
    Table(
        auto__model=Album,
        columns__name__group='foo',
        columns__year__group='foo',
    )


def test_how_do_i_get_rowspan_on_a_table():
    Table(
        auto__model=Album,
        columns__year__auto_rowspan=True,
    )


def test_how_do_i_enable_bulk_editing():
    Table(
        auto__model=Album,
        columns__select__include=True,
        columns__year__bulk__include=True,
    )


def test_how_do_i_enable_bulk_delete():
    Table(
        auto__model=Album,
        columns__select__include=True,
        bulk__actions__delete__include=True,
    )


def test_how_do_i_make_a_custom_bulk_action():
    def my_action_post_handler(table, request, **_):
        queryset = table.bulk_queryset()
        queryset.update(spiral='architect')
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    Table(
        auto__model=Album,
        columns__select__include=True,
        bulk__actions__my_action=Action.submit(
            post_handler=my_action_post_handler,
        )
    )


def test_how_do_i_make_a_freetext_search_field():
    Table(
        auto__model=Album,
        columns__name__filter__freetext=True,
        columns__year__filter__freetext=True,
    )


def test_what_is_the_difference_between_attr_and__name():
    pass


def test_how_do_i_override_what_operator_is_used_for_a_query():
    Table(
        auto__model=Track,
        columns__album__filter__query_operator_to_q_operator=lambda op: 'exact',
    )


def test_how_do_i_control_what_q_is_produced():
    pass
