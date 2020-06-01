import re
from collections import defaultdict
from datetime import (
    date,
    datetime,
    time,
    timedelta,
)
from decimal import Decimal
from io import (
    BytesIO,
    StringIO,
)

import pytest
from bs4 import BeautifulSoup
from django.db.models import Q
from django.test import override_settings
from tri_declarative import (
    class_shortcut,
    get_members,
    getattr_path,
    is_shortcut,
    Namespace,
    setattr_path,
    Shortcut,
)
from tri_struct import Struct

from iommi import Action
from iommi._db_compat import field_defaults_factory
from iommi._web_compat import (
    smart_str,
    Template,
    ValidationError,
)
from iommi.attrs import render_attrs
from iommi.endpoint import (
    InvalidEndpointPathException,
    perform_ajax_dispatch,
)
from iommi.form import (
    bool_parse,
    datetime_iso_formats,
    datetime_parse,
    decimal_parse,
    Field,
    float_parse,
    Form,
    FULL_FORM_FROM_REQUEST,
    INITIALS_FROM_GET,
    int_parse,
    register_field_factory,
    render_template,
    url_parse,
    multi_choice_choice_to_option,
)
from iommi.from_model import (
    member_from_model,
)
from iommi.page import (
    Page,
    html,
)
from iommi.traversable import declared_members
from .compat import RequestFactory
from .helpers import (
    get_attrs,
    prettify,
    reindent,
    req,
)
from .models import (
    Bar,
    BooleanFromModelTestModel,
    TBar,
    TBaz,
    TFoo,
)


def assert_one_error_and_matches_reg_exp(errors, reg_exp):
    error = list(errors)[0]
    assert len(errors) == 1
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
                parsed_data.startswith(form.fields['party'].parsed_data.lower() + '_') if parsed_data is not None else None,
                'Username must begin with "%s_"' % form.fields['party'].parsed_data)
        )
        joined = Field.datetime(attr='contact__joined')
        a_date = Field.date()
        a_time = Field.time()
        staff = Field.boolean()
        admin = Field.boolean()
        manages = Field.multi_choice(choices=['DEF', 'KTH', 'LIU'], required=False)
        not_editable = Field.text(initial='Some non-editable text', editable=False)
        multi_choice_field = Field.multi_choice(choices=['a', 'b', 'c', 'd'], required=False)
    return MyTestForm


def test_field_repr():
    assert repr(Field(_name='foo')) == "<iommi.form.Field foo>"
    assert repr(Form(fields__foo=Field()).bind(request=None).fields.foo) == "<iommi.form.Field foo (bound) path:'foo' members:['endpoints']>"


def test_required_choice():
    class Required(Form):
        c = Field.choice(choices=[1, 2, 3])

    form = Required().bind(request=req('post', **{'-submit': ''}))

    assert form.mode == FULL_FORM_FROM_REQUEST

    assert form.is_target()
    assert form.is_valid() is False
    assert form.fields['c'].errors == {'This field is required'}

    class NotRequired(Form):
        c = Field.choice(choices=[1, 2, 3], required=False)

    form = NotRequired().bind(request=req('post', **{'-submit': '', 'c': ''}))
    assert form.is_target()
    assert form.is_valid()
    assert form.fields['c'].errors == set()


def test_required(MyTestForm):
    form = MyTestForm().bind(request=req('post', **{'-submit': ''}))
    assert form.is_target()
    assert form.is_valid() is False
    assert form.fields['a_date'].value is None
    assert form.fields['a_date'].errors == {'This field is required'}


def test_required_with_falsy_option():
    class MyForm(Form):
        foo = Field.choice(
            choices=[0, 1],
            parse=lambda string_value, **_: int(string_value)
        )
    form = MyForm().bind(request=req('post', **{'foo': '0', '-submit': ''}))
    assert form.fields.foo.value == 0
    assert form.fields.foo.errors == set()


def test_custom_raw_data():
    def my_form_raw_data(**_):
        return 'this is custom raw data'

    class MyForm(Form):
        foo = Field(raw_data=my_form_raw_data)

    form = MyForm().bind(request=req('post', **{'-submit': ''}))
    assert form.fields.foo.value == 'this is custom raw data'


def test_custom_raw_data_list():
    # This is useful for example when doing file upload. In that case the data is on request.FILES, not request.POST so we can use this to grab it from there

    def my_form_raw_data_list(**_):
        return ['this is custom raw data list']

    class MyForm(Form):
        foo = Field(
            raw_data_list=my_form_raw_data_list,
            is_list=True,
        )

    form = MyForm().bind(request=req('post', **{'-': ''}))
    assert form.fields.foo.value == ['this is custom raw data list']


def test_custom_parsed_value():
    def my_form_parsed_data(**_):
        return 'this is custom parsed data'

    class MyForm(Form):
        foo = Field(parsed_data=my_form_parsed_data)

    form = MyForm().bind(request=req('post', **{'-submit': ''}))
    assert form.fields.foo.value == 'this is custom parsed data'


