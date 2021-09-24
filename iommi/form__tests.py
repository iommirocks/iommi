import json
import re
from collections import defaultdict
from datetime import (
    date,
    datetime,
    time,
)
from decimal import Decimal
from io import (
    BytesIO,
    StringIO,
)

import pytest
from bs4 import BeautifulSoup
from django.test import override_settings
from freezegun import freeze_time
from tri_declarative import (
    class_shortcut,
    get_members,
    getattr_path,
    is_shortcut,
    Namespace,
    setattr_path,
    Shortcut,
)
from tri_struct import (
    merged,
    Struct,
)

from iommi import (
    Action,
    html,
)
from iommi._db_compat import field_defaults_factory
from iommi._web_compat import (
    smart_str,
    Template,
    ValidationError,
)
from iommi.attrs import render_attrs
from iommi.base import (
    items,
    keys,
    values,
)
from iommi.endpoint import (
    DISPATCH_PATH_SEPARATOR,
    InvalidEndpointPathException,
    perform_ajax_dispatch,
)
from iommi.form import (
    bool_parse,
    boolean_tristate__parse,
    create_or_edit_object_redirect,
    date_parse,
    datetime_iso_formats,
    datetime_parse,
    decimal_parse,
    Field,
    find_unique_prefixes,
    float_parse,
    Form,
    FULL_FORM_FROM_REQUEST,
    INITIALS_FROM_GET,
    int_parse,
    register_field_factory,
    render_template,
    time_parse,
    url_parse,
)
from iommi.from_model import (
    member_from_model,
)
from iommi.page import (
    Page,
)
from iommi.traversable import declared_members
from tests.compat import RequestFactory
from tests.helpers import (
    get_attrs,
    prettify,
    reindent,
    remove_csrf,
    req,
)
from tests.models import (
    Bar,
    BooleanFromModelTestModel,
    ChoicesModel,
    CreateOrEditObjectTest,
    DefaultsInForms,
    FieldFromModelOneToOneTest,
    Foo,
    TBar,
    TBaz,
    TFoo,
)


def assert_errors_and_matches_reg_exp(errors, reg_exp, count=1):
    assert len(errors) == count
    for error in errors:
        assert re.search(reg_exp, error)


def test_declaration_merge():
    class MyForm(Form):
        class Meta:
            fields__foo = Field()

        bar = Field()

    form = MyForm()
    form = form.bind(request=None)

    assert {'foo', 'bar'} == set(form.fields.keys())


# This function is here to avoid declaring the form at import time, which is annoying when trying to debug unrelated tests
# noinspection PyPep8Naming
@pytest.fixture
def MyTestForm():
    class MyTestForm(Form):
        party = Field.choice(choices=['ABC'], required=False)
        username = Field(
            is_valid=lambda form, field, parsed_data: (
                parsed_data.startswith(form.fields['party'].parsed_data.lower() + '_')
                if parsed_data is not None
                else None,
                'Username must begin with "%s_"' % form.fields['party'].parsed_data,
            )
        )
        joined = Field.datetime(attr='contact__joined')
        a_date = Field.date()
        in_div = html.div(
            children__a_time=Field.time(),
            children__staff=Field.boolean(),
        )
        admin = Field.boolean()
        manages = Field.multi_choice(choices=['DEF', 'KTH', 'LIU'], required=False)
        not_editable = Field.text(initial='Some non-editable text', editable=False)
        multi_choice_field = Field.multi_choice(choices=['a', 'b', 'c', 'd'], required=False)

        class Meta:
            @staticmethod
            def actions__submit__post_handler(form, **_):
                pass  # pragma: no cover

    return MyTestForm


def test_field_repr():
    assert repr(Field(_name='foo')) == "<iommi.form.Field foo>"
    assert (
        repr(Form(fields__foo=Field()).bind(request=None).fields.foo)
        == "<iommi.form.Field foo (bound) path:'foo' members:['endpoints', 'assets']>"
    )


def test_required_choice():
    class Required(Form):
        c = Field.choice(choices=[1, 2, 3])

        class Meta:
            @staticmethod
            def actions__submit__post_handler(form, **_):
                pass  # pragma: no cover

    form = Required().bind(request=req('post', **{'-submit': ''}))

    assert form.mode == FULL_FORM_FROM_REQUEST

    assert form.is_target()
    assert form.is_valid() is False, form.get_errors()
    assert form.fields['c']._errors == {'This field is required'}

    class NotRequired(Form):
        c = Field.choice(choices=[1, 2, 3], required=False)

        class Meta:
            @staticmethod
            def actions__submit__post_handler(form, **_):
                pass  # pragma: no cover

    form = NotRequired().bind(request=req('post', **{'-submit': '', 'c': ''}))
    assert form.is_target()
    assert form.is_valid(), form.get_errors()
    assert form.fields['c']._errors == set()


def test_required_multi_choice():
    class MyForm(Form):
        foo = Field.multi_choice(
            choices=list('abc'),
            initial=[],
            required=True,
        )

        class Meta:
            @staticmethod
            def actions__submit__post_handler(form, **_):
                pass  # pragma: no cover

    form = MyForm()
    target_marker = form.bind(request=req('get'),).actions.submit.own_target_marker()

    bound_form = form.bind(request=req('post', **{target_marker: ''}))

    assert not bound_form.is_valid()
    assert bound_form.fields.foo.get_errors() == {'This field is required'}


def test_required(MyTestForm):
    form = MyTestForm().bind(request=req('post', **{'-submit': ''}))
    assert form.is_target()
    assert form.is_valid() is False, form.get_errors()
    assert form.fields['a_date'].value is None
    assert form.fields['a_date']._errors == {'This field is required'}


def test_required_with_falsy_option():
    class MyForm(Form):
        foo = Field.choice(choices=[0, 1], parse=lambda string_value, **_: int(string_value))

    form = MyForm().bind(request=req('post', **{'foo': '0', '-submit': ''}))
    assert form.fields.foo.value == 0
    assert form.fields.foo._errors == set()


def test_custom_raw_data():
    def my_form_raw_data(**_):
        return 'this is custom raw data'

    class MyForm(Form):
        foo = Field(raw_data=my_form_raw_data)

    form = MyForm().bind(request=req('post', **{'-submit': ''}))
    assert form.fields.foo.value == 'this is custom raw data'


def test_custom_raw_data_list():
    # This is useful for example when doing file upload. In that case the data is on request.FILES, not request.POST so we can use this to grab it from there

    def my_form_raw_data(**_):
        return ['this is custom raw data list']

    class MyForm(Form):
        foo = Field(
            raw_data=my_form_raw_data,
            is_list=True,
        )

    form = MyForm().bind(request=req('post', **{'-': ''}))
    assert form.fields.foo.value == ['this is custom raw data list']


def test_custom_raw_data_none():
    def my_form_raw_data(**_):
        return None

    class MyForm(Form):
        foo = Field(raw_data=my_form_raw_data)

    form = MyForm().bind(request=req('post', **{'-submit': '', 'foo': 'bar'}))
    assert form.fields.foo.value == 'bar'


def test_custom_parsed_value():
    def my_form_parsed_data(**_):
        return 'this is custom parsed data'

    class MyForm(Form):
        foo = Field(parsed_data=my_form_parsed_data)

        class Meta:
            def actions__submit__post_handler(form, **_):
                pass  # pragma: no cover

    form = MyForm().bind(request=req('post', **{'-submit': ''}))
    assert form.fields.foo.value == 'this is custom parsed data'


def test_custom_parsed_value_none():
    def my_form_parsed_data(**_):
        return None

    class MyForm(Form):
        foo = Field(parsed_data=my_form_parsed_data)

        class Meta:
            def actions__submit__post_handler(form, **_):
                pass  # pragma: no cover

    form = MyForm().bind(request=req('post', **{'-submit': '', 'foo': 'bar'}))
    assert form.fields.foo.value == 'bar'


def test_parse(MyTestForm):
    # The spaces in the data are there to check that we strip input
    form = MyTestForm().bind(
        request=req(
            'post',
            **{
                'party': 'ABC ',
                'username': 'abc_foo ',
                'joined': ' 2014-12-12 01:02:03  ',
                'staff': ' true',
                'admin': 'false ',
                'manages': ['DEF  ', 'KTH '],
                'a_date': '  2014-02-12  ',
                'a_time': '  01:02:03  ',
                'multi_choice_field': ['a', 'b'],
                '-': '',
            },
        ),
    )

    assert [x._errors for x in values(form.fields)] == [set() for _ in keys(form.fields)]
    assert form.is_valid() is True, form.get_errors()
    assert form.fields['party'].parsed_data == 'ABC'
    assert form.fields['party'].value == 'ABC'

    assert form.fields['username'].parsed_data == 'abc_foo'
    assert form.fields['username'].value == 'abc_foo'

    assert form.fields['joined'].raw_data == '2014-12-12 01:02:03'
    assert form.fields['joined'].parsed_data == datetime(2014, 12, 12, 1, 2, 3)
    assert form.fields['joined'].value == datetime(2014, 12, 12, 1, 2, 3)

    assert form.fields['staff'].raw_data == 'true'
    assert form.fields['staff'].parsed_data is True
    assert form.fields['staff'].value is True

    assert form.fields['admin'].raw_data == 'false'
    assert form.fields['admin'].parsed_data is False
    assert form.fields['admin'].value is False

    assert form.fields['manages'].raw_data == ['DEF', 'KTH']
    assert form.fields['manages'].parsed_data == ['DEF', 'KTH']
    assert form.fields['manages'].value == ['DEF', 'KTH']

    assert form.fields['a_date'].raw_data == '2014-02-12'
    assert form.fields['a_date'].parsed_data == date(2014, 2, 12)
    assert form.fields['a_date'].value == date(2014, 2, 12)

    assert form.fields['a_time'].raw_data == '01:02:03'
    assert form.fields['a_time'].parsed_data == time(1, 2, 3)
    assert form.fields['a_time'].value == time(1, 2, 3)

    assert form.fields['multi_choice_field'].raw_data == ['a', 'b']
    assert form.fields['multi_choice_field'].parsed_data == ['a', 'b']
    assert form.fields['multi_choice_field'].value == ['a', 'b']
    assert form.fields['multi_choice_field'].is_list
    assert not form.fields['multi_choice_field']._errors
    assert form.fields['multi_choice_field'].rendered_value == 'a, b'

    instance = Struct(contact=Struct())
    form.apply(instance)
    assert instance == Struct(
        contact=Struct(joined=datetime(2014, 12, 12, 1, 2, 3)),
        party='ABC',
        staff=True,
        admin=False,
        username='abc_foo',
        manages=['DEF', 'KTH'],
        a_date=date(2014, 2, 12),
        a_time=time(1, 2, 3),
        not_editable='Some non-editable text',
        multi_choice_field=['a', 'b'],
    )


