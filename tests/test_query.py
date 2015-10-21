from __future__ import unicode_literals, absolute_import
from datetime import date
from django.db.models import Q, F
import pytest
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
    bar_name = Variable.case_sensitive(attr='bar', freetext=True, gui=True)  # short form for gui__show
    baz_name = Variable(attr='baz')

query = TestQuery()


# F/Q expressions don't have a __repr__ which makes testing properly impossible, so let's just monkey patch that in
def f_repr(self):
    return '<F: %s>' % self.name
F.__repr__ = f_repr
Q.__repr__ = lambda self: str(self)


def test_request_data():
    r = Struct(method='POST', POST='POST', GET='GET')
    assert request_data(r) == 'POST'
    r.method = 'GET'
    assert request_data(r) == 'GET'


def test_empty_string():
    assert repr(query.parse('')) == repr(Q())


def test_unknown_field():
    with pytest.raises(QueryException) as e:
        query.parse('unknown_variable=1')

    assert 'Unknown variable "unknown_variable"' == e.value.message
    assert isinstance(e.value, QueryException)


def test_ops():
    for op, cmd in Q_OP_BY_OP.items():
        assert repr(query.parse('foo_name%s1' % op)) == repr(Q(**{'foo__%s' % cmd: 1}))


def test_freetext():
    assert repr(query.parse('"asd"')) == repr(Q(**{'foo__icontains': 'asd'}) | Q(**{'bar__contains': 'asd'}))


def test_or():
    assert repr(query.parse('foo_name="asd" or bar_name = 7')) == repr(Q(**{'foo__iexact': 'asd'}) | Q(**{'bar__exact': 7}))


def test_and():
    assert repr(query.parse('foo_name="asd" and bar_name = 7')) == repr(Q(**{'foo__iexact': 'asd'}) & Q(**{'bar__exact': 7}))


def test_precedence():
    assert repr(query.parse('foo_name="asd" and bar_name = 7 or baz_name = 11')) == repr((Q(**{'foo__iexact': 'asd'}) & Q(**{'bar__exact': 7})) | Q(**{'baz__iexact': 11}))


def test_parenthesis():
    assert repr(query.parse('foo_name="asd" and (bar_name = 7 or baz_name = 11)')) == repr(Q(**{'foo__iexact': 'asd'}) & (Q(**{'bar__exact': 7}) | Q(**{'baz__iexact': 11})))


def test_request_to_q_advanced():
    # noinspection PyTypeChecker
    assert repr(query.request_to_q(Struct(method='GET', GET=Data(**{ADVANCED_QUERY_PARAM: 'foo_name="asd" and (bar_name = 7 or baz_name = 11)'})))) == repr(Q(**{'foo__iexact': 'asd'}) & (Q(**{'bar__exact': 7}) | Q(**{'baz__iexact': 11})))


def test_request_to_q_simple():
    query2 = Query(variables=query.variables + [Variable.boolean(name='bazaar', attr='quux__bar__bazaar', gui__show=True)])
    # noinspection PyTypeChecker
    assert repr(query2.request_to_q(Struct(method='GET', GET=Data(**{'foo_name': "asd", 'bar_name': '7', 'bazaar': 'true'})))) == repr(Q(**{'foo__iexact': 'asd'}) & Q(**{'bar__exact': '7'}) & Q(**{'quux__bar__bazaar__iexact': 1}))


def test_request_to_q_freetext():
    # noinspection PyTypeChecker
    assert repr(query.request_to_q(Struct(method='GET', GET=Data(**{FREETEXT_SEARCH_NAME: "asd"})))) == repr(Q(**{'foo__icontains': 'asd'}) | Q(**{'bar__contains': 'asd'}))


def test_self_reference_with_f_object():
    assert repr(query.parse('foo_name=bar_name')) == repr(Q(**{'foo__iexact': F('bar')}))


def test_date():
    assert repr(query.parse('foo_name=2014-03-07')) == repr(Q(**{'foo__iexact': date(2014, 3, 7)}))


def test_invalid_syntax():
    with pytest.raises(QueryException) as e:
        query.parse('asdadad213124av@$#$#')

    assert e.value.message == 'Invalid syntax for query'