def test_parse(MyTestForm):
    # The spaces in the data are there to check that we strip input
    form = MyTestForm().bind(
        request=req('post', **{
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
        }),
    )

    assert [x.errors for x in form.fields.values()] == [set() for _ in form.fields.keys()]
    assert form.is_valid() is True
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

    assert form.fields['manages'].raw_data_list == ['DEF', 'KTH']
    assert form.fields['manages'].parsed_data == ['DEF', 'KTH']
    assert form.fields['manages'].value == ['DEF', 'KTH']

    assert form.fields['a_date'].raw_data == '2014-02-12'
    assert form.fields['a_date'].parsed_data == date(2014, 2, 12)
    assert form.fields['a_date'].value == date(2014, 2, 12)

    assert form.fields['a_time'].raw_data == '01:02:03'
    assert form.fields['a_time'].parsed_data == time(1, 2, 3)
    assert form.fields['a_time'].value == time(1, 2, 3)

    assert form.fields['multi_choice_field'].raw_data_list == ['a', 'b']
    assert form.fields['multi_choice_field'].parsed_data == ['a', 'b']
    assert form.fields['multi_choice_field'].value == ['a', 'b']
    assert form.fields['multi_choice_field'].is_list
    assert not form.fields['multi_choice_field'].errors
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
    form = MyTestForm(
        post_validation=post_validation,
    ).bind(
        request=req('get', **dict(
            party='foo',
            username='bar_foo',
            joined='foo',
            staff='foo',
            admin='foo',
            a_date='fooasd',
            a_time='asdasd',
            multi_choice_field=['q'],
            **{'-submit': ''}
        )),
    )

    assert form.mode == FULL_FORM_FROM_REQUEST
    assert form.is_valid() is False

    assert form.errors == {'General snafu'}

    assert form.fields['party'].parsed_data == 'foo'
    assert form.fields['party'].errors == {'foo not in available choices'}
    assert form.fields['party'].value is None

    assert form.fields['username'].parsed_data == 'bar_foo'
    assert form.fields['username'].errors == {'Username must begin with "foo_"'}
    assert form.fields['username'].value is None

    assert form.fields['joined'].raw_data == 'foo'
    assert_one_error_and_matches_reg_exp(form.fields['joined'].errors, 'Time data "foo" does not match any of the formats .*')
    assert form.fields['joined'].parsed_data is None
    assert form.fields['joined'].value is None

    assert form.fields['staff'].raw_data == 'foo'
    assert form.fields['staff'].parsed_data is None
    assert form.fields['staff'].value is None

    assert form.fields['admin'].raw_data == 'foo'
    assert form.fields['admin'].parsed_data is None
    assert form.fields['admin'].value is None

    assert form.fields['a_date'].raw_data == 'fooasd'
    assert_one_error_and_matches_reg_exp(form.fields['a_date'].errors, "time data u?'fooasd' does not match format u?'%Y-%m-%d'")
    assert form.fields['a_date'].parsed_data is None
    assert form.fields['a_date'].value is None
    assert form.fields['a_date'].rendered_value == form.fields['a_date'].raw_data

    assert form.fields['a_time'].raw_data == 'asdasd'
    assert_one_error_and_matches_reg_exp(form.fields['a_time'].errors, "time data u?'asdasd' does not match format u?'%H:%M:%S'")
    assert form.fields['a_time'].parsed_data is None
    assert form.fields['a_time'].value is None

    assert form.fields['multi_choice_field'].raw_data_list == ['q']
    assert_one_error_and_matches_reg_exp(form.fields['multi_choice_field'].errors, "q not in available choices")
    assert form.fields['multi_choice_field'].parsed_data == ['q']
    assert form.fields['multi_choice_field'].value is None

    with pytest.raises(AssertionError):
        form.apply(Struct())


def test_initial_from_instance():
    assert Form(
        instance=Struct(a=Struct(b=7)),
        fields__foo=Field(attr='a__b'),
    ).bind(
        request=req('get'),
    ).fields.foo.initial == 7


def test_initial_from_instance_override():
    assert Form(
        instance=Struct(a=Struct(b=7)),
        fields__foo=Field(attr='a__b', initial=11),
    ).bind(
        request=req('get'),
    ).fields.foo.initial == 11


def test_initial_from_instance_is_list():
    assert Form(
        instance=Struct(a=Struct(b=[7])),
        fields__foo=Field(attr='a__b', is_list=True),
    ).bind(
        request=req('get'),
    ).fields.foo.initial == [7]


def test_non_editable_from_initial():
    class MyForm(Form):
        foo = Field(editable=False, initial=':bar:')

    assert ':bar:' in MyForm().bind(request=req('get')).__html__()
    assert ':bar:' in MyForm().bind(request=req('post', **{'-': ''})).__html__()