def test_parse_errors(MyTestForm):
    def post_validation(form, **_):
        form.add_error('General snafu')

    form = MyTestForm(post_validation=post_validation,).bind(
        request=req(
            'get',
            **dict(
                party='foo',
                username='bar_foo',
                joined='foo',
                staff='foo',
                admin='foo',
                a_date='foo',
                a_time='bar',
                multi_choice_field=['q', 'w'],
                **{'-submit': ''},
            ),
        ),
    )

    assert form.mode == FULL_FORM_FROM_REQUEST
    assert form.is_valid() is False, form.get_errors()

    assert form._errors == {'General snafu'}

    assert form.fields['party'].parsed_data == 'foo'
    assert form.fields['party']._errors == {'foo not in available choices'}
    assert form.fields['party'].value is None

    assert form.fields['username'].parsed_data == 'bar_foo'
    assert form.fields['username']._errors == {'Username must begin with "foo_"'}
    assert form.fields['username'].value is None

    assert form.fields['joined'].raw_data == 'foo'
    assert_errors_and_matches_reg_exp(
        form.fields['joined']._errors, 'Time data "foo" does not match any of the formats .*'
    )
    assert form.fields['joined'].parsed_data is None
    assert form.fields['joined'].value is None

    assert form.fields['staff'].raw_data == 'foo'
    assert form.fields['staff'].parsed_data is None
    assert form.fields['staff'].value is None

    assert form.fields['admin'].raw_data == 'foo'
    assert form.fields['admin'].parsed_data is None
    assert form.fields['admin'].value is None

    assert form.fields['a_date'].raw_data == 'foo'
    assert_errors_and_matches_reg_exp(
        form.fields['a_date']._errors, 'Time data "foo" does not match any of the formats.*'
    )
    assert form.fields['a_date'].parsed_data is None
    assert form.fields['a_date'].value is None
    assert form.fields['a_date'].rendered_value == form.fields['a_date'].raw_data

    assert form.fields['a_time'].raw_data == 'bar'
    assert_errors_and_matches_reg_exp(
        form.fields['a_time']._errors, 'Time data "bar" does not match any of the formats.*'
    )
    assert form.fields['a_time'].parsed_data is None
    assert form.fields['a_time'].value is None

    assert form.fields['multi_choice_field'].raw_data == ['q', 'w']
    assert_errors_and_matches_reg_exp(
        form.fields['multi_choice_field']._errors, "[qw] not in available choices", count=2
    )
    assert form.fields['multi_choice_field'].parsed_data == ['q', 'w']
    assert form.fields['multi_choice_field'].value is None

    with pytest.raises(AssertionError):
        form.apply(Struct())


def test_post_validation_and_error_checking_initial():
    timeline = []

    def capture_timeline(form):
        timeline.append(
            dict(
                mode=form.mode,
                is_valid=form.is_valid(),
                errors=form.get_errors(),
            )
        )

    def first__post_validation(form, field, **_):
        capture_timeline(form)
        field.add_error('first error')

    def second__post_validation(form, field, **_):
        capture_timeline(form)
        field.add_error('second error')

    class MyForm(Form):
        first = Field(post_validation=first__post_validation)
        second = Field(post_validation=second__post_validation)

    form = MyForm().bind(request=req('get'))
    capture_timeline(form)

    assert timeline == [
        {'mode': 'initials_from_get', 'is_valid': True, 'errors': {}},
        {'mode': 'initials_from_get', 'is_valid': False, 'errors': {'fields': {'first': {'first error'}}}},
        {
            'mode': 'initials_from_get',
            'is_valid': False,
            'errors': {'fields': {'first': {'first error'}, 'second': {'second error'}}},
        },
    ]


def test_post_validation_and_error_checking_full():
    timeline = []

    def capture_timeline(form):
        timeline.append(
            dict(
                mode=form.mode,
                is_valid=form.is_valid(),
                errors=form.get_errors(),
            )
        )

    def first__post_validation(form, field, **_):
        capture_timeline(form)
        field.add_error('first error')

    def second__post_validation(form, field, **_):
        capture_timeline(form)
        field.add_error('second error')

    def form__post_validation(form, **_):
        capture_timeline(form)
        form.add_error('global error')

    class MyForm(Form):
        first = Field(post_validation=first__post_validation)
        second = Field(post_validation=second__post_validation)

        class Meta:
            post_validation = form__post_validation

            def actions__submit__post_handler(form, **_):
                return form

    form = MyForm().bind(request=req('post', **{'-submit': '', 'first': 'First', 'second': 'Second'}))
    form.render_to_response()
    capture_timeline(form)

    assert timeline == [
        {'mode': 'full_form_from_request', 'is_valid': True, 'errors': {}},
        {'mode': 'full_form_from_request', 'is_valid': False, 'errors': {'fields': {'first': {'first error'}}}},
        {
            'mode': 'full_form_from_request',
            'is_valid': False,
            'errors': {'fields': {'first': {'first error'}, 'second': {'second error'}}},
        },
        {
            'mode': 'full_form_from_request',
            'is_valid': False,
            'errors': {'fields': {'first': {'first error'}, 'second': {'second error'}}, 'global': {'global error'}},
        },
    ]


def test_initial_from_instance():
    assert (
        Form(
            instance=Struct(a=Struct(b=7)),
            fields__foo=Field(attr='a__b'),
        )
        .bind(
            request=req('get'),
        )
        .fields.foo.initial
        == 7
    )


def test_initial_from_instance_override():
    assert (
        Form(
            instance=Struct(a=Struct(b=7)),
            fields__foo=Field(attr='a__b', initial=11),
        )
        .bind(
            request=req('get'),
        )
        .fields.foo.initial
        == 11
    )


def test_initial_from_instance_is_list():
    assert (
        Form(
            instance=Struct(a=Struct(b=[7])),
            fields__foo=Field(attr='a__b', is_list=True),
        )
        .bind(
            request=req('get'),
        )
        .fields.foo.initial
        == [7]
    )


def test_non_editable_from_initial():
    class MyForm(Form):
        foo = Field(editable=False, initial=':bar:')

    assert ':bar:' in MyForm().bind(request=req('get')).__html__()
    assert ':bar:' in MyForm().bind(request=req('post', **{'-': ''})).__html__()


def test_apply():
    form = Form(fields__foo=Field(initial=17, editable=False),).bind(
        request=req('get'),
    )
    assert Struct(foo=17) == form.apply(Struct())


def test_include():
    assert list(Form(fields__foo=Field(include=True)).bind(request=req('get')).fields.keys()) == ['foo']
    assert list(Form(fields__foo=Field(include=False)).bind(request=req('get')).fields.keys()) == []
    assert list(Form(fields__foo=Field(include=None)).bind(request=req('get')).fields.keys()) == []
    assert list(
        Form(fields__foo=Field(include=lambda form, field, **_: True)).bind(request=req('get')).fields.keys()
    ) == ['foo']
    assert (
        list(Form(fields__foo=Field(include=lambda form, field, **_: False)).bind(request=req('get')).fields.keys())
        == []
    )
    assert (
        list(Form(fields__foo=Field(include=lambda form, field, **_: None)).bind(request=req('get')).fields.keys())
        == []
    )


def test_declared_fields():
    form = Form(fields=dict(foo=Field(include=True), bar=Field(include=False),),).bind(
        request=req('get'),
    )
    assert list(declared_members(form).fields.keys()) == ['foo', 'bar']
    assert list(form.fields.keys()) == ['foo']


def test_non_editable():
    actual = prettify(
        Form(
            fields__foo=Field(editable=False, input__attrs__custom=7, initial='11'),
        )
        .bind(
            request=req('get'),
        )
        .fields.foo.__html__()
    )

    expected = prettify(
        """
        <div>
            <label for="id_foo">Foo</label>
            <span custom="7" id="id_foo" name="foo">11</span>
        </div>
    """
    )

    assert actual == expected


def test_editable():
    actual = prettify(
        Form(
            fields__foo=Field(input__attrs__custom=7, initial='11'),
        )
        .bind(
            request=req('get'),
        )
        .fields.foo.__html__()
    )

    expected = prettify(
        """
        <div>
            <label for="id_foo">Foo</label>
            <input custom="7" id="id_foo" name="foo" type="text" value="11"/>
        </div>
    """
    )

    assert actual == expected


def test_non_editable_form():
    form = Form(
        editable=False,
        instance=Struct(foo=3, bar=4),
        fields=dict(
            foo=Field.integer(),
            bar=Field.integer(editable=False),
        ),
    ).bind(
        request=req('get', foo='1', bar='2'),
    )
    assert 3 == form.fields.foo.value
    assert 4 == form.fields.bar.value
    assert False is form.fields.foo.editable
    assert False is form.fields.bar.editable


def test_text_field():
    rendered_form = str(Form(fields__foo=Field.text()).bind(request=req('get')))
    foo = BeautifulSoup(rendered_form, 'html.parser').find(id='id_foo')
    assert foo.name == 'input'
    assert get_attrs(foo, ['type']) == {'type': 'text'}


def test_textarea_field():
    form = Form(fields__foo=Field.textarea(initial='test')).bind(request=req('get'))
    assert form.fields.foo.initial == 'test'
    assert form.fields.foo.value == 'test'
    assert form.fields.foo.rendered_value == 'test'
    rendered_form = str(form)
    foo = BeautifulSoup(rendered_form, 'html.parser').find(id='id_foo')
    assert foo.name == 'textarea', rendered_form
    assert get_attrs(foo, ['type']) == {'type': None}
    assert foo.text == 'test'
    assert 'value="test">' not in rendered_form


def test_integer_field():
    assert (
        Form(
            fields__foo=Field.integer(),
        )
        .bind(request=req('get', foo=' 7  '))
        .fields.foo.parsed_data
        == 7
    )

    actual_errors = Form(fields__foo=Field.integer()).bind(request=req('get', foo=' foo  ')).fields.foo._errors
    assert_errors_and_matches_reg_exp(actual_errors, r"invalid literal for int\(\) with base 10: 'foo'")


def test_float_field():
    assert Form(fields__foo=Field.float()).bind(request=req('get', foo=' 7.3  ')).fields.foo.parsed_data == 7.3
    assert Form(fields__foo=Field.float()).bind(request=req('get', foo=' foo  ')).fields.foo._errors == {
        "could not convert string to float: foo"
    }


def test_email_field():
    assert Form(fields__foo=Field.email()).bind(request=req('get', foo=' 5  ')).fields.foo._errors == {
        u'Enter a valid email address.'
    }
    assert Form(fields__foo=Field.email()).bind(request=req('get', foo='foo@example.com')).is_valid()


def test_phone_field():
    assert Form(fields__foo=Field.phone_number()).bind(request=req('get', foo=' asdasd  ')).fields.foo._errors == {
        u'Please use format +<country code> (XX) XX XX. Example of US number: +1 (212) 123 4567 or +1 212 123 4567'
    }
    assert Form(fields__foo=Field.phone_number()).bind(request=req('get', foo='+1 (212) 123 4567')).is_valid()
    assert Form(fields__foo=Field.phone_number()).bind(request=req('get', foo='+46 70 123 123')).is_valid()


def test_render_template_string():
    form = Form(fields__foo=Field(_name='foo', template=Template('{{ field.value }} {{ field.display_name }}')))
    form = form.bind(request=req('get', foo='7'))
    assert form.fields.foo.__html__() == '7 Foo'


def test_render_template():
    assert '<form' in Form(fields__foo=Field()).bind(request=req('get', foo='7')).__html__()


def test_render_on_dunder_html():
    form = Form(fields__foo=Field()).bind(request=req('get', foo='7'))
    assert remove_csrf(form.__html__()) == remove_csrf(form.__html__())  # used by jinja2


