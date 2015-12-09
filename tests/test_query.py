from __future__ import unicode_literals, absolute_import
from datetime import date
from django.db.models import Q, F
import pytest
from tests.models import Foo, Bar
from tri.query import Variable, Query, Q_OP_BY_OP, request_data, QueryException, ADVANCED_QUERY_PARAM, FREETEXT_SEARCH_NAME
from tri.struct import Struct


class Data(Struct):
    def getlist(self, key):
        r = self.get(key)
        if r is not None and not isinstance(r, list):
            return [r]
        return r


class TestQuery(Query):
    foo_name = Variable(attr='foo', freetext=True, gui__show=True)
    bar_name = Variable.case_sensitive(attr='bar', freetext=True, gui__show=True)
    baz_name = Variable(attr='baz')


# F/Q expressions don't have a __repr__ which makes testing properly impossible, so let's just monkey patch that in
def f_repr(self):
    return '<F: %s>' % self.name
F.__repr__ = f_repr
Q.__repr__ = lambda self: str(self)


def test_show():
    class ShowQuery(Query):
        foo = Variable()
        bar = Variable(
            show=lambda query, variable: query.request.GET['foo'] == 'show' and variable.extra.foo == 'show2',
            extra__foo='show2')

    # noinspection PyTypeChecker
    assert [x.name for x in ShowQuery(request=Struct(GET=Data(foo='hide'))).bound_variables] == ['foo']

    # noinspection PyTypeChecker
    assert [x.name for x in ShowQuery(request=Struct(GET=Data(foo='show'))).bound_variables] == ['foo', 'bar']


def test_request_data():
    r = Struct(method='POST', POST='POST', GET='GET')
    assert request_data(r) == 'POST'
    r.method = 'GET'
    assert request_data(r) == 'GET'


def test_empty_string():
    query = TestQuery()
    assert repr(query.parse('')) == repr(Q())


def test_unknown_field():
    query = TestQuery()
    with pytest.raises(QueryException) as e:
        query.parse('unknown_variable=1')

    assert 'Unknown variable "unknown_variable"' == e.value.message
    assert isinstance(e.value, QueryException)


def test_ops():
    query = TestQuery()
    for op, cmd in Q_OP_BY_OP.items():
        assert repr(query.parse('foo_name%s1' % op)) == repr(Q(**{'foo__%s' % cmd: 1}))


def test_freetext():
    query = TestQuery()
    assert repr(query.parse('"asd"')) == repr(Q(**{'foo__icontains': 'asd'}) | Q(**{'bar__contains': 'asd'}))


def test_or():
    query = TestQuery()
    assert repr(query.parse('foo_name="asd" or bar_name = 7')) == repr(Q(**{'foo__iexact': 'asd'}) | Q(**{'bar__exact': 7}))


def test_and():
    query = TestQuery()
    assert repr(query.parse('foo_name="asd" and bar_name = 7')) == repr(Q(**{'foo__iexact': 'asd'}) & Q(**{'bar__exact': 7}))


def test_negation():
    query = TestQuery()
    assert repr(query.parse('foo_name!:"asd" and bar_name != 7')) == repr(~Q(**{'foo__icontains': 'asd'}) & ~Q(**{'bar__exact': 7}))


def test_precedence():
    query = TestQuery()
    assert repr(query.parse('foo_name="asd" and bar_name = 7 or baz_name = 11')) == repr((Q(**{'foo__iexact': 'asd'}) & Q(**{'bar__exact': 7})) | Q(**{'baz__iexact': 11}))


def test_parenthesis():
    query = TestQuery()
    assert repr(query.parse('foo_name="asd" and (bar_name = 7 or baz_name = 11)')) == repr(Q(**{'foo__iexact': 'asd'}) & (Q(**{'bar__exact': 7}) | Q(**{'baz__iexact': 11})))


def test_request_to_q_advanced():
    query = TestQuery(request=Struct(method='GET', GET=Data(**{ADVANCED_QUERY_PARAM: 'foo_name="asd" and (bar_name = 7 or baz_name = 11)'})))
    # noinspection PyTypeChecker
    assert repr(query.to_q()) == repr(Q(**{'foo__iexact': 'asd'}) & (Q(**{'bar__exact': 7}) | Q(**{'baz__iexact': 11})))


def test_request_to_q_simple():
    class Query2(TestQuery):
        bazaar = Variable.boolean(attr='quux__bar__bazaar', gui__show=True)

    query2 = Query2(request=Struct(method='GET', GET=Data(**{'foo_name': "asd", 'bar_name': '7', 'bazaar': 'true'})))
    # noinspection PyTypeChecker
    assert repr(query2.to_q()) == repr(Q(**{'foo__iexact': 'asd'}) & Q(**{'bar__exact': '7'}) & Q(**{'quux__bar__bazaar__iexact': 1}))


