from collections import defaultdict
from datetime import date

import pytest
from django.db.models import (
    F,
    Q,
    QuerySet,
)
from tri_declarative import (
    class_shortcut,
    get_members,
    get_shortcuts_by_name,
    is_shortcut,
    Namespace,
    Shortcut,
)
from tri_struct import Struct

from iommi.endpoint import perform_ajax_dispatch
from iommi.form import (
    Field,
    Form,
)
from iommi.from_model import NoRegisteredNameException
from iommi.part import request_data
from iommi.query import (
    FREETEXT_SEARCH_NAME,
    Q_OPERATOR_BY_QUERY_OPERATOR,
    Query,
    QueryException,
    value_to_str_for_query,
    Filter,
)
from iommi.traversable import declared_members
from tests.helpers import req
from tests.models import (
    Bar,
    EndPointDispatchModel,
    Foo,
    FromModelWithInheritanceTest,
    NonStandardName,
    TBar,
    TBaz,
    TFoo,
)


# This function is here to avoid declaring the query at import time, which is annoying when trying to debug unrelated tests
# noinspection PyPep8Naming
@pytest.fixture
def MyTestQuery():
    class MyTestQuery(Query):
        foo_name = Filter(attr='foo', freetext=True, field__include=True)
        bar_name = Filter.case_sensitive(attr='bar', freetext=True, field__include=True)
        baz_name = Filter(attr='baz')
    return MyTestQuery


# F/Q expressions don't have a __repr__ which makes testing properly impossible, so let's just monkey patch that in
def f_repr(self):
    return '<F: %s>' % self.name


F.__repr__ = f_repr
Q.__repr__ = lambda self: str(self)


def test_include():
    class ShowQuery(Query):
        foo = Filter()
        bar = Filter(
            include=lambda query, filter, **_: query.get_request().GET['foo'] == 'include' and filter.extra.foo == 'include2',
            extra__foo='include2')

    assert list(ShowQuery().bind(request=req('get', foo='hide')).filters.keys()) == ['foo']
    assert list(ShowQuery().bind(request=req('get', foo='include')).filters.keys()) == ['foo', 'bar']


def test_request_data():
    r = Struct(method='POST', POST='POST', GET='GET')
    assert request_data(r) == 'POST'
    r.method = 'GET'
    assert request_data(r) == 'GET'


def test_empty_string(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('')) == repr(Q())