def test_render_attrs():
    assert (
        str(Form(fields__foo=Field(attrs={'foo': '1'})).bind(request=req('get', foo='7')).fields.foo.attrs)
        == ' foo="1"'
    )
    assert str(Form(fields__foo=Field()).bind(request=req('get', foo='7')).fields.foo.attrs) == ''
    assert render_attrs(dict(foo='"foo"')) == ' foo="&quot;foo&quot;"'


def test_render_attrs_new_style():
    assert (
        str(Form(fields__foo=Field(_name='foo', attrs__foo='1')).bind(request=req('get', foo='7')).fields.foo.attrs)
        == ' foo="1"'
    )
    assert str(Form(fields__foo=Field(_name='foo')).bind(request=req('get', foo='7')).fields.foo.attrs) == ''


def test_render_attrs_bug_with_curly_brace():
    assert render_attrs(dict(foo='{foo}')) == ' foo="{foo}"'


def test_getattr_path():
    assert getattr_path(Struct(a=1), 'a') == 1
    assert getattr_path(Struct(a=Struct(b=2)), 'a__b') == 2
    with pytest.raises(AttributeError):
        getattr_path(Struct(a=2), 'b')

    assert getattr_path(Struct(a=None), 'a__b__c__d') is None


def test_setattr_path():
    assert getattr_path(setattr_path(Struct(a=0), 'a', 1), 'a') == 1
    assert getattr_path(setattr_path(Struct(a=Struct(b=0)), 'a__b', 2), 'a__b') == 2

    with pytest.raises(AttributeError):
        setattr_path(Struct(a=1), 'a__b', 1)


def test_multi_select_with_one_value_only():
    assert (
        Form(
            fields__foo=Field.multi_choice(_name='foo', choices=['a', 'b']),
        )
        .bind(request=req('get', foo=['a']))
        .fields.foo.value
        == ['a']
    )


def test_render_misc_attributes():
    class MyForm(Form):
        foo = Field(
            attrs__class=dict(**{'@@@@21@@@@': True}),
            input__attrs__class=dict(**{'###5###': True}),
            label__attrs__class=dict(**{'$$$11$$$': True}),
            help_text='^^^13^^^',
            display_name='***17***',
            attrs__id='$$$$5$$$$$',
        )

    table = MyForm().bind(request=req('get', foo='!!!7!!!')).__html__()
    assert '!!!7!!!' in table
    assert '###5###' in table
    assert '$$$11$$$' in table
    assert '^^^13^^^' in table
    assert '***17***' in table
    assert '@@@@21@@@@' in table
    assert 'id="$$$$5$$$$$"' in table


def test_heading():
    assert '>#foo#</' in Form(fields__heading=Field.heading(display_name='#foo#')).bind(request=req('get')).__html__()


def test_none_title_from_display_name():
    assert Form(fields__foo=Field(display_name=None)).bind(request=req('get')).fields.foo.label is None


def test_info():
    form = Form(fields__foo=Field.info(value='#foo#')).bind(request=req('get'))
    assert form.is_valid() is True, form.get_errors()
    assert '#foo#' in form.__html__()


def test_radio():
    choices = [
        'a',
        'b',
        'c',
    ]
    req('get')
    form = Form(fields__foo=Field.radio(choices=choices),).bind(
        request=req('get', foo='a'),
    )
    soup = BeautifulSoup(form.__html__(), 'html.parser')
    items = [x for x in soup.find_all('input') if x.attrs['type'] == 'radio']
    assert len(items) == 3
    assert [x.attrs['value'] for x in items if 'checked' in x.attrs] == ['a']


def test_radio_full_render():
    choices = [
        'a',
        'b',
        'c',
    ]
    req('get')
    form = Form(fields__foo=Field.radio(choices=choices),).bind(
        request=req('get', foo='a'),
    )
    first = form.fields.foo.__html__()
    second = form.fields.foo.__html__()
    assert first == second
    actual = prettify(first)
    expected = prettify(
        """
<div>
    <label for="id_foo">Foo</label>

    <div>

        <input type="radio" value="a" name="foo" id="id_foo_1" name="foo" checked/>
        <label for="id_foo_1">a</label>

    </div>

    <div>

        <input type="radio" value="b" name="foo" id="id_foo_2" name="foo" />
        <label for="id_foo_2">b</label>

    </div>

    <div>

        <input type="radio" value="c" name="foo" id="id_foo_3" name="foo" />
        <label for="id_foo_3">c</label>

    </div>

</div>

    """
    )
    assert actual == expected


def test_hidden():
    soup = BeautifulSoup(Form(fields__foo=Field.hidden()).bind(request=req('get', foo='1')).__html__(), 'html.parser')
    x = soup.find(id='id_foo')
    assert get_attrs(x, ['type', 'name', 'value']) == dict(type='hidden', name='foo', value='1')


def test_hidden_with_name():
    class MyPage(Page):
        baz = Form(
            fields__foo=Field.hidden(),
            attrs__method='get',
        )

    page = MyPage().bind(request=req('get', **{'foo': '1'}))
    rendered_page = page.__html__()

    assert page.parts.baz._is_bound
    assert page.parts.baz.mode == INITIALS_FROM_GET

    soup = BeautifulSoup(rendered_page, 'html.parser')
    actual = {
        (x.attrs['type'], x.attrs.get('name'), x.attrs['value'])
        for x in soup.find_all('input')
        if x.attrs['type'] == 'hidden'
    }
    expected = {
        ('hidden', 'foo', '1'),
    }

    assert actual == expected


def test_password():
    assert ' type="password" ' in Form(fields__foo=Field.password()).bind(request=req('get', foo='1')).__html__()


def test_choice_not_required():
    class MyForm(Form):
        foo = Field.choice(required=False, choices=['bar'])

    assert MyForm().bind(request=req('post', **{'foo': 'bar', '-': ''})).fields.foo.value == 'bar'
    assert MyForm().bind(request=req('post', **{'foo': '', '-': ''})).fields.foo.value is None


def test_multi_choice():
    soup = BeautifulSoup(
        Form(fields__foo=Field.multi_choice(choices=['a']))
        .bind(
            request=req('get', foo=['0']),
        )
        .__html__(),
        'html.parser',
    )
    assert [x.attrs['multiple'] for x in soup.find_all('select')] == ['']


@pytest.mark.django
def test_help_text_from_model():
    from tests.models import Foo

    assert (
        Form(
            model=Foo,
            fields__foo=Field.from_model(model=Foo, model_field_name='foo'),
        )
        .bind(
            request=req('get', foo='1'),
        )
        .fields.foo.help_text
        == 'foo_help_text'
    )


@pytest.mark.django_db
def test_display_name_callable():
    from tests.models import Foo

    sentinel = '#### foo ####'
    form = Form(
        auto__model=Foo,
        auto__include=['foo'],
        fields__foo__display_name=lambda **_: sentinel,
    ).bind(request=req('get', foo='1'))
    assert sentinel in form.__html__()


@pytest.mark.django_db
def test_help_text_from_model2():
    from tests.models import Foo, Bar

    # simple integer field
    form = Form(auto__model=Foo, auto__include=['foo']).bind(request=req('get', foo='1'))
    assert form.fields.foo.model_field is Foo._meta.get_field('foo')
    assert form.fields.foo.help_text == 'foo_help_text'

    # foreign key field
    Bar.objects.create(foo=Foo.objects.create(foo=1))
    form = Form(auto__model=Bar, auto__include=['foo']).bind(request=req('get'))
    assert form.fields.foo.help_text == 'bar_help_text'
    assert form.fields.foo.model is Foo


@pytest.mark.django_db
def test_multi_choice_queryset():
    from django.contrib.auth.models import User

    user = User.objects.create(username='foo')
    user2 = User.objects.create(username='foo2')
    user3 = User.objects.create(username='foo3')

    class MyForm(Form):
        foo = Field.multi_choice_queryset(attr=None, choices=User.objects.filter(username=user.username))

    assert [x.pk for x in MyForm().bind(request=req('get')).fields.foo.choices] == [user.pk]
    assert MyForm().bind(request=req('get', foo=smart_str(user2.pk))).fields.foo._errors == {
        'User matching query does not exist.'
    }
    assert MyForm().bind(request=req('get', foo=[smart_str(user2.pk), smart_str(user3.pk)])).fields.foo._errors == {
        'User matching query does not exist.'
    }

    form = MyForm().bind(request=req('get', foo=[smart_str(user.pk)]))
    assert form.fields.foo._errors == set()
    result = form.__html__()
    assert (
        str(BeautifulSoup(result, "html.parser").select('#id_foo')[0])
        == '<select id="id_foo" multiple="" name="foo">\n<option label="foo" selected="selected" value="1">foo</option>\n</select>'
    )


@pytest.mark.django_db
def test_choice_queryset():
    from django.contrib.auth.models import User

    user = User.objects.create(username='foo')
    user2 = User.objects.create(username='foo2')
    User.objects.create(username='foo3')

    class MyForm(Form):
        foo = Field.choice_queryset(attr=None, choices=User.objects.filter(username=user.username))

    assert [x.pk for x in MyForm().bind(request=req('get')).fields.foo.choices] == [user.pk]
    assert MyForm().bind(request=req('get', foo=smart_str(user2.pk))).fields.foo._errors == {
        'User matching query does not exist.'
    }

    form = MyForm().bind(request=req('get', foo=[smart_str(user.pk)]))
    assert form.fields.foo._errors == set()
    result = form.__html__()
    assert (
        str(BeautifulSoup(result, "html.parser").select('#id_foo')[0])
        == '<select id="id_foo" name="foo">\n<option label="foo" selected="selected" value="1">foo</option>\n</select>'
    )


@pytest.mark.django_db
def test_choice_queryset_do_not_cache():
    from django.contrib.auth.models import User

    User.objects.create(username='foo')

    class MyForm(Form):
        foo = Field.choice_queryset(attr=None, choices=User.objects.all(), template='iommi/form/choice.html')

    # There is just one user, check that we get it
    form = MyForm().bind(request=req('get'))
    assert form.fields.foo._errors == set()

    assert (
        str(BeautifulSoup(form.__html__(), "html.parser").select('select')[0])
        == '<select id="id_foo" name="foo">\n<option value="1">foo</option>\n</select>'
    )

    # Now create a new queryset, check that we get two!
    User.objects.create(username='foo2')
    form = MyForm().bind(request=req('get'))
    assert form.fields.foo._errors == set()
    assert (
        str(BeautifulSoup(form.__html__(), "html.parser").select('select')[0])
        == '<select id="id_foo" name="foo">\n<option value="1">foo</option>\n<option value="2">foo2</option>\n</select>'
    )


@pytest.mark.django_db
def test_choice_queryset_do_not_look_up_by_default():
    from django.contrib.auth.models import User

    user = User.objects.create(username='foo')

    class MyForm(Form):
        foo = Field.choice_queryset(attr=None, choices=User.objects.all())

    form = MyForm().bind(request=req('get'))
    assert form.fields.foo._errors == set()

    # The list should be empty because options are retrieved via ajax when needed
    assert (
        str(BeautifulSoup(form.__html__(), "html.parser").select('select')[0])
        == '<select id="id_foo" name="foo">\n</select>'
    )
    assert form.fields.foo.input.template is not None

    # Now check that it renders the selected value
    form = MyForm(fields__foo__initial=user).bind(request=req('get'))
    assert form.fields.foo.value == user
    assert form.fields.foo._errors == set()

    assert form.fields.foo.input.template is not None

    expected = (
        '<select id="id_foo" name="foo">\n<option label="foo" selected="selected" value="1">foo</option>\n</select>'
    )
    assert str(BeautifulSoup(form.__html__(), "html.parser").select('select')[0]) == expected