def test_apply():
    form = Form(
        fields__foo=Field(initial=17, editable=False),
    ).bind(
        request=req('get'),
    )
    assert Struct(foo=17) == form.apply(Struct())


def test_include():
    assert list(Form(fields__foo=Field(include=True)).bind(request=req('get')).fields.keys()) == ['foo']
    assert list(Form(fields__foo=Field(include=False)).bind(request=req('get')).fields.keys()) == []
    assert list(Form(fields__foo=Field(include=lambda form, field, **_: False)).bind(request=req('get')).fields.keys()) == []


def test_declared_fields():
    form = Form(
        fields=dict(
            foo=Field(include=True),
            bar=Field(include=False),
        ),
    ).bind(
        request=req('get'),
    )
    assert list(declared_members(form).fields.keys()) == ['foo', 'bar']
    assert list(form.fields.keys()) == ['foo']


def test_non_editable():
    actual = prettify(Form(
        fields__foo=Field(editable=False, input__attrs__custom=7, initial='11'),
    ).bind(
        request=req('get'),
    ).fields.foo.__html__())

    expected = prettify("""
        <div>
            <label for="id_foo">Foo</label>
            <span custom="7" id="id_foo" name="foo">11</span>
            <div class="helptext"></div>
        </div>
    """)

    assert actual == expected


def test_editable():
    actual = prettify(Form(
        fields__foo=Field(input__attrs__custom=7, initial='11'),
    ).bind(
        request=req('get'),
    ).fields.foo.__html__())

    expected = prettify("""
        <div>
            <label for="id_foo">Foo</label>
            <input custom="7" id="id_foo" name="foo" type="text" value="11"/>
            <div class="helptext"></div>
        </div>
    """)

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
    assert Form(fields__foo=Field.integer(),).bind(request=req('get', foo=' 7  ')).fields.foo.parsed_data == 7

    actual_errors = Form(fields__foo=Field.integer()).bind(request=req('get', foo=' foo  ')).fields.foo.errors
    assert_one_error_and_matches_reg_exp(actual_errors, r"invalid literal for int\(\) with base 10: u?'foo'")


def test_float_field():
    assert Form(fields__foo=Field.float()).bind(request=req('get', foo=' 7.3  ')).fields.foo.parsed_data == 7.3
    assert Form(fields__foo=Field.float()).bind(request=req('get', foo=' foo  ')).fields.foo.errors == {"could not convert string to float: foo"}


def test_email_field():
    assert Form(fields__foo=Field.email()).bind(request=req('get', foo=' 5  ')).fields.foo.errors == {u'Enter a valid email address.'}
    assert Form(fields__foo=Field.email()).bind(request=req('get', foo='foo@example.com')).is_valid()


def test_phone_field():
    assert Form(fields__foo=Field.phone_number()).bind(request=req('get', foo=' asdasd  ')).fields.foo.errors == {u'Please use format +<country code> (XX) XX XX. Example of US number: +1 (212) 123 4567 or +1 212 123 4567'}
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
    assert str(Form(fields__foo=Field(attrs={'foo': '1'})).bind(request=req('get', foo='7')).fields.foo.attrs) == ' foo="1"'
    assert str(Form(fields__foo=Field()).bind(request=req('get', foo='7')).fields.foo.attrs) == ''
    assert render_attrs(dict(foo='"foo"')) == ' foo="&quot;foo&quot;"'


def test_render_attrs_new_style():
    assert str(Form(fields__foo=Field(_name='foo', attrs__foo='1')).bind(request=req('get', foo='7')).fields.foo.attrs) == ' foo="1"'
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
    assert Form(
        fields__foo=Field.multi_choice(_name='foo', choices=['a', 'b']),
    ).bind(
        request=req('get', foo=['a'])
    ).fields.foo.value == ['a']