def test_integer_request_to_q_simple():
    class Query2(Query):
        bazaar = Variable.integer(attr='quux__bar__bazaar', gui__show=True)

    query2 = Query2(request=Struct(method='GET', GET=Data(**{'bazaar': '11'})))
    # noinspection PyTypeChecker
    assert repr(query2.to_q()) == repr(Q(**{'quux__bar__bazaar__iexact': 11}))


def test_invalid_value():
    request = Struct(method='GET', GET=Data(**{'query': 'bazaar=asd'}))
    query2 = Query(request=request, variables=[Variable.integer(name='bazaar', value_to_q=lambda variable, op, value_string_or_f: None)])
    with pytest.raises(QueryException) as e:
        query2.to_q()
    assert e.value.message == 'Unknown value "asd" for variable "bazaar"'


def test_invalid_variable():
    query2 = Query(request=Struct(method='GET', GET=Data(**{'query': 'not_bazaar=asd'})), variables=[Variable(name='bazaar')])
    with pytest.raises(QueryException) as e:
        query2.to_q()
    assert e.value.message == 'Unknown variable "not_bazaar"'


def test_invalid_form_data():
    query2 = Query(request=Struct(method='GET', GET=Data(**{'bazaar': 'asds'})), variables=[Variable.integer(name='bazaar', attr='quux__bar__bazaar', gui__show=True)])
    # noinspection PyTypeChecker
    assert query2.to_query_string() == ''
    # noinspection PyTypeChecker
    assert repr(query2.to_q()) == repr(Q())


def test_none_attr():
    query2 = Query(request=Struct(method='GET', GET=Data(**{'bazaar': 'foo'})), variables=[Variable(name='bazaar', attr=None, gui__show=True)])
    # noinspection PyTypeChecker
    assert repr(query2.to_q()) == repr(Q())


def test_request_to_q_freetext():
    query = TestQuery(request=Struct(method='GET', GET=Data(**{FREETEXT_SEARCH_NAME: "asd"})))
    # noinspection PyTypeChecker
    assert repr(query.to_q()) == repr(Q(**{'foo__icontains': 'asd'}) | Q(**{'bar__contains': 'asd'}))


def test_self_reference_with_f_object():
    query = TestQuery()
    assert repr(query.parse('foo_name=bar_name')) == repr(Q(**{'foo__iexact': F('bar')}))


def test_null():
    query = TestQuery()
    assert repr(query.parse('foo_name=null')) == repr(Q(**{'foo': None}))


def test_date():
    query = TestQuery()
    assert repr(query.parse('foo_name=2014-03-07')) == repr(Q(**{'foo__iexact': date(2014, 3, 7)}))


def test_invalid_syntax():
    query = TestQuery()
    with pytest.raises(QueryException) as e:
        query.parse('asdadad213124av@$#$#')

    assert e.value.message == 'Invalid syntax for query'


@pytest.mark.django_db
def test_choice_queryset():
    foos = [Foo.objects.create(value=5), Foo.objects.create(value=7)]

    # make sure we get either 1 or 3 objects later when we choose a random pk
    Bar.objects.create(foo=foos[0])
    Bar.objects.create(foo=foos[1])
    Bar.objects.create(foo=foos[1])
    Bar.objects.create(foo=foos[1])

    class Query2(Query):
        foo = Variable.choice_queryset(
            model=Foo,
            choices=Foo.objects.all(),
            gui__show=True,
            value_to_q_lookup='value')
        baz = Variable.choice_queryset(
            model=Foo,
            attr=None,
            choices=None,
        )

    random_valid_obj = Foo.objects.all().order_by('?')[0]
    query2 = Query2(request=Struct(method='POST', POST=Data({'query': 'foo=%s and baz=buzz' % str(random_valid_obj.value)})))

    # test GUI
    form = query2.form(Struct(method='POST', POST=Data({'foo': 'asdasdasdasd'})))
    assert not form.is_valid()
    form = query2.form(Struct(method='POST', POST=Data({'foo': str(random_valid_obj.pk)})))
    assert form.is_valid()
    assert set(form.fields_by_name['foo'].choices) == {None} | set(Foo.objects.all())

    # test query
    # noinspection PyTypeChecker
    q = query2.to_q()
    assert set(Bar.objects.filter(q)) == set(Bar.objects.filter(foo__pk=random_valid_obj.pk))
    assert repr(q) == repr(Q(**{'foo__pk': random_valid_obj.pk}))

    # test searching for something that does not exist
    query2 = Query2(request=Struct(method='POST', POST=Data({'query': 'foo=%s' % str(11)})))
    value_that_does_not_exist = 11
    assert Foo.objects.filter(value=value_that_does_not_exist).count() == 0
    with pytest.raises(QueryException) as e:
        query2.to_q()
    assert e.value.message == 'Unknown value "%s" for variable "foo"' % value_that_does_not_exist