@pytest.mark.django
def test_field_from_model():
    from tests.models import Foo

    class FooForm(Form):
        foo = Field.from_model(Foo, 'foo')

        class Meta:
            model = Foo

    assert FooForm().bind(request=req('get', foo='1')).fields.foo.value == 1
    assert not FooForm().bind(request=req('get', foo='asd')).is_valid()


@pytest.mark.django_db
def test_field_from_model_foreign_key_choices():
    from tests.models import Foo, Bar

    foo = Foo.objects.create(foo=1)
    foo2 = Foo.objects.create(foo=2)
    Bar.objects.create(foo=foo)
    Bar.objects.create(foo=foo2)

    class FooForm(Form):
        # Choices is a lambda here to avoid Field.field_choice_queryset grabbing the model from the queryset object
        foo = Field.from_model(Bar, 'foo', choices=lambda form, field, **_: Foo.objects.all())

    assert list(FooForm().bind(request=req('get')).fields.foo.choices) == list(Foo.objects.all())
    form = FooForm().bind(request=req('post', foo=str(foo2.pk)))
    bar = Bar()
    form.apply(bar)
    bar.save()
    assert bar.foo == foo2
    assert Bar.objects.get(pk=bar.pk).foo == foo2


@pytest.mark.django_db
def test_field_validate_foreign_key_does_not_exist():
    from tests.models import Foo, FieldFromModelForeignKeyTest

    foo = Foo.objects.create(foo=17)
    assert Foo.objects.count() == 1

    class MyForm(Form):
        class Meta:
            fields = Form.fields_from_model(model=FieldFromModelForeignKeyTest)

    assert MyForm().bind(request=req('post', foo_fk=foo.pk)).is_valid() is True
    assert MyForm().bind(request=req('post', foo_fk=foo.pk + 1)).is_valid() is False


@pytest.mark.django
def test_form_default_fields_from_model():
    from tests.models import Foo

    class FooForm(Form):
        class Meta:
            fields = Form.fields_from_model(model=Foo)
            fields__bar = Field.text(attr=None)

    assert set(FooForm().bind(request=req('get')).fields.keys()) == {'foo', 'bar'}
    assert FooForm().bind(request=req('get', foo='1')).fields.foo.value == 1
    assert not FooForm().bind(request=req('get', foo='asd')).is_valid()


@pytest.mark.django
@pytest.mark.filterwarnings("ignore:Model 'tests.foomodel' was already registered")
def test_field_from_model_required():
    from django.db.models import TextField, Model

    class FooModel(Model):
        a = TextField(blank=True, null=True)
        b = TextField(blank=True, null=False)
        c = TextField(blank=False, null=True)
        d = TextField(blank=False, null=False)

    assert not Field.from_model(FooModel, 'a').required
    assert not Field.from_model(FooModel, 'b').required
    assert not Field.from_model(FooModel, 'c').required
    assert Field.from_model(FooModel, 'd').required


@pytest.mark.django
@pytest.mark.filterwarnings("ignore:Model 'tests.foomodel' was already registered")
def test_field_from_model_label():
    from django.db.models import TextField, Model

    class FieldFromModelModel(Model):
        a = TextField(verbose_name='FOOO bar FOO')

    assert Field.from_model(FieldFromModelModel, 'a').display_name == 'FOOO bar FOO'


@pytest.mark.django_db
def test_form_from_model_valid_form():
    from tests.models import FormFromModelTest

    assert [
        x.value
        for x in values(
            Form(
                auto__model=FormFromModelTest,
                auto__include=['f_int', 'f_float', 'f_bool'],
            )
            .bind(
                request=req('get', f_int='1', f_float='1.1', f_bool='true'),
            )
            .fields
        )
    ] == [1, 1.1, True]


@pytest.mark.django_db
def test_form_from_model_error_message_include():
    from tests.models import FormFromModelTest

    with pytest.raises(AssertionError) as e:
        Form(auto__model=FormFromModelTest, auto__include=['does_not_exist', 'f_float']).bind(request=None)

    assert (
        str(e.value)
        == 'You can only include fields that exist on the model: does_not_exist specified but does not exist\n'
        'Existing fields:\n'
        '    f_bool\n'
        '    f_file\n'
        '    f_float\n'
        '    f_int\n'
        '    f_int_excluded\n'
        '    id\n'
        '    pk'
    )


@pytest.mark.django_db
def test_form_from_model_error_message_exclude():
    from tests.models import FormFromModelTest

    with pytest.raises(AssertionError) as e:
        Form(auto__model=FormFromModelTest, auto__exclude=['does_not_exist', 'f_float']).bind(request=None)

    assert (
        str(e.value)
        == 'You can only exclude fields that exist on the model: does_not_exist specified but does not exist\n'
        'Existing fields:\n'
        '    f_bool\n'
        '    f_file\n'
        '    f_float\n'
        '    f_int\n'
        '    f_int_excluded\n'
        '    id\n'
        '    pk'
    )


@pytest.mark.django
def test_form_from_model_invalid_form():
    from tests.models import FormFromModelTest

    actual_errors = [
        x._errors
        for x in values(
            Form(
                auto__model=FormFromModelTest,
                auto__exclude=['f_int_excluded'],
            )
            .bind(
                request=req('get', f_int='1.1', f_float='true', f_bool='asd', f_file='foo'),
            )
            .fields
        )
    ]

    assert len(actual_errors) == 4
    assert {'could not convert string to float: true'} in actual_errors
    assert {u'asd is not a valid boolean value'} in actual_errors
    assert {"invalid literal for int() with base 10: '1.1'"} in actual_errors or {
        "invalid literal for int() with base 10: u'1.1'"
    } in actual_errors


@pytest.mark.django
def test_field_from_model_supports_all_types():
    from tests.models import Foo

    from django.db.models import fields

    not_supported = []
    blacklist = {
        'Field',
        'NullBooleanField',
        'BinaryField',
        'IPAddressField',
        'DurationField',
    }
    field_type_names = [x for x in dir(fields) if x.endswith('Field') and x not in blacklist]

    for name in field_type_names:
        field_type = getattr(fields, name)
        try:
            Field.from_model(model=Foo, model_field=field_type())
        except AssertionError:  # pragma: no cover
            not_supported.append(name)

    assert not_supported == []


@pytest.mark.django
def test_field_from_model_blank_handling():
    from tests.models import Foo

    from django.db.models import CharField

    subject = Field.from_model(model=Foo, model_field=CharField(null=True, blank=False))
    assert True is subject.parse_empty_string_as_none

    subject = Field.from_model(model=Foo, model_field=CharField(null=False, blank=True))
    assert False is subject.parse_empty_string_as_none


@pytest.mark.django
def test_overriding_parse_empty_string_as_none_in_shortcut():
    from tests.models import Foo

    from django.db.models import CharField

    s = Shortcut(
        call_target=Field.text,
        parse_empty_string_as_none='foo',
    )
    # test overriding parse_empty_string_as_none
    x = member_from_model(
        cls=Field,
        model=Foo,
        model_field=CharField(blank=True),
        factory_lookup={CharField: s},
        factory_lookup_register_function=register_field_factory,
        defaults_factory=field_defaults_factory,
    )

    assert 'foo' == x.parse_empty_string_as_none


@pytest.mark.django_db
def test_field_from_model_foreign_key():
    from django.db.models import QuerySet
    from tests.models import Foo, FieldFromModelForeignKeyTest

    Foo.objects.create(foo=2)
    Foo.objects.create(foo=3)
    Foo.objects.create(foo=5)

    class MyForm(Form):
        c = Field.from_model(FieldFromModelForeignKeyTest, 'foo_fk')

    form = MyForm().bind(request=req('get'))
    choices = form.fields.c.choices
    assert isinstance(choices, QuerySet)
    assert set(choices) == set(Foo.objects.all())


@pytest.mark.django_db
def test_field_from_model_many_to_many():
    from django.db.models import QuerySet
    from tests.models import Foo, FieldFromModelManyToManyTest

    Foo.objects.create(foo=2)
    b = Foo.objects.create(foo=3)
    c = Foo.objects.create(foo=5)

    class MyForm(Form):
        foo_many_to_many = Field.from_model(FieldFromModelManyToManyTest, 'foo_many_to_many')

    form = MyForm().bind(request=req('get'))
    choices = form.fields.foo_many_to_many.choices

    assert isinstance(choices, QuerySet)
    assert set(choices) == set(Foo.objects.all())
    m2m = FieldFromModelManyToManyTest.objects.create()
    assert set(MyForm(instance=m2m).bind(request=req('get')).fields.foo_many_to_many.initial) == set()
    m2m.foo_many_to_many.add(b)
    assert set(MyForm(instance=m2m).bind(request=req('get')).fields.foo_many_to_many.initial) == {b}
    m2m.foo_many_to_many.add(c)
    assert set(MyForm(instance=m2m).bind(request=req('get')).fields.foo_many_to_many.initial) == {b, c}


@pytest.mark.django_db
def test_field_from_model_many_to_one_foreign_key():
    from tests.models import Bar

    assert (
        set(
            Form(auto__model=Bar, fields__foo__call_target=Field.from_model)
            .bind(
                request=req('get'),
            )
            .fields.keys()
        )
        == {'foo'}
    )


@pytest.mark.django
def test_register_field_factory():
    from tests.models import FooField, RegisterFieldFactoryTest

    register_field_factory(FooField, factory=lambda **kwargs: 7)

    assert Field.from_model(RegisterFieldFactoryTest, 'foo') == 7