def test_render_misc_attributes():
    class MyForm(Form):
        foo = Field(
            attrs__class=dict(**{'@@@@21@@@@': True}),
            input__attrs__class=dict(**{'###5###': True}),
            label__attrs__class=dict(**{'$$$11$$$': True}),
            help_text='^^^13^^^',
            display_name='***17***',
            attrs__id='$$$$5$$$$$'
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


def test_info():
    form = Form(fields__foo=Field.info(value='#foo#')).bind(request=req('get'))
    assert form.is_valid() is True
    assert '#foo#' in form.__html__()


def test_radio():
    choices = [
        'a',
        'b',
        'c',
    ]
    req('get')
    form = Form(
        fields__foo=Field.radio(choices=choices),
    ).bind(
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
    form = Form(
        fields__foo=Field.radio(choices=choices),
    ).bind(
        request=req('get', foo='a'),
    )
    first = form.fields.foo.__html__()
    second = form.fields.foo.__html__()
    assert first == second
    actual = prettify(first)
    expected = prettify("""
<div>
    <label for="id_foo">Foo</label>
    
    <div>
        
        <input type="radio" value="a" name="foo" id="id_foo_1"  id="id_foo" name="foo" checked/>
        <label for="id_foo_1">a</label>

        <div class="helptext"></div>
        
    </div>

    <div>
        
        <input type="radio" value="b" name="foo" id="id_foo_2"  id="id_foo" name="foo" />
        <label for="id_foo_2">b</label>

        <div class="helptext"></div>
        
    </div>

    <div>
        
        <input type="radio" value="c" name="foo" id="id_foo_3"  id="id_foo" name="foo" />
        <label for="id_foo_3">c</label>

        <div class="helptext"></div>
        
    </div>


    <div class="helptext"></div>
    
</div>

    """)
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


# def test_choice_default_parser():
#
#     class MyThing(object):
#         def __init__(self, name):
#             self.name = name
#
#         def __str__(self):
#             return self.name
#
#     a, b, c = MyThing('a'), MyThing('b'), MyThing('c')
#
#     class MyForm(Form):
#         foo = Field.choice(choices=[a, b, c])
#
#     assert MyForm(request=req('post', **{'foo': 'b', '-': ''})).fields.foo.value is b
#     assert MyForm(request=req('post', **{'foo': 'fisk', '-': ''})).fields.foo.errors == {'fisk not in available choices'}


def test_multi_choice():
    soup = BeautifulSoup(Form(
        fields__foo=Field.multi_choice(choices=['a'])
    ).bind(
        request=req('get', foo=['0']),
    ).__html__(), 'html.parser')
    assert [x.attrs['multiple'] for x in soup.find_all('select')] == ['']


@pytest.mark.django
def test_help_text_from_model():
    from tests.models import Foo

    assert Form(
        model=Foo,
        fields__foo=Field.from_model(model=Foo, field_name='foo'),
    ).bind(
        request=req('get', foo='1'),
    ).fields.foo.help_text == 'foo_help_text'


@pytest.mark.django_db
def test_display_name_callable():
    from .models import Foo
    sentinel = '#### foo ####'
    form = Form(
        auto__model=Foo,
        auto__include=['foo'],
        fields__foo__display_name=lambda **_: sentinel,
    ).bind(request=req('get', foo='1'))
    assert sentinel in form.__html__()


@pytest.mark.django_db
def test_help_text_from_model2():
    from .models import Foo, Bar
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
    assert MyForm().bind(request=req('get', foo=smart_str(user2.pk))).fields.foo.errors == {'User matching query does not exist.'}
    assert MyForm().bind(request=req('get', foo=[smart_str(user2.pk), smart_str(user3.pk)])).fields.foo.errors == {'User matching query does not exist.'}

    form = MyForm().bind(request=req('get', foo=[smart_str(user.pk)]))
    assert form.fields.foo.errors == set()
    result = form.__html__()
    assert str(BeautifulSoup(result, "html.parser").select('#id_foo')[0]) == '<select id="id_foo" multiple="" name="foo">\n<option label="foo" selected="selected" value="1">foo</option>\n</select>'


@pytest.mark.django_db
def test_choice_queryset():
    from django.contrib.auth.models import User

    user = User.objects.create(username='foo')
    user2 = User.objects.create(username='foo2')
    User.objects.create(username='foo3')

    class MyForm(Form):
        foo = Field.choice_queryset(attr=None, choices=User.objects.filter(username=user.username))

    assert [x.pk for x in MyForm().bind(request=req('get')).fields.foo.choices] == [user.pk]
    assert MyForm().bind(request=req('get', foo=smart_str(user2.pk))).fields.foo.errors == {'User matching query does not exist.'}

    form = MyForm().bind(request=req('get', foo=[smart_str(user.pk)]))
    assert form.fields.foo.errors == set()
    result = form.__html__()
    assert str(BeautifulSoup(result, "html.parser").select('#id_foo')[0]) == '<select id="id_foo" name="foo">\n<option label="foo" selected="selected" value="1">foo</option>\n</select>'


@pytest.mark.django_db
def test_choice_queryset_do_not_cache():
    from django.contrib.auth.models import User

    User.objects.create(username='foo')

    class MyForm(Form):
        foo = Field.choice_queryset(attr=None, choices=User.objects.all(), template='iommi/form/choice.html')

    # There is just one user, check that we get it
    form = MyForm().bind(request=req('get'))
    assert form.fields.foo.errors == set()

    assert str(BeautifulSoup(form.__html__(), "html.parser").select('select')[0]) == '<select id="id_foo" name="foo">\n<option value="1">foo</option>\n</select>'

    # Now create a new queryset, check that we get two!
    User.objects.create(username='foo2')
    form = MyForm().bind(request=req('get'))
    assert form.fields.foo.errors == set()
    assert str(BeautifulSoup(form.__html__(), "html.parser").select('select')[0]) == '<select id="id_foo" name="foo">\n<option value="1">foo</option>\n<option value="2">foo2</option>\n</select>'


@pytest.mark.django_db
def test_choice_queryset_do_not_look_up_by_default():
    from django.contrib.auth.models import User

    user = User.objects.create(username='foo')

    class MyForm(Form):
        foo = Field.choice_queryset(attr=None, choices=User.objects.all())

    form = MyForm().bind(request=req('get'))
    assert form.fields.foo.errors == set()

    # The list should be empty because options are retrieved via ajax when needed
    assert str(BeautifulSoup(form.__html__(), "html.parser").select('select')[0]) == '<select id="id_foo" name="foo">\n</select>'
    assert form.fields.foo.input.template is not None

    # Now check that it renders the selected value
    form = MyForm(fields__foo__initial=user).bind(request=req('get'))
    assert form.fields.foo.value == user
    assert form.fields.foo.errors == set()

    assert form.fields.foo.input.template is not None

    expected = '<select id="id_foo" name="foo">\n<option label="foo" selected="selected" value="1">foo</option>\n</select>'
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

    class FooModel(Model):
        a = TextField(verbose_name='FOOO bar FOO')

    assert Field.from_model(FooModel, 'a').display_name == 'FOOO bar FOO'


@pytest.mark.django_db
def test_form_from_model_valid_form():
    from tests.models import FormFromModelTest

    assert [x.value for x in Form(
        auto__model=FormFromModelTest,
        auto__include=['f_int', 'f_float', 'f_bool'],
    ).bind(
        request=req('get', f_int='1', f_float='1.1', f_bool='true'),
    ).fields.values()] == [
        1,
        1.1,
        True
    ]


@pytest.mark.django_db
def test_form_from_model_error_message_include():
    from tests.models import FormFromModelTest
    with pytest.raises(AssertionError) as e:
        Form(auto__model=FormFromModelTest, auto__include=['does_not_exist', 'another_non_existant__sub', 'f_float']).bind(request=None)

    assert 'You can only include fields that exist on the model: another_non_existant__sub, does_not_exist specified but does not exist\nExisting fields:\n    f_bool\n    f_file\n    f_float\n    f_int\n    f_int_excluded\n    id' == str(e.value)


@pytest.mark.django_db
def test_form_from_model_error_message_exclude():
    from tests.models import FormFromModelTest
    with pytest.raises(AssertionError) as e:
        Form(auto__model=FormFromModelTest, auto__exclude=['does_not_exist', 'does_not_exist_2', 'f_float']).bind(request=None)

    assert 'You can only exclude fields that exist on the model: does_not_exist, does_not_exist_2 specified but does not exist\nExisting fields:\n    f_bool\n    f_file\n    f_float\n    f_int\n    f_int_excluded\n    id' == str(e.value)


@pytest.mark.django
def test_form_from_model_invalid_form():
    from tests.models import FormFromModelTest

    actual_errors = [x.errors for x in Form(
        auto__model=FormFromModelTest,
        auto__exclude=['f_int_excluded'],
    ).bind(
        request=req('get', f_int='1.1', f_float='true', f_bool='asd', f_file='foo'),
    ).fields.values()]

    assert len(actual_errors) == 4
    assert {'could not convert string to float: true'} in actual_errors
    assert {u'asd is not a valid boolean value'} in actual_errors
    assert {"invalid literal for int() with base 10: '1.1'"} in actual_errors or {"invalid literal for int() with base 10: u'1.1'"} in actual_errors


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

    assert set(Form(
        auto__model=Bar,
        fields__foo__call_target=Field.from_model
    ).bind(
        request=req('get'),
    ).fields.keys()) == {'foo'}


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
        f = Form(
            fields__foo=shortcut(required=False, ),
        ).bind(
            request=req('get', foo=''),
        )
        assert not f.get_errors()
        assert f.fields.foo.value in (None, [])
        assert f.fields.foo.rendered_value == ''

    def test_empty_data():
        f = Form(
            fields__foo=shortcut(required=False, ),
        ).bind(
            request=req('get'),
        )
        assert not f.get_errors()
        assert f.fields.foo.value in (None, [])

    def test_editable_false():
        f = Form(
            fields__foo=shortcut(required=False, initial=SENTINEL, editable=False),
        ).bind(
            request=req('get', foo='asdasasd'),
        )
        assert not f.get_errors()
        assert f.fields.foo.value is SENTINEL

    def test_editable_false_list():
        f = Form(
            fields__foo=shortcut(required=False, initial=[SENTINEL], editable=False),
        ).bind(
            request=req('get', foo='asdasasd'),
        )
        assert not f.get_errors()
        assert f.fields.foo.value == [SENTINEL]

    def test_roundtrip_from_initial_to_raw_string():
        for raw, initial in raw_and_parsed_data_tuples:
            form = Form(
                fields__foo=shortcut(required=True, initial=initial),
            ).bind(
                request=req('get'),
            )
            assert not form.get_errors()
            f = form.fields.foo
            assert not f.is_list
            assert initial == f.value
            assert raw == f.rendered_value, 'Roundtrip failed'

    def test_roundtrip_from_initial_to_raw_string_list():
        for raw, initial in raw_and_parsed_data_tuples:
            form = Form(
                fields__foo=shortcut(required=True, initial=initial),
            ).bind(
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
            form = Form(
                fields__foo=shortcut(required=True, ),
            ).bind(
                request=req('get', foo=raw),
            )
            assert not form.get_errors(), 'input: %s' % raw
            f = form.fields.foo
            if f.is_list:
                assert f.raw_data_list == raw
                assert f.value == initial
                if initial:
                    assert [type(x) for x in f.value] == [type(x) for x in initial]
            else:
                assert f.raw_data == raw
                assert f.value == initial
                assert type(f.value) == type(initial)

    def test_normalizing():
        for non_normalized, normalized in normalizing:
            form = Form(
                fields__foo=shortcut(required=True, ),
            ).bind(
                request=req('get', foo=non_normalized),
            )
            assert not form.get_errors()
            assert form.fields.foo.rendered_value == normalized

    test_roundtrip_from_raw_string_to_initial()
    test_empty_string_data()
    test_empty_data()
    test_normalizing()

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
    assert sentinel in Form(fields__foo=Field(initial='not sentinel value', render_value=lambda form, field, value: sentinel)).bind(request=req('get')).__html__()


def test_boolean_initial_true():
    fields = dict(
        foo=Field.boolean(initial=True),
        bar=Field(required=False),
    )

    form = Form(fields=fields).bind(request=req('get'))
    assert form.fields.foo.value is True

    # If there are arguments, but not for key foo it means checkbox for foo has been unchecked.
    # Field foo should therefore be false.
    form = Form(fields=fields).bind(request=RequestFactory().get('/', dict(bar='baz', **{'-submit': ''})))
    assert form.fields.foo.value is False

    form = Form(fields=fields).bind(request=RequestFactory().get('/', dict(foo='on', bar='baz', **{'-submit': ''})))
    assert form.fields.foo.value is True


def test_file():
    class FooForm(Form):
        foo = Field.file(required=False)

    file_data = '1'
    fake_file = StringIO(file_data)

    form = FooForm().bind(request=req('post', foo=fake_file))
    instance = Struct(foo=None)
    assert form.is_valid() is True
    form.apply(instance)
    assert instance.foo.file.getvalue() == b'1'

    # Non-existent form entry should not overwrite data
    form = FooForm().bind(request=req('post', foo=''))
    assert form.is_valid(), {x._name: x.errors for x in form.fields}
    form.apply(instance)
    assert instance.foo.file.getvalue() == b'1'

    form = FooForm().bind(request=req('post'))
    assert form.is_valid(), {x._name: x.errors for x in form.fields}
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

    # empty POST
    form = FooForm().bind(request=req('post', **{'-submit': ''}))
    assert form.is_valid() is False
    assert form.errors == set()
    assert form.fields.foo.errors == {'This field is required'}
    assert form.fields['bar'].errors == {'This field is required'}
    assert form.fields['baz'].errors == set()  # not present in POST request means false

    form = FooForm().bind(request=req('post', **{
        'foo': 'x',
        'bar': 'y',
        'baz': 'false',
        '-submit': '',
    }))
    assert form.is_valid() is True
    assert form.fields['baz'].value is False

    # all params in GET
    form = FooForm().bind(request=req('get', **{'-submit': ''}))
    assert form.is_valid() is False
    assert form.fields.foo.errors == {'This field is required'}
    assert form.fields['bar'].errors == {'This field is required'}
    assert form.fields['baz'].errors == set()  # not present in POST request means false

    form = FooForm().bind(request=req('get', **{
        'foo': 'x',
        'bar': 'y',
        'baz': 'on',
        '-submit': '',
    }))
    assert not form.errors
    assert not form.fields.foo.errors

    assert form.is_valid() is True


def test_mode_initials_from_get():
    class FooForm(Form):
        foo = Field(required=True)
        bar = Field(required=True)
        baz = Field.boolean(initial=True)

    # empty GET
    form = FooForm().bind(request=req('get'))
    assert form.is_valid() is True

    # initials from GET
    form = FooForm().bind(request=req('get', foo='foo_initial'))
    assert form.is_valid() is True
    assert form.fields.foo.value == 'foo_initial'

    assert form.fields.foo.errors == set()
    assert form.fields['bar'].errors == set()
    assert form.fields['baz'].errors == set()


def test_form_errors_function():
    class MyForm(Form):
        foo = Field(is_valid=lambda **_: (False, 'field error'))

    def post_validation(form, **_):
        form.add_error('global error')

    assert MyForm(
        post_validation=post_validation,
    ).bind(
        request=req('post', **{'-': '', 'foo': 'asd'}),
    ).get_errors() == {'global': {'global error'}, 'fields': {'foo': {'field error'}}}


@pytest.mark.django
@pytest.mark.filterwarnings("ignore:Model 'tests.foomodel' was already registered")
def test_null_field_factory():
    from django.db import models

    class ShouldBeNullField(models.Field):
        pass

    class FooModel(models.Model):
        should_be_null = ShouldBeNullField()
        foo = models.IntegerField()

    register_field_factory(ShouldBeNullField, factory=None)

    form = Form(auto__model=FooModel).bind(request=req('get'))
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
        'results': [
            {'id': user2.pk, 'text': smart_str(user2)}
        ],
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

    class FooModel(models.Model):
        user = models.ForeignKey(User, on_delete=CASCADE)

    User.objects.create(username='foo')
    user2 = User.objects.create(username='bar')

    form = Form(auto__model=FooModel).bind(request=req('get'))
    actual = perform_ajax_dispatch(root=form, path='/fields/user/endpoints/choices', value='ar')

    assert actual == {
        'results': [
            {'id': user2.pk, 'text': smart_str(user2)}
        ],
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

    class FooModel(models.Model):
        user = models.ForeignKey(User, on_delete=CASCADE)

    form = Form(auto__model=FooModel).bind(request=req('get', page=2))
    actual = perform_ajax_dispatch(root=form, path='/fields/user/endpoints/choices', value='ar')

    assert actual == {
        'results': [
        ],
        'pagination': {'more': False},
        'page': 2,
    }


@pytest.mark.django_db
@pytest.mark.filterwarnings("ignore:Model 'tests.foomodel' was already registered")
@pytest.mark.filterwarnings("ignore:Pagination may yield inconsistent results")
def test_choice_queryset_ajax_custom_q():
    from django.contrib.auth.models import User
    from django.db import models
    from django.db.models import CASCADE

    class FooModel(models.Model):
        user = models.ForeignKey(User, on_delete=CASCADE)

    User.objects.create(username='foo', first_name='7')
    user2 = User.objects.create(username='bar', first_name='11')

    form = Form(
        auto__model=FooModel,
        fields__user__extra__create_q_from_value=lambda field, value, **_: Q(first_name='11')
    ).bind(request=req('get'))
    actual = perform_ajax_dispatch(
        root=form,
        path='/fields/user/endpoints/choices',
        value="doesn't matter, since we hardcode value above",
    )

    assert actual == {
        'results': [
            {'id': user2.pk, 'text': smart_str(user2)}
        ],
        'pagination': {'more': False},
        'page': 1,
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
        bar = Field(post_validation=lambda field, **_: field.errors.add('FAIL'))

    request = req('get')
    form = MyForm()
    form = form.bind(request=request)
    assert dict(
        name='foo',
    ) == perform_ajax_dispatch(root=form, path='/fields/foo/endpoints/config', value=None)

    assert dict(
        valid=True,
        errors=[]
    ) == perform_ajax_dispatch(root=form, path='/fields/foo/endpoints/validate', value='new value')

    assert dict(
        valid=False,
        errors=['FAIL']
    ) == perform_ajax_dispatch(root=form, path='/fields/bar/endpoints/validate', value='new value')


@override_settings(DEBUG=True)
def test_custom_endpoint():
    class MyForm(Form):
        class Meta:
            endpoints__foo__func = lambda value, **_: 'foo' + value

    form = MyForm()
    form = form.bind(request=None)
    assert 'foobar' == perform_ajax_dispatch(root=form, path='/foo', value='bar')


def remove_csrf(html_code):
    csrf_regex = r'<input[^>]+csrfmiddlewaretoken[^>]+>'
    return re.sub(csrf_regex, '', html_code)


def test_render():
    class MyForm(Form):
        bar = Field()

    expected_html = """
        <form action="" enctype="multipart/form-data" method="post">
            <div>
                <label for="id_bar">
                    Bar
                </label>
                <input id="id_bar" name="bar" type="text" value="">
                <div class="helptext">
                </div>
            </div>
            <div class="links">
                <input accesskey="s" name="-submit" type="submit" value="Submit">
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

    assert e.value.messages == ["Invalid literal for Decimal: u'asdasd'"] or e.value.messages == ["Invalid literal for Decimal: 'asdasd'"]


def test_url_parse():
    assert url_parse(string_value='https://foo.example') == 'https://foo.example'

    with pytest.raises(ValidationError) as e:
        url_parse(string_value='asdasd')

    assert e.value.messages == ['Enter a valid URL.']


def test_render_temlate_none():
    # noinspection PyTypeChecker
    assert render_template(request=None, template=None, context=None) == ''


def test_render_template_template_object():
    assert render_template(
        request=req('get'),
        context=dict(a='1'),
        template=Template(template_string='foo {{a}} bar')
    ) == 'foo 1 bar'


def test_action_render():
    action = Action(display_name='Title', template='test_action_render.html').bind(request=req('get'))
    assert action.__html__().strip() == 'tag=a display_name=Title'


def test_action_submit_render():
    action = Action.submit(display_name='Title').bind(request=req('get'))
    assert action.__html__().strip() == '<input accesskey="s" name="-" type="submit" value="Title">'

    action = Action.submit(attrs__value='Title').bind(request=req('get'))
    assert action.__html__().strip() == '<input accesskey="s" name="-" type="submit" value="Title">'

    action = Action.submit(attrs__value='Title', template='test_action_render.html').bind(request=req('get'))
    assert action.__html__().strip() == 'tag=input display_name=Root accesskey="s" name="-" type="submit" value="Title"'


def test_action_repr():
    assert repr(Action(_name='name', template='test_link_render.html')) == '<iommi.action.Action name>'


def test_action_shortcut_icon():
    assert Action.icon('foo', display_name='title').bind(request=None).__html__() == '<a><i class="fa fa-foo"></i> title</a>'


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
        foo = Field(
            extra_evaluated__bar=lambda field, **_: field.initial
        )

    assert 17 == MyForm(instance=Struct(foo=17)).bind(request=req('get')).fields.foo.extra_evaluated.bar


@pytest.mark.django_db
def test_field_from_model_path():
    from .models import Bar

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

    result = Field.from_model(model=FromModelSubtype, field_name='foo')

    assert result.parse is int_parse


@pytest.mark.django_db
def test_create_members_from_model_path():
    from .models import Foo, Bar

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

    assert 'The convenience feature to automatically get the parameter model set only works for QuerySet instances or if you specify model_field' == str(e.value)


def test_datetime_parse():
    assert datetime_parse('2001-02-03 12') == datetime(2001, 2, 3, 12)
    assert (datetime_parse('now') - datetime.now()) < timedelta(seconds=0.1)

    bad_date = '091223'
    with pytest.raises(ValidationError) as e:
        datetime_parse(bad_date)

    expected = 'Time data "%s" does not match any of the formats "now", %s' % (bad_date, ', '.join('"%s"' % x for x in datetime_iso_formats))
    assert expected == str(e.value) or [expected] == [str(x) for x in e.value]


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

    MyForm(
        auto__model=FromModelWithInheritanceTest,
    ).bind(
        request=req('get'),
    )

    assert was_called == {
        'MyField.float': 1,
    }


@pytest.mark.django_db
def test_from_model_override_field():
    from tests.models import FormFromModelTest
    form = Form(
        auto__model=FormFromModelTest,
        fields__f_float=Field(_name='f_float'),
    ).bind(
        request=req('get'),
    )
    assert form.fields.f_float.parse is not float_parse


def test_field_merge():
    form = Form(
        fields__foo={},
        instance=Struct(foo=1),
    ).bind(
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

    form = FooForm()
    form = form.bind(request=None)
    assert list(form.fields.keys()) == ['foo', 'foo__a']


def test_help_text_for_boolean_tristate():
    form = Form(auto__model=BooleanFromModelTestModel)
    form = form.bind(request=req('get'))
    assert '$$$$' in str(form)


@pytest.mark.django_db
def test_all_field_shortcuts():
    class MyFancyField(Field):
        class Meta:
            extra__fancy = True

    class MyFancyForm(Form):
        class Meta:
            member_class = MyFancyField

    all_shortcut_names = get_members(
        cls=MyFancyField,
        member_class=Shortcut,
        is_member=is_shortcut,
    ).keys()

    config = {
        f'fields__field_of_type_{t}__call_target__attribute': t
        for t in all_shortcut_names
    }

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

    form = MyFancyForm(
        **config,
        **type_specifics
    ).bind(
        request=req('get')
    )

    for name, field in form.fields.items():
        assert field.extra.get('fancy'), name


def test_shortcut_to_subclass():
    class MyField(Field):
        @classmethod
        @class_shortcut
        def my_shortcut(cls, call_target=None, **kwargs):
            return call_target(**kwargs)

    assert isinstance(MyField.my_shortcut(), MyField)

    class MyField(Field):
        @classmethod
        @class_shortcut
        def choices(cls, call_target=None, **kwargs):
            return call_target(**kwargs)

    field = MyField.choice(choices=[])
    assert isinstance(field, MyField)
    assert field.empty_label == '---'


def test_multi_choice_choice_to_option():
    field = Struct(
        value=[1, 2],
    )
    assert multi_choice_choice_to_option(field, 1) == (1, '1', '1', True)
    assert multi_choice_choice_to_option(field, 2) == (2, '2', '2', True)
    assert multi_choice_choice_to_option(field, 3) == (3, '3', '3', False)


def test_form_h_tag():
    assert '<h1>$$$</h1>' in Form(title='$$$').bind(request=req('get')).__html__()
    assert '<b>$$$</b>' in Form(title='$$$', h_tag__tag='b').bind(request=req('get')).__html__()
    assert '<b>$$$</b>' in Form(h_tag=html.b('$$$')).bind(request=req('get')).__html__()