def test_unknown_field(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    with pytest.raises(QueryException) as e:
        query.parse_query_string('unknown_filter=1')

    assert 'Unknown filter "unknown_filter"' in str(e)
    assert isinstance(e.value, QueryException)


def test_freetext(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    expected = repr(Q(**{'foo__icontains': 'asd'}) | Q(**{'bar__contains': 'asd'}))
    assert repr(query.parse_query_string('"asd"')) == expected

    query2 = MyTestQuery().bind(request=req('get', **{'-': '-', FREETEXT_SEARCH_NAME: 'asd'}))
    assert repr(query2.get_q()) == expected


def test_or(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('foo_name="asd" or bar_name = 7')) == repr(Q(**{'foo__iexact': 'asd'}) | Q(**{'bar__exact': 7}))


def test_and(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('foo_name="asd" and bar_name = 7')) == repr(Q(**{'foo__iexact': 'asd'}) & Q(**{'bar__exact': 7}))


def test_negation(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('foo_name!:"asd" and bar_name != 7')) == repr(~Q(**{'foo__icontains': 'asd'}) & ~Q(**{'bar__exact': 7}))


def test_precedence(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('foo_name="asd" and bar_name = 7 or baz_name = 11')) == repr((Q(**{'foo__iexact': 'asd'}) & Q(**{'bar__exact': 7})) | Q(**{'baz__iexact': 11}))
    assert repr(query.parse_query_string('foo_name="asd" or bar_name = 7 and baz_name = 11')) == repr(Q(**{'foo__iexact': 'asd'}) | (Q(**{'bar__exact': 7})) & Q(**{'baz__iexact': 11}))


@pytest.mark.parametrize('op,django_op', [
    ('>', 'gt'),
    ('=>', 'gte'),
    ('>=', 'gte'),
    ('<', 'lt'),
    ('<=', 'lte'),
    ('=<', 'lte'),
    ('=', 'iexact'),
    (':', 'icontains'),
])
def test_ops(op, django_op, MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('foo_name%sbar' % op)) == repr(Q(**{'foo__%s' % django_op: 'bar'}))


def test_parenthesis(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('foo_name="asd" and (bar_name = 7 or baz_name = 11)')) == repr(Q(**{'foo__iexact': 'asd'}) & (Q(**{'bar__exact': 7}) | Q(**{'baz__iexact': 11})))


def test_request_to_q_advanced(MyTestQuery):

    q = MyTestQuery().bind(request=req('get'))
    query = MyTestQuery().bind(request=req('get', **{q.get_advanced_query_param(): 'foo_name="asd" and (bar_name = 7 or baz_name = 11)'}))
    assert repr(query.get_q()) == repr(Q(**{'foo__iexact': 'asd'}) & (Q(**{'bar__exact': 7}) | Q(**{'baz__iexact': 11})))


def test_request_to_q_simple(MyTestQuery):
    class Query2(MyTestQuery):
        bazaar = Filter.boolean(attr='quux__bar__bazaar', field__include=True)

    query2 = Query2().bind(request=req('get', **{'foo_name': "asd", 'bar_name': '7', 'bazaar': 'true'}))
    assert repr(query2.get_q()) == repr(Q(**{'foo__iexact': 'asd'}) & Q(**{'bar__exact': '7'}) & Q(**{'quux__bar__bazaar__iexact': 1}))

    query2 = Query2().bind(request=req('get', **{'foo_name': "asd", 'bar_name': '7', 'bazaar': 'false'}))
    assert repr(query2.get_q()) == repr(Q(**{'foo__iexact': 'asd'}) & Q(**{'bar__exact': '7'}) & Q(**{'quux__bar__bazaar__iexact': 0}))


def test_boolean_parse():
    class MyQuery(Query):
        foo = Filter.boolean()

    assert repr(MyQuery().bind(request=None).parse_query_string('foo=false')) == repr(Q(**{'foo__iexact': False}))
    assert repr(MyQuery().bind(request=None).parse_query_string('foo=true')) == repr(Q(**{'foo__iexact': True}))


def test_boolean_unary_op():
    class MyQuery(Query):
        foo = Filter.boolean()

    assert repr(MyQuery().bind(request=None).parse_query_string('foo')) == repr(Q(**{'foo__iexact': True}))
    assert repr(MyQuery().bind(request=None).parse_query_string('!foo')) == repr(Q(**{'foo__iexact': False}))


def test_boolean_unary_op_error_messages():
    class MyQuery(Query):
        foo = Filter.integer()

    with pytest.raises(QueryException) as e:
        repr(MyQuery().bind(request=None).parse_query_string('foo'))

    assert str(e.value) == '"foo" is not a unary filter, you must use it like "foo=something"'

    with pytest.raises(QueryException) as e:
        repr(MyQuery().bind(request=None).parse_query_string('bar'))

    assert str(e.value) == 'Unknown unary filter "bar", available filters: foo'


def test_integer_request_to_q_simple():
    class Query2(Query):
        bazaar = Filter.integer(attr='quux__bar__bazaar', field=Struct(include=True))

    query2 = Query2().bind(request=req('get', bazaar='11'))
    assert repr(query2.get_q()) == repr(Q(**{'quux__bar__bazaar__iexact': 11}))


def test_gui_is_not_required():
    class Query2(Query):
        foo = Filter()
    assert Query2.foo.field.required is False


def test_invalid_value():
    q = Query(
        filters__bazaar=Filter.integer(
            value_to_q=lambda filter, op, value_string_or_f: None
        ),
    ).bind(request=req('get'))
    request = req('get', **{q.get_advanced_query_param(): 'bazaar=asd'})

    query2 = Query(
        filters__bazaar=Filter.integer(
            value_to_q=lambda filter, op, value_string_or_f: None
        ),
    ).bind(request=request)
    with pytest.raises(QueryException) as e:
        query2.get_q()
    assert 'Unknown value "asd" for filter "bazaar"' in str(e)


def test_invalid_filter():
    q = Query(
        filters__bazaar=Filter(),
    ).bind(request=req('get'))

    query2 = Query(
        filters__bazaar=Filter(),
    ).bind(request=req('get', **{q.get_advanced_query_param(): 'not_bazaar=asd'}))
    with pytest.raises(QueryException) as e:
        query2.get_q()
    assert 'Unknown filter "not_bazaar"' in str(e)


def test_invalid_form_data():

    query2 = Query(
        filters__bazaar=Filter.integer(attr='quux__bar__bazaar', field__include=True),
    ).bind(request=req('get', bazaar='asds'))
    assert query2.get_query_string() == ''
    assert repr(query2.get_q()) == repr(Q())


def test_none_attr():
    with pytest.raises(AssertionError) as e:
        Query(
            filters__bazaar=Filter(attr=None, field__include=True),
        ).bind(request=req('get', bazaar='foo'))

    assert str(e.value) == "bazaar cannot be a part of a query, it has no attr or value_to_q so we don't know what to search for"


def test_request_to_q_freetext(MyTestQuery):

    query = MyTestQuery().bind(request=req('get', **{FREETEXT_SEARCH_NAME: "asd"}))
    assert repr(query.get_q()) == repr(Q(**{'foo__icontains': 'asd'}) | Q(**{'bar__contains': 'asd'}))


def test_self_reference_with_f_object(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('foo_name=bar_name')) == repr(Q(**{'foo__iexact': F('bar')}))


def test_null(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('foo_name=null')) == repr(Q(**{'foo': None}))


def test_date(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('foo_name=2014-03-07')) == repr(Q(**{'foo__iexact': date(2014, 3, 7)}))


def test_date_out_of_range(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    with pytest.raises(QueryException) as e:
        query.parse_query_string('foo_name=2014-03-37')

    assert 'out of range' in str(e)


def test_invalid_syntax(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    with pytest.raises(QueryException) as e:
        query.parse_query_string('??asdadad213124av@$#$#')

    assert 'Invalid syntax for query' in str(e)


@pytest.mark.django_db
def test_choice_queryset():
    foos = [Foo.objects.create(foo=5), Foo.objects.create(foo=7)]

    # make sure we get either 1 or 3 objects later when we choose a random pk
    Bar.objects.create(foo=foos[0])
    Bar.objects.create(foo=foos[1])
    Bar.objects.create(foo=foos[1])
    Bar.objects.create(foo=foos[1])

    class Query2(Query):
        foo = Filter.choice_queryset(
            choices=Foo.objects.all(),
            field__include=True,
            name_field='foo')

    random_valid_obj = Foo.objects.all().order_by('?')[0]

    # test GUI
    form = Query2().bind(
        request=req('get', **{'-': '-', 'foo': 'asdasdasdasd'}),
    ).form
    assert not form.is_valid()
    query2 = Query2().bind(request=req('get', **{'-': '-', 'foo': str(random_valid_obj.pk)}))
    form = query2.form
    assert form.is_valid(), form.get_errors()
    assert set(form.fields['foo'].choices) == set(Foo.objects.all())
    q = query2.get_q()
    assert set(Bar.objects.filter(q)) == set(Bar.objects.filter(foo__pk=random_valid_obj.pk))

    # test searching for something that does not exist
    query2 = Query2().bind(
        request=req('get', **{'-': '-', query2.get_advanced_query_param(): 'foo=%s' % str(11)}),
    )
    value_that_does_not_exist = 11
    assert Foo.objects.filter(foo=value_that_does_not_exist).count() == 0
    with pytest.raises(QueryException) as e:
        query2.get_q()
    assert ('Unknown value "%s" for filter "foo"' % value_that_does_not_exist) in str(e)

    # test invalid ops
    valid_ops = ['=']
    for invalid_op in [op for op in Q_OPERATOR_BY_QUERY_OPERATOR.keys() if op not in valid_ops]:
        query2 = Query2().bind(
            request=req('get', **{'-': '-', query2.get_advanced_query_param(): 'foo%s%s' % (invalid_op, str(random_valid_obj.foo))}),
        )
        with pytest.raises(QueryException) as e:
            query2.get_q()
        assert('Invalid operator "%s" for filter "foo"' % invalid_op) in str(e)

    # test a string with the contents "null"
    assert repr(query2.parse_query_string('foo="null"')) == repr(Q(foo=None))


@pytest.mark.django_db
def test_multi_choice_queryset():
    foos = [Foo.objects.create(foo=5), Foo.objects.create(foo=7)]

    # make sure we get either 1 or 3 objects later when we choose a random pk
    Bar.objects.create(foo=foos[0])
    Bar.objects.create(foo=foos[1])
    Bar.objects.create(foo=foos[1])
    Bar.objects.create(foo=foos[1])
    Bar.objects.create(foo=foos[1])
    Bar.objects.create(foo=foos[1])
    Bar.objects.create(foo=foos[1])

    class Query2(Query):
        foo = Filter.multi_choice_queryset(
            choices=Foo.objects.all(),
            field__include=True,
            name_field='foo')

    random_valid_obj, random_valid_obj2 = Foo.objects.all().order_by('?')[:2]

    # test GUI
    form = Query2().bind(request=req('get', **{'-': '-', 'foo': 'asdasdasdasd'})).form
    assert not form.is_valid()
    query2 = Query2().bind(request=req('get', **{'-': '-', 'foo': [str(random_valid_obj.pk), str(random_valid_obj2.pk)]}))
    form = query2.form
    assert form.is_valid(), form.get_errors()
    assert set(form.fields['foo'].choices) == set(Foo.objects.all())
    q = query2.get_q()
    assert set(Bar.objects.filter(q)) == set(Bar.objects.filter(foo__pk__in=[random_valid_obj.pk, random_valid_obj2.pk]))

    # test searching for something that does not exist
    query2 = Query2().bind(request=req('get', **{'-': '-', query2.get_advanced_query_param(): 'foo=%s' % str(11)}))
    value_that_does_not_exist = 11
    assert Foo.objects.filter(foo=value_that_does_not_exist).count() == 0
    with pytest.raises(QueryException) as e:
        query2.get_q()
    assert ('Unknown value "%s" for filter "foo"' % value_that_does_not_exist) in str(e)

    # test invalid ops
    valid_ops = ['=']
    for invalid_op in [op for op in Q_OPERATOR_BY_QUERY_OPERATOR.keys() if op not in valid_ops]:
        query2 = Query2().bind(request=req('get', **{'-': '-', query2.get_advanced_query_param(): 'foo%s%s' % (invalid_op, str(random_valid_obj.foo))}))
        with pytest.raises(QueryException) as e:
            query2.get_q()
        assert('Invalid operator "%s" for filter "foo"' % invalid_op) in str(e)


@pytest.mark.django_db
def test_from_model_with_model_class():
    t = Query(auto__model=Foo).bind(request=None)
    assert list(declared_members(t).filters.keys()) == ['id', 'foo']
    assert list(t.filters.keys()) == ['foo']


@pytest.mark.django_db
def test_from_model_with_queryset():
    t = Query(auto__rows=Foo.objects.all()).bind(request=None)
    assert list(declared_members(t).filters.keys()) == ['id', 'foo']
    assert list(t.filters.keys()) == ['foo']


def test_from_model_foreign_key():
    class MyQuery(Query):
        class Meta:
            filters = Query.filters_from_model(model=Bar)

    t = MyQuery().bind(request=req('get'))
    assert list(declared_members(t).filters.keys()) == ['id', 'foo']
    assert isinstance(t.filters['foo'].choices, QuerySet)


@pytest.mark.django_db
def test_endpoint_dispatch():
    EndPointDispatchModel.objects.create(name='foo')
    x = EndPointDispatchModel.objects.create(name='bar')

    class MyQuery(Query):
        foo = Filter.choice_queryset(
            field__include=True,
            field__attr='name',
            choices=EndPointDispatchModel.objects.all().order_by('id'),
        )

    request = req('get')
    query = MyQuery().bind(request=request)

    assert query.form.fields.foo.endpoints.choices.endpoint_path == '/choices'
    expected = {
        'results': [
            {'id': x.pk, 'text': str(x)},
        ],
        'pagination': {'more': False},
        'page': 1,
    }
    assert perform_ajax_dispatch(root=query, path='/form/fields/foo/endpoints/choices', value='ar') == expected
    assert perform_ajax_dispatch(root=query, path='/choices', value='ar') == expected


def test_endpoint_dispatch_errors():
    class MyQuery(Query):
        foo = Filter.choice(
            field__include=True,
            field__attr='name',
            choices=('a', 'b'),
        )

    q = MyQuery().bind(request=req('get'))

    assert perform_ajax_dispatch(
        root=MyQuery().bind(request=req('get', **{q.get_advanced_query_param(): '!!'})),
        path='/errors',
        value='',
    ) == {'global': ['Invalid syntax for query']}
    assert perform_ajax_dispatch(
        root=MyQuery().bind(request=req('get', **{q.get_advanced_query_param(): 'foo=a'})),
        path='/errors',
        value='',
    ) == {}
    assert perform_ajax_dispatch(
        root=MyQuery().bind(request=req('get', foo='q')),
        path='/errors',
        value='',
    ) == {'fields': {'foo': ['q not in available choices']}}


def test_filter_repr():
    assert repr(Filter(_name='foo')) == '<iommi.query.Filter foo>'


@pytest.mark.django_db
def test_nice_error_message():
    with pytest.raises(NoRegisteredNameException) as e:
        value_to_str_for_query(Filter(), NonStandardName(non_standard_name='foo'))

    assert str(e.value) == "NonStandardName has no registered name field. Please register a name with register_name_field or specify name_field."

    with pytest.raises(NoRegisteredNameException) as e:
        value_to_str_for_query(Filter(name_field='custom_name_field'), NonStandardName(non_standard_name='foo'))

    assert str(e.value) == "NonStandardName has no attribute custom_name_field. Please register a name with register_name_field or specify name_field."


def test_escape_quote():
    class MyQuery(Query):
        foo = Filter(field__include=True)


    query = MyQuery().bind(request=Struct(method='GET', GET={'foo': '"', '-': '-'}))
    assert query.get_query_string() == 'foo="\\""'
    assert repr(query.get_q()) == repr(Q(**{'foo__iexact': '"'}))


def test_escape_quote_freetext():
    class MyQuery(Query):
        foo = Filter(freetext=True)


    query = MyQuery().bind(request=Struct(method='GET', GET={FREETEXT_SEARCH_NAME: '"', '-': '-'}))
    assert query.get_query_string() == '(foo:"\\"")'
    assert repr(query.get_q()) == repr(Q(**{'foo__icontains': '"'}))


def test_freetext_combined_with_other_stuff():
    class MyTestQuery(Query):
        foo_name = Filter(attr='foo', freetext=True, field__include=True)
        bar_name = Filter.case_sensitive(attr='bar', freetext=True, field__include=True)

        baz_name = Filter(attr='baz', field__include=True)

    expected = repr(Q(**{'baz__iexact': '123'}) & Q(Q(**{'foo__icontains': 'asd'}) | Q(**{'bar__contains': 'asd'})))

    assert repr(MyTestQuery().bind(request=req('get', **{'-': '-', FREETEXT_SEARCH_NAME: 'asd', 'baz_name': '123'})).get_q()) == expected


@pytest.mark.django_db
def test_from_model_with_inheritance():
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

    class MyFilter(Filter):
        @classmethod
        @class_shortcut(
            field__call_target__attribute='float',
        )
        def float(cls, call_target=None, **kwargs):
            was_called['MyVariable.float'] += 1
            return call_target(**kwargs)

    class MyQuery(Query):
        class Meta:
            member_class = MyFilter
            form_class = MyForm

    query = MyQuery(
        auto__model=FromModelWithInheritanceTest,
        filters__value__field__include=True,
    )
    query.bind(request=req('get'))

    assert was_called == {
        'MyField.float': 1,
        'MyVariable.float': 1,
    }


@pytest.mark.parametrize('name, shortcut', get_shortcuts_by_name(Filter).items())
def test_shortcuts_map_to_form(name, shortcut):
    if name == 'case_sensitive':  # This has no equivalent in Field
        return

    assert shortcut.dispatch.field.call_target.attribute == name


@pytest.mark.django_db
def test_all_filter_shortcuts():
    class MyFancyFilter(Filter):
        class Meta:
            extra__fancy = True

    class MyFancyQuery(Query):
        class Meta:
            member_class = MyFancyFilter

    all_shortcut_names = get_members(
        cls=MyFancyFilter,
        member_class=Shortcut,
        is_member=is_shortcut,
    ).keys()

    config = {
        f'filters__filter_of_type_{t}__call_target__attribute': t
        for t in all_shortcut_names
    }

    type_specifics = Namespace(
        filters__filter_of_type_choice__choices=[],
        filters__filter_of_type_multi_choice__choices=[],
        filters__filter_of_type_choice_queryset__choices=TFoo.objects.none(),
        filters__filter_of_type_multi_choice_queryset__choices=TFoo.objects.none(),
        filters__filter_of_type_many_to_many__model_field=TBaz.foo.field,
        filters__filter_of_type_foreign_key__model_field=TBar.foo.field,
    )

    query = MyFancyQuery(
        **config,
        **type_specifics
    ).bind(
        request=req('get')
    )

    for name, filter in query.filters.items():
        assert filter.extra.get('fancy'), name


def test_pk(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    assert repr(query.parse_query_string('foo_name.pk=7')) == repr(Q(**{'foo__pk': 7}))


def test_pk_error_message_1(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    with pytest.raises(QueryException) as e:
        query.parse_query_string('foo_name.pk=foo')

    assert str(e.value) == 'Could not interpret foo as an integer'


def test_pk_error_message_2(MyTestQuery):
    query = MyTestQuery().bind(request=None)
    with pytest.raises(QueryException) as e:
        query.parse_query_string('foo_name.pk:7')

    assert str(e.value) == 'Only = is supported for primary key lookup'


def test_error_message_when_trying_freetext_via_advanced_query_when_no_freetext_field_exists():
    class MyTestQuery(Query):
        foo_name = Filter(attr='foo')

    query = MyTestQuery().bind(request=None)

    with pytest.raises(QueryException) as e:
        query.parse_query_string('"freetext"')

    assert str(e.value) == 'There are no freetext filters available'