def shortcut_test(shortcut, raw_and_parsed_data_tuples, normalizing=None, is_list=False):
    if normalizing is None:
        normalizing = []

    SENTINEL = object()

    def test_empty_string_data():
        f = Form(fields__foo=shortcut(required=False,),).bind(
            request=req('get', foo=''),
        )
        assert not f.get_errors()
        assert f.fields.foo.value in (None, [])
        assert f.fields.foo.rendered_value == ''

    def test_empty_data():
        f = Form(fields__foo=shortcut(required=False,),).bind(
            request=req('get'),
        )
        assert not f.get_errors()
        assert f.fields.foo.value in (None, [])

    def test_editable_false():
        f = Form(fields__foo=shortcut(required=False, initial=SENTINEL, editable=False),).bind(
            request=req('get', foo='asdasasd'),
        )
        assert not f.get_errors()
        assert f.fields.foo.value is SENTINEL

    def test_editable_false_list():
        f = Form(fields__foo=shortcut(required=False, initial=[SENTINEL], editable=False),).bind(
            request=req('get', foo='asdasasd'),
        )
        assert not f.get_errors()
        assert f.fields.foo.value == [SENTINEL]

    def test_roundtrip_from_initial_to_raw_string():
        for raw, initial in raw_and_parsed_data_tuples:
            form = Form(fields__foo=shortcut(required=True, initial=initial),).bind(
                request=req('get'),
            )
            assert not form.get_errors()
            f = form.fields.foo
            assert not f.is_list
            assert initial == f.value
            assert raw == f.rendered_value, 'Roundtrip failed'

    def test_roundtrip_from_initial_to_raw_string_list():
        for raw, initial in raw_and_parsed_data_tuples:
            form = Form(fields__foo=shortcut(required=True, initial=initial),).bind(
                request=req('get'),
            )
            assert not form.get_errors()
            f = form.fields.foo
            assert f.initial == initial
            assert f.is_list
            assert f.value == initial
            assert ', '.join([str(x) for x in raw]) == f.rendered_value, 'Roundtrip failed'

    def test_roundtrip_from_raw_string_to_initial():
        for raw, initial in raw_and_parsed_data_tuples:
            form = Form(fields__foo=shortcut(required=True,),).bind(
                request=req('get', foo=raw),
            )
            assert not form.get_errors(), 'input: %s' % raw
            f = form.fields.foo
            assert f.raw_data == raw
            assert f.value == initial
            if f.is_list:
                if initial:
                    assert [type(x) for x in f.value] == [type(x) for x in initial]
            else:
                assert type(f.value) == type(initial)

    def test_normalizing():
        for non_normalized, normalized in normalizing:
            form = Form(fields__foo=shortcut(required=True,),).bind(
                request=req('get', foo=non_normalized),
            )
            assert not form.get_errors()
            assert form.fields.foo.rendered_value == normalized

    def test_parse():
        for raw, parsed in raw_and_parsed_data_tuples:
            form = Form(fields__foo=shortcut(required=True,),).bind(
                request=req('get', foo=raw),
            )
            assert not form.get_errors(), 'input: %s' % raw
            f = form.fields.foo
            assert f.raw_data == raw
            if parsed is None and f.is_list:
                parsed = []
            assert f.parsed_data == parsed

    test_roundtrip_from_raw_string_to_initial()
    test_empty_string_data()
    test_empty_data()
    test_normalizing()
    test_parse()

    if is_list:
        test_roundtrip_from_initial_to_raw_string_list()
        test_editable_false_list()
    else:
        test_roundtrip_from_initial_to_raw_string()
        test_editable_false()


def test_datetime():
    shortcut_test(
        Field.datetime,
        raw_and_parsed_data_tuples=[
            ('2001-02-03 12:13:14', datetime(2001, 2, 3, 12, 13, 14)),
        ],
        normalizing=[
            ('2001-02-03 12:13', '2001-02-03 12:13:00'),
            ('2001-02-03 12', '2001-02-03 12:00:00'),
        ],
    )


def test_date():
    shortcut_test(
        Field.date,
        raw_and_parsed_data_tuples=[
            ('2001-02-03', date(2001, 2, 3)),
        ],
    )


def test_time():
    shortcut_test(
        Field.time,
        raw_and_parsed_data_tuples=[
            ('12:34:56', time(12, 34, 56)),
        ],
        normalizing=[
            ('2:34:56', '02:34:56'),
        ],
    )


def test_integer():
    shortcut_test(
        Field.integer,
        raw_and_parsed_data_tuples=[
            ('123', 123),
        ],
        normalizing=[
            ('00123', '123'),
        ],
    )


def test_float():
    shortcut_test(
        Field.float,
        raw_and_parsed_data_tuples=[
            ('123.0', 123.0),
            ('123.123', 123.123),
        ],
        normalizing=[
            ('123', '123.0'),
            ('00123', '123.0'),
            ('00123.123', '123.123'),
        ],
    )


def test_multi_choice_shortcut():
    shortcut_test(
        Namespace(
            call_target=Field.multi_choice,
            choices=['a', 'b', 'c'],
        ),
        is_list=True,
        raw_and_parsed_data_tuples=[
            (['b', 'c'], ['b', 'c']),
            ([], None),
        ],
    )


def test_choice_shortcut():
    shortcut_test(
        Namespace(
            call_target=Field.choice,
            choices=[1, 2, 3],
        ),
        raw_and_parsed_data_tuples=[
            ('1', 1),
        ],
    )


def test_render_custom():
    sentinel = '!!custom!!'
    assert (
        sentinel
        in Form(fields__foo=Field(initial='not sentinel value', render_value=lambda form, field, value: sentinel))
        .bind(request=req('get'))
        .__html__()
    )


def test_boolean_initial_true():
    fields = dict(
        foo=Field.boolean(initial=True),
        bar=Field(required=False),
    )

    def submit(form, **_):
        pass  # pragma: no cover

    form = Form(fields=fields).bind(request=req('get'))
    assert form.fields.foo.value is True

    # If there are arguments, but not for key foo it means checkbox for foo has been unchecked.
    # Field foo should therefore be false.
    form = Form(fields=fields, actions__submit__post_handler=submit).bind(
        request=RequestFactory().get('/', dict(bar='baz', **{'-submit': ''}))
    )
    assert form.fields.foo.value is False

    form = Form(fields=fields, actions__submit__post_handler=submit).bind(
        request=RequestFactory().get('/', dict(foo='on', bar='baz', **{'-submit': ''}))
    )
    assert form.fields.foo.value is True


def test_file():
    class FooForm(Form):
        foo = Field.file(required=False)

    file_data = '1'
    fake_file = StringIO(file_data)

    form = FooForm().bind(request=req('post', foo=fake_file))
    instance = Struct(foo=None)
    assert form.is_valid() is True, form.get_errors()
    form.apply(instance)
    assert instance.foo.file.getvalue() == b'1'

    # Non-existent form entry should not overwrite data
    form = FooForm().bind(request=req('post', foo=''))
    assert form.is_valid(), form.get_errors()
    form.apply(instance)
    assert instance.foo.file.getvalue() == b'1'

    form = FooForm().bind(request=req('post'))
    assert form.is_valid(), form.get_errors()
    form.apply(instance)
    assert instance.foo.file.getvalue() == b'1'


@pytest.mark.django
def test_file_no_roundtrip():
    class FooForm(Form):
        foo = Field.file(is_valid=lambda form, field, parsed_data: (False, 'invalid!'))

    fake_file = BytesIO(b'binary_content_here')

    form = FooForm().bind(request=req('post', foo=fake_file))
    assert form.is_valid() is False, form.get_errors()
    assert 'binary_content_here' not in form.__html__()


@pytest.mark.django
def test_mode_full_form_from_request():
    class FooForm(Form):
        foo = Field(required=True)
        bar = Field(required=True)
        baz = Field.boolean(initial=True)

        class Meta:
            @classmethod
            def actions__submit__post_handler(form, **_):
                pass  # pragma: no cover

    # empty POST
    form = FooForm().bind(request=req('post', **{'-submit': ''}))
    assert form.is_valid() is False, form.get_errors()
    assert form._errors == set()
    assert form.fields.foo._errors == {'This field is required'}
    assert form.fields['bar']._errors == {'This field is required'}
    assert form.fields['baz']._errors == set()  # not present in POST request means false

    form = FooForm().bind(
        request=req(
            'post',
            **{
                'foo': 'x',
                'bar': 'y',
                'baz': 'false',
                '-submit': '',
            },
        )
    )
    assert form.is_valid() is True, form.get_errors()
    assert form.fields['baz'].value is False

    # all params in GET
    form = FooForm().bind(request=req('get', **{'-submit': ''}))
    assert form.is_valid() is False, form.get_errors()
    assert form.fields.foo._errors == {'This field is required'}
    assert form.fields['bar']._errors == {'This field is required'}
    assert form.fields['baz']._errors == set()  # not present in POST request means false

    form = FooForm().bind(
        request=req(
            'get',
            **{
                'foo': 'x',
                'bar': 'y',
                'baz': 'on',
                '-submit': '',
            },
        )
    )
    assert not form._errors
    assert not form.fields.foo._errors

    assert form.is_valid() is True, form.get_errors()


def test_mode_initials_from_get():
    class FooForm(Form):
        foo = Field(required=True)
        bar = Field(required=True)
        baz = Field.boolean(initial=True)

    # empty GET
    form = FooForm().bind(request=req('get'))
    assert form.is_valid() is True, form.get_errors()

    # initials from GET
    form = FooForm().bind(request=req('get', foo='foo_initial'))
    assert form.is_valid() is True, form.get_errors()
    assert form.fields.foo.value == 'foo_initial'

    assert form.fields.foo._errors == set()
    assert form.fields['bar']._errors == set()
    assert form.fields['baz']._errors == set()


def test_form_errors_function():
    class MyForm(Form):
        foo = Field(is_valid=lambda **_: (False, 'field error'))

        class Meta:
            def actions__submit__post_handler(form, **_):
                pass  # pragma: no cover

    def post_validation(form, **_):
        form.add_error('global error')

    assert (
        MyForm(
            post_validation=post_validation,
        )
        .bind(
            request=req('post', **{'-submit': '', 'foo': 'asd'}),
        )
        .get_errors()
        == {'global': {'global error'}, 'fields': {'foo': {'field error'}}}
    )


@pytest.mark.django
@pytest.mark.filterwarnings("ignore:Model 'tests.foomodel' was already registered")
def test_null_field_factory():
    from django.db import models

    class ShouldBeNullField(models.Field):
        pass

    class NullFieldFactoryModel(models.Model):
        should_be_null = ShouldBeNullField()
        foo = models.IntegerField()

    register_field_factory(ShouldBeNullField, factory=None)

    form = Form(auto__model=NullFieldFactoryModel).bind(request=req('get'))
    assert list(form.fields.keys()) == ['foo']


@override_settings(DEBUG=True)
@pytest.mark.django_db
@pytest.mark.filterwarnings("ignore:Model 'tests.foomodel' was already registered")
def test_choice_queryset_ajax_attrs_direct():
    from django.contrib.auth.models import User

    User.objects.create(username='foo')
    user2 = User.objects.create(username='bar')

    class MyForm(Form):
        class Meta:
            _name = 'form_name'

        username = Field.choice_queryset(choices=User.objects.all().order_by('username'))
        not_returning_anything = Field.integer()

    form = MyForm()
    form = form.bind(request=req('get'))
    actual = perform_ajax_dispatch(root=form, path='/fields/username/endpoints/choices', value='ar')
    assert actual == {
        'results': [{'id': user2.pk, 'text': smart_str(user2)}],
        'pagination': {'more': False},
        'page': 1,
    }

    with pytest.raises(InvalidEndpointPathException):
        perform_ajax_dispatch(root=form, path='/fields/not_returning_anything', value='ar')


@pytest.mark.django_db
@pytest.mark.filterwarnings("ignore:Model 'tests.foomodel' was already registered")
@pytest.mark.filterwarnings("ignore:Pagination may yield inconsistent results")
def test_choice_queryset_ajax_attrs_foreign_key():
    from django.contrib.auth.models import User
    from django.db import models
    from django.db.models import CASCADE

    class ChoiceQuerySetAjaxAttrsForeignKeyModel(models.Model):
        user = models.ForeignKey(User, on_delete=CASCADE)

    User.objects.create(username='foo')
    user2 = User.objects.create(username='bar')

    form = Form(auto__model=ChoiceQuerySetAjaxAttrsForeignKeyModel).bind(request=req('get'))
    actual = perform_ajax_dispatch(root=form, path='/fields/user/endpoints/choices', value='ar')

    assert actual == {
        'results': [{'id': user2.pk, 'text': smart_str(user2)}],
        'pagination': {'more': False},
        'page': 1,
    }


@pytest.mark.django_db
@pytest.mark.filterwarnings("ignore:Model 'tests.foomodel' was already registered")
@pytest.mark.filterwarnings("ignore:Pagination may yield inconsistent results")
def test_choice_queryset_ajax_one_past_the_end():
    from django.contrib.auth.models import User
    from django.db import models
    from django.db.models import CASCADE

    class ChoiceQuerySetAjaxOnePastTheEndModel(models.Model):
        user = models.ForeignKey(User, on_delete=CASCADE)

    form = Form(auto__model=ChoiceQuerySetAjaxOnePastTheEndModel).bind(request=req('get', page=2))
    actual = perform_ajax_dispatch(root=form, path='/fields/user/endpoints/choices', value='ar')

    assert actual == {
        'results': [],
        'pagination': {'more': False},
        'page': 2,
    }


@override_settings(DEBUG=True)
def test_ajax_namespacing():
    class MyForm(Form):
        foo = Field(
            endpoints__bar__func=lambda **_: 'bar',
            endpoints__baaz__func=lambda **_: 'baaz',
        )

    request = req('get')
    form = MyForm()
    form = form.bind(request=request)
    assert 'bar' == perform_ajax_dispatch(root=form, path='/fields/foo/endpoints/bar', value='ar')
    assert 'baaz' == perform_ajax_dispatch(root=form, path='/fields/foo/endpoints/baaz', value='ar')


@override_settings(DEBUG=True)
def test_ajax_config_and_validate():
    class MyForm(Form):
        foo = Field()
        bar = Field(post_validation=lambda field, **_: field.add_error('FAIL'))

    request = req('get')
    form = MyForm()
    form = form.bind(request=request)
    assert (
        dict(
            name='foo',
        )
        == perform_ajax_dispatch(root=form, path='/fields/foo/endpoints/config', value=None)
    )

    assert dict(valid=True, errors=[]) == perform_ajax_dispatch(
        root=form, path='/fields/foo/endpoints/validate', value='new value'
    )

    assert dict(valid=False, errors=['FAIL']) == perform_ajax_dispatch(
        root=form, path='/fields/bar/endpoints/validate', value='new value'
    )


@override_settings(DEBUG=True)
def test_custom_endpoint():
    class MyForm(Form):
        class Meta:
            endpoints__foo__func = lambda value, **_: 'foo' + value

    form = MyForm()
    form = form.bind(request=None)
    assert 'foobar' == perform_ajax_dispatch(root=form, path='/foo', value='bar')


def test_render_with_action():
    class MyForm(Form):
        bar = Field()

        class Meta:
            def actions__submit__post_handler(**_):
                pass  # pragma: no cover

    expected_html = """
        <form action="" enctype="multipart/form-data" method="post">
            <div>
                <label for="id_bar">
                    Bar
                </label>
                <input id="id_bar" name="bar" type="text" value="">
            </div>
            <div class="links">
                <button accesskey="s" name="-submit">Submit</button>
            </div>
        </form>
    """

    actual_html = remove_csrf(MyForm().bind(request=req('get')).__html__())
    prettified_expected = reindent(BeautifulSoup(expected_html, 'html.parser').prettify()).strip()
    prettified_actual = reindent(BeautifulSoup(actual_html, 'html.parser').prettify()).strip()
    assert prettified_actual == prettified_expected


def test_render_without_actions():
    class MyForm(Form):
        bar = Field()

    expected_html = """
        <form action="" enctype="multipart/form-data" method="post">
            <div>
                <label for="id_bar">
                    Bar
                </label>
                <input id="id_bar" name="bar" type="text" value="">
            </div>
        </form>
    """

    actual_html = remove_csrf(MyForm().bind(request=req('get')).__html__())
    prettified_expected = reindent(BeautifulSoup(expected_html, 'html.parser').prettify()).strip()
    prettified_actual = reindent(BeautifulSoup(actual_html, 'html.parser').prettify()).strip()
    assert prettified_actual == prettified_expected


def test_bool_parse():
    for t in ['1', 'true', 't', 'yes', 'y', 'on']:
        assert bool_parse(t) is True

    for f in ['0', 'false', 'f', 'no', 'n', 'off']:
        assert bool_parse(f) is False


def test_decimal_parse():
    assert decimal_parse(string_value='1') == Decimal(1)

    with pytest.raises(ValidationError) as e:
        decimal_parse(string_value='asdasd')

    assert e.value.messages == ["Invalid literal for Decimal: u'asdasd'"] or e.value.messages == [
        "Invalid literal for Decimal: 'asdasd'"
    ]


def test_url_parse():
    assert url_parse(string_value='https://foo.example') == 'https://foo.example'

    with pytest.raises(ValidationError) as e:
        url_parse(string_value='asdasd')

    assert e.value.messages == ['Enter a valid URL.']


def test_render_temlate_none():
    # noinspection PyTypeChecker
    assert render_template(request=None, template=None, context=None) == ''


def test_render_template_template_object():
    assert (
        render_template(request=req('get'), context=dict(a='1'), template=Template(template_string='foo {{a}} bar'))
        == 'foo 1 bar'
    )


def test_action_render():
    action = Action(display_name='Title', template='test_action_render.html').bind(request=req('get'))
    assert action.__html__().strip() == 'tag=a display_name=Title'


def test_action_submit_render():
    action = Action.submit(display_name='Title').bind(request=req('get'))
    assert action.__html__().strip() == '<button accesskey="s" name="-">Title</button>'


def test_action_repr():
    assert repr(Action(_name='name', template='test_link_render.html')) == '<iommi.action.Action name>'


def test_action_shortcut_icon():
    assert (
        Action.icon('foo', display_name='title').bind(request=None).__html__()
        == '<a><i class="fa fa-foo"></i> title</a>'
    )


def test_include_prevents_read_from_instance():
    class MyForm(Form):
        foo = Field(include=False)

    MyForm(instance=object()).bind(request=req('get'))


def test_choice_post_validation_not_overwritten():
    def my_post_validation(**_):
        raise Exception('foobar')

    class MyForm(Form):
        foo = Field.choice(post_validation=my_post_validation, choices=[1, 2, 3])

    with pytest.raises(Exception) as e:
        MyForm().bind(request=req('get'))

    assert str(e.value) == 'foobar'


def test_choice_post_validation_chains_empty_choice_when_required_false():
    class MyForm(Form):
        foo = Field.choice(required=False, choices=[1, 2, 3])

    form = MyForm().bind(request=req('get'))

    assert list(form.fields.foo.choice_tuples) == [
        form.fields.foo.empty_choice_tuple + (0,),
        (1, '1', '1', False, 1),
        (2, '2', '2', False, 2),
        (3, '3', '3', False, 3),
    ]


def test_instance_set_earlier_than_evaluate_is_called():
    class MyForm(Form):
        foo = Field(initial=lambda form, **_: form.instance)

    MyForm()


@pytest.mark.django_db
def test_auto_field_not_included_by_default():
    from tests.models import Foo

    form = Form(auto__model=Foo).bind(request=req('get'))
    assert 'id' not in form.fields


@pytest.mark.django_db
def test_auto_field_possible_to_show():
    from tests.models import Foo

    form = Form(auto__model=Foo, fields__id__include=True).bind(request=req('get'))
    assert 'id' in form.fields


def test_initial_set_earlier_than_evaluate_is_called():
    class MyForm(Form):
        foo = Field(extra_evaluated__bar=lambda field, **_: field.initial)

    assert 17 == MyForm(instance=Struct(foo=17)).bind(request=req('get')).fields.foo.extra_evaluated.bar


@pytest.mark.django_db
def test_field_from_model_path_minimal():
    from tests.models import Bar

    class FooForm(Form):
        baz = Field.from_model(Bar, 'foo__foo', help_text='another help text')

    assert FooForm().bind(request=req('get', baz='1')).fields.baz.attr == 'foo__foo'


@pytest.mark.django_db
def test_field_from_model_path():
    from tests.models import Bar

    class FooForm(Form):
        baz = Field.from_model(Bar, 'foo__foo', help_text='another help text')

        class Meta:
            model = Bar

    assert FooForm().bind(request=req('get', baz='1')).fields.baz.attr == 'foo__foo'
    assert FooForm().bind(request=req('get', baz='1')).fields.baz._name == 'baz'
    assert FooForm().bind(request=req('get', baz='1')).fields.baz.value == 1
    assert FooForm().bind(request=req('get', baz='1')).fields.baz.help_text == 'another help text'
    assert not FooForm().bind(request=req('get', baz='asd')).is_valid()
    fake = Struct(foo=Struct(foo='1'))
    assert FooForm(instance=fake).bind(request=req('get')).fields.baz.initial == '1'
    assert FooForm(instance=fake).bind(request=req('get')).fields.baz.parse is int_parse


@pytest.mark.django_db
def test_field_from_model_subtype():
    from django.db import models

    class Foo(models.IntegerField):
        pass

    class FromModelSubtype(models.Model):
        foo = Foo()

    result = Field.from_model(model=FromModelSubtype, model_field_name='foo')

    assert result.parse is int_parse


@pytest.mark.django_db
def test_create_members_from_model_path():
    from tests.models import Foo, Bar

    class BarForm(Form):
        class Meta:
            fields__foo_foo__attr = 'foo__foo'

    bar = Bar.objects.create(foo=Foo.objects.create(foo=7))
    form = BarForm(auto__instance=bar).bind(request=req('get'))

    assert form.fields.foo_foo.attr == 'foo__foo'
    assert form.fields.foo_foo._name == 'foo_foo'
    assert form.fields.foo_foo.model_field is Foo._meta.get_field('foo')
    assert form.fields.foo_foo.help_text == 'foo_help_text'


@pytest.mark.django
def test_namespaces_do_not_call_in_templates():
    from django.template import RequestContext

    def raise_always():
        assert False  # pragma: no cover as the test is that this doesn't fire!

    assert Template('{{ foo }}').render(RequestContext(None, dict(foo=Namespace(call_target=raise_always))))


@pytest.mark.django
def test_choice_queryset_error_message_for_automatic_model_extraction():
    with pytest.raises(AssertionError) as e:
        Field.choice_queryset(choices=[])

    assert (
        str(e.value)
        == 'The convenience feature to automatically get the parameter model set only works for QuerySet instances or if you specify model_field'
    )


def test_datetime_parse():
    assert datetime_parse('2001-02-03 12') == datetime(2001, 2, 3, 12)

    with freeze_time('2001-02-03 12:13:14'):
        assert datetime_parse('now') == datetime(2001, 2, 3, 12, 13, 14)

    with freeze_time('2001-02-03 12:13:14'):
        assert datetime_parse('-2d') == datetime(2001, 2, 1, 12, 13, 14)

    bad_date = '091223'
    with pytest.raises(ValidationError) as e:
        datetime_parse(bad_date)

    formats = ', '.join('"%s"' % x for x in datetime_iso_formats)
    expected = f'Time data "{bad_date}" does not match any of the formats "now", {formats}, and is not a relative date like "2d" or "2 weeks ago"'
    actual = e.value.message
    assert actual == expected


@pytest.mark.django_db
def test_from_model_with_inheritance():
    from tests.models import FromModelWithInheritanceTest

    was_called = defaultdict(int)

    class MyField(Field):
        @classmethod
        @class_shortcut
        def float(cls, call_target=None, **kwargs):
            was_called['MyField.float'] += 1
            return call_target(**kwargs)

    class MyForm(Form):
        class Meta:
            member_class = MyField

    MyForm(auto__model=FromModelWithInheritanceTest,).bind(
        request=req('get'),
    )

    assert was_called == {
        'MyField.float': 2,
    }


@pytest.mark.django_db
def test_from_model_override_field():
    from tests.models import FormFromModelTest

    form = Form(auto__model=FormFromModelTest, fields__f_float=Field(_name='f_float'),).bind(
        request=req('get'),
    )
    assert form.fields.f_float.parse is not float_parse


def test_field_merge():
    form = Form(fields__foo={}, instance=Struct(foo=1),).bind(
        request=req('get'),
    )
    assert len(form.fields) == 1
    assert form.fields.foo._name == 'foo'
    assert form.fields.foo.value == 1


def test_override_doesnt_stick():
    class MyForm(Form):
        foo = Field()

    form = MyForm(fields__foo__include=False).bind(request=req('get'))
    assert len(form.fields) == 0

    form2 = MyForm().bind(request=req('get'))
    assert len(form2.fields) == 1


def test_override_shenanigans():
    class MyForm(Form):
        foo = Field()

    form = MyForm(fields__foo=Field.integer()).bind(request=req('get'))
    assert form.fields.foo.parse is int_parse

    form = MyForm(fields__foo__extra__hello=True).bind(request=req('get'))
    assert form.fields.foo.extra.hello is True


def test_dunder_name_for_column():
    class FooForm(Form):
        class Meta:
            model = Bar

        foo = Field()
        foo__a = Field()

    with pytest.deprecated_call():
        form = FooForm()
        form = form.bind(request=None)

    assert list(form.fields.keys()) == ['foo', 'foo__a']


def test_help_text_for_boolean_tristate():
    form = Form(auto__model=BooleanFromModelTestModel)
    form = form.bind(request=req('get'))
    assert '$$$$' in str(form)


def test_boolean_tristate_none_parse():
    assert boolean_tristate__parse(string_value='') is None


@pytest.mark.django_db
def test_all_field_shortcuts():
    class MyFancyField(Field):
        class Meta:
            extra__fancy = True

    class MyFancyForm(Form):
        class Meta:
            member_class = MyFancyField

    all_shortcut_names = keys(
        get_members(
            cls=MyFancyField,
            member_class=Shortcut,
            is_member=is_shortcut,
        )
    )

    config = {f'fields__field_of_type_{t}__call_target__attribute': t for t in all_shortcut_names}

    type_specifics = Namespace(
        fields__field_of_type_choice__choices=[],
        fields__field_of_type_multi_choice__choices=[],
        fields__field_of_type_radio__choices=[],
        fields__field_of_type_choice_queryset__choices=TFoo.objects.none(),
        fields__field_of_type_multi_choice_queryset__choices=TFoo.objects.none(),
        fields__field_of_type_many_to_many__model_field=TBaz.foo.field,
        fields__field_of_type_foreign_key__model_field=TBar.foo.field,
        fields__field_of_type_foreign_key__model=TBar,
        fields__field_of_type_info__value='dummy information',
    )

    form = MyFancyForm(**config, **type_specifics).bind(request=req('get'))

    for name, field in items(form.fields):
        assert field.extra.get('fancy'), name


def test_shortcut_to_subclass():
    class MyField(Field):
        @classmethod
        @class_shortcut
        def my_shortcut(cls, call_target=None, **kwargs):
            return call_target(
                **kwargs
            )  # pragma: no cover: we aren't testing that this shortcut is implemented correctly

    assert isinstance(MyField.my_shortcut(), MyField)

    class MyField(Field):
        @classmethod
        @class_shortcut
        def choices(cls, call_target=None, **kwargs):
            return call_target(
                **kwargs
            )  # pragma: no cover: we aren't testing that this shortcut is implemented correctly

    field = MyField.choice(choices=[])
    assert isinstance(field, MyField)
    assert field.empty_label == '---'


def test_multi_choice_choice_tuples():
    class MyForm(Form):
        foo = Field.multi_choice(
            choices=list('abc'),
            initial=list('b'),
        )

    assert MyForm().bind().fields.foo.choice_tuples == [
        ('a', 'a', 'a', False, 1),
        ('b', 'b', 'b', True, 2),
        ('c', 'c', 'c', False, 3),
    ]


def test_multi_choice_choice_tuples_empty_initial():
    class MyForm(Form):
        foo = Field.multi_choice(
            choices=list('abc'),
            initial=[],
        )

    assert MyForm().bind().fields.foo.choice_tuples == [
        ('a', 'a', 'a', False, 1),
        ('b', 'b', 'b', False, 2),
        ('c', 'c', 'c', False, 3),
    ]


def test_form_h_tag():
    assert '<h1>$$$</h1>' in Form(title='$$$').bind(request=req('get')).__html__()
    assert '<b>$$$</b>' in Form(title='$$$', h_tag__tag='b').bind(request=req('get')).__html__()
    assert '<b>$$$</b>' in Form(h_tag=html.b('$$$')).bind(request=req('get')).__html__()


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_render_create_object():
    form = Form.create(auto__model=CreateOrEditObjectTest,).bind(
        request=req('get'),
    )
    response = form.__html__(render__call_target=lambda **kwargs: kwargs)
    assert response['context']['csrf_token']

    form = Form.create(
        auto__model=CreateOrEditObjectTest,
        fields__f_int__initial=1,
        fields__f_float__initial=lambda form, field, **_: 2,
        template='<template name>',
    ).bind(
        request=req('get'),
    )
    response = form.__html__(
        render__context={'foo': 'FOO'},
        render__foobarbaz='render__foobarbaz',
        render__call_target=lambda **kwargs: kwargs,
    )

    assert form.extra.is_create is True
    assert response['context']['foo'] == 'FOO'
    assert response['context']['csrf_token']
    assert response['foobarbaz'] == 'render__foobarbaz'
    assert response['template'] == '<template name>'
    assert form.mode is INITIALS_FROM_GET
    assert form.fields['f_int'].initial == 1
    assert form.fields['f_int']._errors == set()
    assert form.fields['f_int'].value == 1
    assert form.fields['f_float'].initial == 2
    assert form.fields['f_float'].value == 2
    assert form.fields['f_bool'].value is None
    assert set(form.fields.keys()) == {'f_int', 'f_float', 'f_bool', 'f_foreign_key', 'f_many_to_many'}


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_create_object():
    a_foo = Foo.objects.create(foo=7)
    form = Form.create(
        auto__model=CreateOrEditObjectTest,
    )

    target_marker = form.bind(
        request=req('get'),
    ).actions.submit.own_target_marker()

    form = form.bind(
        request=req(
            'post',
            **{
                'f_int': '3',
                'f_float': '5.1',
                'f_bool': 'True',
                'f_foreign_key': str(a_foo.pk),
                'f_many_to_many': [str(a_foo.pk)],
                target_marker: '',
            },
        ),
    )
    response = form.render_to_response()
    assert form._request_data
    instance = CreateOrEditObjectTest.objects.get()
    assert instance is not None
    assert instance.f_int == 3
    assert instance.f_float == 5.1
    assert instance.f_bool is True
    assert response.status_code == 302
    assert response['Location'] == '../'


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_create_object_callbacks():
    a_foo = Foo.objects.create(foo=7)
    invoked = []

    def pre_save_all_but_related_fields(**_):
        invoked.append('pre_save_all_but_related_fields')

    def on_save_all_but_related_fields(**_):
        invoked.append('on_save_all_but_related_fields')

    def pre_save(**_):
        invoked.append('pre_save')

    def on_save(form, instance, **_):
        # validate that the arguments are what we expect
        assert form.instance is instance
        assert isinstance(instance, CreateOrEditObjectTest)
        assert instance.pk is not None
        invoked.append('on_save')

    def new_instance(form, **_):
        invoked.append('new_instance')
        return form.model(f_bool=True)

    form = Form.create(
        auto__model=CreateOrEditObjectTest,
        auto__exclude=['f_bool'],
        extra__pre_save_all_but_related_fields=pre_save_all_but_related_fields,
        extra__on_save_all_but_related_fields=on_save_all_but_related_fields,
        extra__pre_save=pre_save,
        extra__on_save=on_save,
        extra__new_instance=new_instance,
    )

    target_marker = form.bind(
        request=req('get'),
    ).actions.submit.own_target_marker()

    form.bind(
        request=req(
            'post',
            **{
                'f_int': '3',
                'f_float': '5.1',
                'f_foreign_key': str(a_foo.pk),
                'f_many_to_many': [str(a_foo.pk)],
                target_marker: '',
            },
        ),
    ).render_to_response()

    instance = CreateOrEditObjectTest.objects.get()
    assert instance is not None
    assert instance.f_bool is True

    assert invoked == [
        'new_instance',
        'pre_save_all_but_related_fields',
        'on_save_all_but_related_fields',
        'pre_save',
        'on_save',
    ]


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_edit_object():
    a_foo = Foo.objects.create(foo=7)
    instance = CreateOrEditObjectTest.objects.create(f_int=3, f_float=5.1, f_bool=True, f_foreign_key=a_foo)
    instance.save()

    request = req('get')
    form = Form.edit(
        auto__instance=instance,
    )
    form = form.bind(request=request)
    response = form.__html__(
        render=lambda **kwargs: kwargs,
    )
    assert form.get_errors() == {}
    assert form.fields['f_int'].value == 3
    assert form.fields['f_float'].value == 5.1
    assert form.fields['f_bool'].value is True
    assert response['context']['csrf_token']

    request = req(
        'POST',
        **{
            'f_int': '7',
            'f_float': '11.2',
            'f_foreign_key': str(a_foo.pk),
            'f_many_to_many': [],
            '-submit': '',
            # Not sending a parameter in a POST is the same thing as false
        },
    )
    form = Form.edit(
        auto__instance=instance,
    )
    form = form.bind(request=request)
    assert form.mode == FULL_FORM_FROM_REQUEST
    response = form.render_to_response()
    assert form.is_valid(), form.get_errors()
    assert response.status_code == 302

    assert response['Location'] == '../../'

    instance.refresh_from_db()
    assert instance is not None
    assert instance.f_int == 7
    assert instance.f_float == 11.2
    assert not instance.f_bool

    # edit again, to check redirect
    form = Form.edit(
        auto__instance=instance,
    )
    form = form.bind(request=request)
    response = form.render_to_response()
    assert response.status_code == 302
    assert response['Location'] == '../../'


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_edit_object_foreign_related_attribute():
    from tests.models import CreateOrEditObjectTest, Foo

    instance = CreateOrEditObjectTest.objects.create(
        f_foreign_key=Foo.objects.create(
            foo=17,
        ),
        f_int=0,
        f_float=0.0,
        f_bool=False,
    )

    request = req('get')
    form = Form.edit(auto__instance=instance, auto__include=['f_foreign_key__foo'])

    form = form.bind(request=request)
    response = form.__html__(
        render=lambda **kwargs: kwargs,
    )
    assert form.get_errors() == {}
    assert form.fields['f_foreign_key_foo'].value == 17
    assert response['context']['csrf_token']

    request = req(
        'POST',
        **{
            'f_foreign_key_foo': str(42),
            '-submit': '',
        },
    )
    form = Form.edit(auto__instance=instance, auto__include=['f_foreign_key__foo'])
    form = form.bind(request=request)
    assert form.mode == FULL_FORM_FROM_REQUEST
    response = form.render_to_response()
    assert response.status_code == 302

    assert response['Location'] == '../../'

    instance.refresh_from_db()
    assert instance is not None
    assert instance.f_foreign_key.foo == 42


def test_redirect_default_case():
    sentinel1, sentinel2, sentinel3, sentinel4 = object(), object(), object(), object()
    expected = dict(redirect_to=sentinel2, request=sentinel3, form=sentinel4)
    assert (
        create_or_edit_object_redirect(**merged(expected, is_create=sentinel1, redirect=lambda **kwargs: kwargs))
        == expected
    )


@pytest.mark.django_db
def test_unique_constraint_violation():
    from tests.models import UniqueConstraintTest

    request = req(
        'post',
        **{
            'f_int': '3',
            'f_float': '5.1',
            'f_bool': 'True',
            '-submit': '',
        },
    )
    Form.create(auto__model=UniqueConstraintTest).bind(request=request).render_to_response()
    assert UniqueConstraintTest.objects.all().count() == 1

    form = Form.create(
        auto__model=UniqueConstraintTest,
    ).bind(request=request)
    form.render_to_response()

    assert form.is_valid() is False
    assert form.get_errors() == {
        'global': {'Unique constraint test with this F int, F float and F bool already exists.'}
    }
    assert UniqueConstraintTest.objects.all().count() == 1


@pytest.mark.django_db
@pytest.mark.filterwarnings("ignore:Pagination may yield inconsistent results with an unordered")
@override_settings(DEBUG=True)
def test_create_or_edit_object_dispatch():
    from tests.models import Bar, Foo

    f1 = Foo.objects.create(foo=1)
    f2 = Foo.objects.create(foo=2)
    request = req('get', **{DISPATCH_PATH_SEPARATOR + 'choices': ''})

    response = (
        Form.create(
            auto__model=Bar,
            template='<template name>',
        )
        .bind(request=request)
        .render_to_response()
    )
    assert json.loads(response.content) == {
        'results': [
            {"text": str(f1), "id": f1.pk},
            {"text": str(f2), "id": f2.pk},
        ],
        'pagination': {'more': False},
        'page': 1,
    }


@pytest.mark.django_db
def test_create_or_edit_object_validate_unique():
    from tests.models import Baz

    request = req(
        'post',
        **{
            'a': '1',
            'b': '1',
            '-submit': '',
        },
    )

    response = Form.create(auto__model=Baz).bind(request=request).render_to_response()
    assert response.status_code == 302
    assert Baz.objects.filter(a=1, b=1).exists()

    response = Form.create(auto__model=Baz).bind(request=request).render_to_response()
    assert response.status_code == 200
    assert 'Baz with this A and B already exists.' in response.content.decode('utf-8')

    request = req(
        'post',
        **{
            'a': '1',
            'b': '2',  # <-- changed from 1
            '-submit': '',
        },
    )
    response = Form.create(auto__model=Baz).bind(request=request).render_to_response()
    assert response.status_code == 302
    instance = Baz.objects.get(a=1, b=2)

    request = req(
        'post',
        **{
            'a': '1',
            'b': '1',  # <-- 1 again
            '-submit': '',
        },
    )

    response = Form.edit(auto__instance=instance).bind(request=request).render_to_response()
    assert response.status_code == 200
    assert 'Baz with this A and B already exists.' in response.content.decode('utf-8')


@pytest.mark.django_db
def test_create_or_edit_object_full_template_1():
    from tests.models import Foo

    request = req('get')

    response = Form.create(auto__model=Foo).bind(request=request).render_to_response()
    assert response.status_code == 200

    expected_html = """
<!DOCTYPE html>
<html>
    <head>
        <title>
            Create foo
        </title>
    </head>
    <body>
        <form action="" enctype="multipart/form-data" method="post">
            <h1>
                Create foo
            </h1>
            <div>
                <label for="id_foo">
                    Foo
                </label>
                <input id="id_foo" name="foo" type="text" value=""/>
                <div class="helptext">
                    foo_help_text
                </div>
            </div>
            <div class="links">
                <button accesskey="s" name="-submit">Create</button>
            </div>
        </form>
    </body>
</html>

    """
    actual = prettify(remove_csrf(response.content.decode()))
    expected = prettify(expected_html)
    assert actual == expected


def test_create_or_edit_view_name():
    from tests.models import Foo

    class MyForm(Form):
        pass

    assert MyForm(auto__model=Foo).as_view().__name__ == "MyForm.as_view"


@pytest.mark.django_db
def test_create_or_edit_object_full_template_2():
    from tests.models import Foo

    foo = Foo.objects.create(foo=7)
    Form.delete(auto__instance=foo).bind(request=req('post', **{'-submit': ''})).render_to_response()
    with pytest.raises(Foo.DoesNotExist):
        foo.refresh_from_db()


@pytest.mark.django_db
def test_evil_names():
    from tests.models import EvilNames

    Form.create(auto__model=EvilNames).bind(request=req('post'))


def test_time_parse():
    with freeze_time('2012-03-07 12:13:14'):
        assert time_parse('now') == time(12, 13, 14)


@pytest.mark.parametrize(
    'attributes, result',
    [
        (['foo', 'bar'], ['']),
        (['foo', 'bar__boink'], ['', 'bar']),
        (['foo', 'bar__boink__bink'], ['', 'bar', 'bar__boink']),
        (['foo', 'bar__boink__bink'], ['', 'bar', 'bar__boink']),
        (['foo__hej', 'foo__hopp', 'bar__bink', 'bar__boink'], ['bar', 'foo']),
        (['fisk', 'foo__hej', 'foo__hopp', 'bar__bink', 'bar__boink'], ['', 'bar', 'foo']),
    ],
)
def test_find_prefixes(attributes, result):
    assert find_unique_prefixes(attributes) == result


@pytest.mark.django_db
def test_choices_in_char_field_model():
    form = Form.edit(auto__model=ChoicesModel).bind(request=req('get'))
    assert form.fields.color.choices == [x[0] for x in ChoicesModel.CHOICES]

    value, display_name = ChoicesModel.CHOICES[0]
    assert (
        form.fields.color.choice_display_name_formatter(value, **form.fields.color.iommi_evaluate_parameters())
        == display_name
    )


def test_date_parse():
    with pytest.raises(ValidationError) as e:
        date_parse(string_value='2020-01-60')

    assert (
        str(e.value.args[0])
        == 'Time data "2020-01-60" does not match any of the formats "now", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H", and is not a relative date like "2d" or "2 weeks ago" (out of range)'
    )

    with pytest.raises(ValidationError) as e:
        date_parse(string_value='2020-01-031')

    assert (
        str(e.value.args[0])
        == 'Time data "2020-01-031" does not match any of the formats "now", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H", and is not a relative date like "2d" or "2 weeks ago" (out of range)'
    )

    assert date_parse('2020-01-02') == date(2020, 1, 2)
    assert date_parse('today') == date.today()


def test_grouped_choices():
    f = Form(
        fields__foo=Field.choice(
            choices=[1, 2, 3, 4, 5],
            choice_to_optgroup=lambda choice, **_: 'a' if choice < 3 else 'b',
        )
    ).bind(request=req('get'))
    assert f.fields.foo.grouped_choice_tuples == [
        (None, []),
        ('a', [(1, '1', '1', False, 1), (2, '2', '2', False, 2)]),
        ('b', [(3, '3', '3', False, 3), (4, '4', '4', False, 4), (5, '5', '5', False, 5)]),
    ]


def test_nested_form():
    class InnerForm(Form):
        inner_field = Field()

    class OuterForm(Form):
        outer_field = Field()
        inner_form = InnerForm()

    instance = Struct(outer_field='a', inner_form=Struct(inner_field='b'))

    f = OuterForm(instance=instance).bind(request=req('get'))

    applied_instance = Struct(inner_form=Struct())
    f.apply(applied_instance)
    assert instance == applied_instance

    assert f.parts.inner_form.parent_form is f
    (inner_form,) = values(f.nested_forms)
    assert inner_form is f.parts.inner_form
    assert inner_form.form_tag != 'form'


def test_nested_form_attr_empty_path():
    class InnerForm(Form):
        inner_field = Field()

    class OuterForm(Form):
        outer_field = Field()
        inner_form = InnerForm(attr='')

    instance = Struct(outer_field='a', inner_field='b')

    f = OuterForm(instance=instance).bind(request=req('get'))

    applied_instance = Struct()
    f.apply(applied_instance)
    assert instance == applied_instance


def test_nested_form_validation_error_propagates_to_parent():
    class InnerForm(Form):
        inner_field = Field(is_valid=lambda **_: (False, 'nope'))

    class OuterForm(Form):
        outer_field = Field()
        inner_form = InnerForm(attr='')

    instance = Struct(outer_field='a', inner_field='b')

    f = OuterForm(instance=instance).bind(request=req('get', inner_field='foo'))

    assert not f.nested_forms.inner_form.is_valid()
    assert not f.is_valid()
    assert f.nested_forms.inner_form.get_errors() == {'fields': {'inner_field': {'nope'}}}
    assert f.get_errors() == {}


def test_filter_model_mixup():
    f = Form(auto__model=TBar).bind(request=req('get'))
    assert f.fields.foo.model == TFoo


def test_initial_is_set_to_default_of_model():
    form = Form.create(auto__model=DefaultsInForms).bind(request=req('get'))
    assert form.fields.name.initial == '<name>'
    assert form.fields.number.initial == 7


@pytest.mark.skip('currently broken')
def test_shoot_config_into_auto_dunder_field():
    Form(
        auto__model=FieldFromModelOneToOneTest,
        # attr `foo_one_to_one__foo` creates a field named `foo_one_to_one_foo`. Note that the `__` is collapsed to one `_`!
        auto__include=['foo_one_to_one__foo'],
        fields__foo_one_to_one_foo__display_name='bar',
    ).bind(request=req('get'))


@pytest.mark.django_db
def test_instance_available_in_evaluate_parameters():
    x = Foo.objects.create(foo=42)
    f = Form(
        instance=lambda **_: x,
        title=lambda instance, **_: f'title: {instance.foo}',
    ).bind()
    assert f.title == 'title: 42'


@pytest.mark.django_db
def test_editable_can_be_a_callable():
    x = Foo.objects.create(foo=7)
    f = Form(auto__instance=x, editable=lambda instance, **_: instance.foo == 7).bind()
    assert f.fields.foo.editable is True

    x.foo = 3
    x.save()
    f = Form(auto__instance=x, editable=lambda instance, **_: instance.foo == 7).bind()
    assert f.fields.foo.editable is False
