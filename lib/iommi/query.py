import operator
from datetime import date
from functools import reduce
from typing import (
    Type,
)

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import (
    F,
    Model,
    Q,
)
from iommi.base import (
    bind_members,
    collect_members,
    MISSING,
    model_and_rows,
    no_copy_on_bind,
    PagePart,
    request_data,
    setup_endpoint_proxies,
    evaluate_members,
)
from iommi.form import (
    bool_parse,
    create_members_from_model,
    Form,
    member_from_model,
)
from pyparsing import (
    alphanums,
    alphas,
    CaselessLiteral,
    Combine,
    delimitedList,
    Forward,
    Group,
    Keyword,
    nums,
    oneOf,
    Optional,
    ParseException,
    ParseResults,
    QuotedString,
    quotedString,
    Word,
    ZeroOrMore,
)
from tri_declarative import (
    class_shortcut,
    declarative,
    dispatch,
    EMPTY,
    evaluate_recursive,
    Namespace,
    Refinable,
    refinable,
    setattr_path,
    setdefaults_path,
    with_meta,
    evaluate,
)
from tri_struct import Struct


# TODO: short form for boolean values? "is_us_person" or "!is_us_person"

class QueryException(Exception):
    pass


PRECEDENCE = {
    'and': 3,  # pragma: no mutate
    'or': 2,  # pragma: no mutate
}
assert PRECEDENCE['and'] > PRECEDENCE['or']  # pragma: no mutate

Q_OP_BY_OP = {
    '>': 'gt',
    '=>': 'gte',
    '>=': 'gte',
    '<': 'lt',
    '<=': 'lte',
    '=<': 'lte',
    '=': 'iexact',
    ':': 'icontains',
}

FREETEXT_SEARCH_NAME = 'term'
ADVANCED_QUERY_PARAM = 'query'

_variable_factory_by_django_field_type = {}


def register_variable_factory(field_class, factory):
    _variable_factory_by_django_field_type[field_class] = factory


def to_string_surrounded_by_quote(v):
    str_v = '%s' % v
    return '"%s"' % str_v.replace('"', '\\"')


def value_to_query_string_value_string(variable, v):
    if type(v) == bool:
        return {True: '1', False: '0'}.get(v)
    if type(v) in (int, float):
        return str(v)
    if isinstance(v, Model):
        try:
            v = getattr(v, variable.value_to_q_lookup)
        except AttributeError:
            name_ish_attributes = [x for x in dir(v) if 'name' in x and not x.startswith('_')]
            raise AttributeError(
                '{} object has no attribute {}. You can specify another name property with the value_to_q_lookup argument.{}'.format(
                    type(v),
                    variable.value_to_q_lookup,
                    " Maybe one of " + repr(name_ish_attributes) + "?" if name_ish_attributes else ""),
            )
    return to_string_surrounded_by_quote(v)


def case_sensitive_op_to_q_op(op):
    return {'=': 'exact', ':': 'contains'}.get(op) or Q_OP_BY_OP[op]


def choice_queryset_value_to_q(variable, op, value_string_or_f):
    if op != '=':
        raise QueryException('Invalid operator "%s" for variable "%s"' % (op, variable.name))
    if variable.attr is None:
        return Q()
    if isinstance(value_string_or_f, str) and value_string_or_f.lower() == 'null':
        return Q(**{variable.attr: None})
    try:
        instance = variable.form.choices.get(**{variable.value_to_q_lookup: str(value_string_or_f)})
    except ObjectDoesNotExist:
        return None
    return Q(**{variable.attr + '__pk': instance.pk})


def boolean_value_to_q(variable, op, value_string_or_f):
    if isinstance(value_string_or_f, str):
        value_string_or_f = bool_parse(value_string_or_f)
    return Variable.value_to_q(variable, op, value_string_or_f)


@with_meta
class Variable(PagePart):
    """
    Class that describes a variable that you can search for.
    """

    attr = Refinable()
    form: Namespace = Refinable()
    gui_op = Refinable()
    freetext = Refinable()
    model = Refinable()
    model_field = Refinable()
    choices = Refinable()
    value_to_q_lookup = Refinable()

    @dispatch(
        gui_op='=',
        attr=MISSING,
        form=Namespace(
            include=False,
            required=False,
        ),
        default_child=False,
    )
    def __init__(self, **kwargs):
        """
        Parameters with the prefix "form__" will be passed along downstream to the `Field` instance if applicable. This can be used to tweak the basic style interface.

        :param form__include: set to True to display a GUI element for this variable in the basic style interface.
        :param form__call_target: the factory to create a `Field` for the basic GUI, for example `Field.choice`. Default: `Field`
        """

        super(Variable, self).__init__(**kwargs)

    def __repr__(self):
        return '<{}.{} {}>'.format(self.__class__.__module__, self.__class__.__name__, self.name)

    @property
    def query(self):
        return self.parent

    def on_bind(self) -> None:
        for k, v in getattr(self.parent.parent, '_variables_unapplied_data', {}).get(self.name, {}).items():
            setattr_path(self, k, v)

        if self.attr is MISSING:
            self.attr = self.name

        self.model = evaluate(self.model, **self.evaluate_attribute_kwargs())

        evaluated_attributes = [
            'name',
            'include',
            'after',
            'default_child',
            'extra',
            'style',
            'attr',
            'gui_op',
            'freetext',
            'model_field',
            'choices',
        ]
        evaluate_members(self, evaluated_attributes, **self.evaluate_attribute_kwargs())

    def _evaluate_attribute_kwargs(self):
        return dict(query=self.parent, variable=self)

    @staticmethod
    @refinable
    def op_to_q_op(op: str) -> Q:
        return Q_OP_BY_OP[op]

    @staticmethod
    @refinable
    def value_to_q(variable, op, value_string_or_f):
        if variable.attr is None:
            return Q()
        negated = False
        if op in ('!=', '!:'):
            negated = True
            op = op[1:]
        if isinstance(value_string_or_f, str) and value_string_or_f.lower() == 'null':
            r = Q(**{variable.attr: None})
        else:
            r = Q(**{variable.attr + '__' + variable.op_to_q_op(op): value_string_or_f})
        if negated:
            return ~r
        else:
            return r

    @classmethod
    def from_model(cls, model, field_name=None, model_field=None, **kwargs):
        return member_from_model(
            cls=cls,
            model=model,
            factory_lookup=_variable_factory_by_django_field_type,
            field_name=field_name,
            model_field=model_field,
            defaults_factory=lambda model_field: {},
            **kwargs)

    @classmethod
    @class_shortcut
    def text(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        op_to_q_op=case_sensitive_op_to_q_op,
    )
    def case_sensitive(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='choice',
    )
    def choice(cls, call_target=None, **kwargs):
        """
        Field that has one value out of a set.
        :type choices: list
        """
        setdefaults_path(kwargs, dict(
            form__choices=kwargs.get('choices'),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='multi_choice',
    )
    def multi_choice(cls, call_target=None, **kwargs):
        """
        Field that has one value out of a set.
        :type choices: list
        """
        setdefaults_path(kwargs, dict(
            form__choices=kwargs.get('choices'),
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='choice_queryset',
        op_to_q_op=lambda op: 'exact',
        value_to_q_lookup='name',
        value_to_q=choice_queryset_value_to_q,
    )
    def choice_queryset(cls, choices, call_target=None, **kwargs):
        """
        Field that has one value out of a set.
        :type choices: django.db.models.QuerySet
        """
        from django.db.models import QuerySet
        if 'model' not in kwargs:
            assert isinstance(choices, QuerySet), 'The convenience feature to automatically get the parameter model set only works for QuerySet instances'
            kwargs['model'] = choices.model

        setdefaults_path(kwargs, dict(
            form__choices=choices,
            form__model=kwargs['model'],
            choices=choices,
        ))
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute="choice_queryset",
        form__call_target__attribute='multi_choice_queryset',
    )
    def multi_choice_queryset(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='boolean',
        value_to_q=boolean_value_to_q,
    )
    def boolean(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='boolean_tristate',
        value_to_q=boolean_value_to_q,
    )
    def boolean_tristate(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='integer',
    )
    def integer(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='float',
    )
    def float(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='url',
    )
    def url(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='time',
    )
    def time(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='datetime',
    )
    def datetime(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='date',
    )
    def date(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='email',
    )
    def email(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        form__call_target__attribute='decimal',
    )
    def decimal(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice_queryset',
    )
    def foreign_key(cls, model_field, model, call_target, **kwargs):
        del model
        setdefaults_path(
            kwargs,
            choices=model_field.foreign_related_fields[0].model.objects.all(),
        )
        return call_target(model_field=model_field, **kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='multi_choice_queryset',
    )
    def many_to_many(cls, call_target, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.remote_field.model.objects.all(),
            extra__django_related_field=True,
        )
        kwargs['model'] = model_field.remote_field.model
        return call_target(model_field=model_field, **kwargs)


class StringValue(str):
    def __new__(cls, s):
        if len(s) > 2 and s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
        return super(StringValue, cls).__new__(cls, s)


def default_endpoint__errors(query, **_):
    try:
        query.to_q()
        errors = query.form.get_errors()
        # These dicts contains sets that we don't want in the JSON response, so convert to list
        if 'fields' in errors:
            errors['fields'] = {x: list(y) for x, y in errors['fields'].items()}
        if 'global' in errors:
            errors['global'] = list(errors['global'])
        return errors
    except QueryException as e:
        return {'global': [str(e)]}


@no_copy_on_bind
@declarative(Variable, '_variables_dict')
@with_meta
class Query(PagePart):
    """
    Declare a query language. Example:

    .. code:: python

        class CarQuery(Query):
            make = Variable.choice(choices=['Toyota', 'Volvo', 'Ford])
            model = Variable()

        query_set = Car.objects.filter(CarQuery(request=request).to_q())
    """

    form: Namespace = Refinable()
    endpoint: Namespace = Refinable()
    model: Type['django.db.models.Model'] = Refinable()
    rows = Refinable()

    member_class = Refinable()
    form_class = Refinable()

    class Meta:
        member_class = Variable
        form_class = Form

    def children(self):
        return Struct(
            form=self.form,
            # TODO: this is a potential namespace conflict with form above. Care or not care?
            **setup_endpoint_proxies(self)
        )

    @dispatch(
        endpoint__errors=default_endpoint__errors,
        variables=EMPTY,
    )
    def __init__(self, *, model=None, rows=None, variables=None, _variables_dict=None, **kwargs):
        model, rows = model_and_rows(model, rows)

        assert isinstance(variables, dict)

        setdefaults_path(
            kwargs,
            form__call_target=self.get_meta().form_class,
            form__name='form',
        )

        self._form = None

        super(Query, self).__init__(
            model=model,
            rows=rows,
            **kwargs
        )

        self._variables_unapplied_data = {}
        self.declared_variables = collect_members(items=variables, items_dict=_variables_dict, cls=self.get_meta().member_class, unapplied_config=self._variables_unapplied_data)
        self.variables = None

    def on_bind(self) -> None:
        bind_members(self, name='variables', default_child=True)

        fields = []

        if any(v.freetext for v in self.variables.values()):
            fields.append(self.get_meta().form_class.get_meta().member_class(name=FREETEXT_SEARCH_NAME, display_name='Search', required=False))

        for variable in self.variables.values():
            if variable.form is not None and variable.form.include:
                # pass form__* parameters to the GUI component
                assert variable.name is not MISSING
                assert variable.attr is not MISSING
                params = setdefaults_path(
                    Namespace(),
                    variable.form,
                    name=variable.name,
                    attr=variable.attr,
                    model_field=variable.model_field,
                    call_target__cls=self.get_meta().form_class.get_meta().member_class
                )
                fields.append(params())

        self.form: Form = self.form(
            _fields_dict={x.name: x for x in fields},
            attrs__method='get',
            default_child=True,
            actions__submit__attrs__value='Filter',
        )
        self.form.bind(parent=self)
        # TODO: This is suspect. The advanced query param isn't namespaced for one, and why is it stored there?
        self.form.query_advanced_value = request_data(self.request()).get(ADVANCED_QUERY_PARAM, '') if self.request else ''

    def _evaluate_attribute_kwargs(self):
        return dict(query=self)

    def parse(self, query_string: str) -> Q:
        assert self._is_bound
        query_string = query_string.strip()
        if not query_string:
            return Q()
        parser = self._grammar()
        try:
            tokens = parser.parseString(query_string, parseAll=True)
        except ParseException:
            raise QueryException('Invalid syntax for query')
        return self.compile(tokens)

    def compile(self, tokens) -> Q:
        items = []
        for token in tokens:
            if isinstance(token, ParseResults):
                items.append(self.compile(token))
            elif isinstance(token, Q):
                items.append(token)
            elif token in ('and', 'or'):
                items.append(token)
        return self.__rpn_to_q(self.__to_rpn(items))

    @staticmethod
    def __rpn_to_q(tokens):
        stack = []
        for each in tokens:
            if isinstance(each, Q):
                stack.append(each)
            else:
                op = each
                # infix right hand operator is on the top of the stack
                right, left = stack.pop(), stack.pop()
                stack.append(left & right if op == 'and' else left | right)
        assert len(stack) == 1
        return stack[0]

    @staticmethod
    def __to_rpn(tokens):
        # Convert a infix sequence of Q objects and 'and/or' operators using
        # dijkstra shunting yard algorithm into RPN
        if len(tokens) == 1:
            return tokens
        result_q, stack = [], []
        for token in tokens:
            assert token is not None
            if isinstance(token, Q):
                result_q.append(token)
            elif token in PRECEDENCE:
                p1 = PRECEDENCE[token]
                while stack:
                    t2, p2 = stack[-1]
                    if p1 <= p2:
                        stack.pop()
                        result_q.append(t2)
                    else:  # pragma: no cover
                        break  # pragma: no mutate
                stack.append((token, PRECEDENCE[token]))
        while stack:
            result_q.append(stack.pop()[0])
        return result_q

    def _grammar(self):
        """
        Pyparsing implementation of a where clause grammar based on http://pyparsing.wikispaces.com/file/view/simpleSQL.py

        The query language is a series of statements separated by AND or OR operators and parentheses can be used to group/provide
        precedence.

        A statement is a combination of three strings "<variable> <operator> <value>" or "<value> <operator> <variable>".

        A value can be a string, integer or a real(floating) number, a (ISO YYYY-MM-DD) date, or a year based period (nY) where the resulting value
        will typically be base_date + relativedelta(years=n).
        See self.period_to_date

        An operator must be one of "= != < > >= <= !:" and are translated into django __lte or equivalent suffixes.
        See self.as_q

        Example
        something < 10 AND other >= 2015-01-01 AND (foo < 1 OR bar > 1)

        """
        quoted_string_excluding_quotes = QuotedString('"', escChar='\\').setParseAction(lambda token: StringValue(token[0]))
        and_ = Keyword('and', caseless=True)
        or_ = Keyword('or', caseless=True)
        exponential_marker = CaselessLiteral('E')
        binary_op = oneOf('=> =< = < > >= <= : != !:', caseless=True).setResultsName('operator')
        arith_sign = Word('+-', exact=1)
        integer = Word(nums)

        real_num = Combine(Optional(arith_sign) + (integer + '.' + Optional(integer) | ('.' + integer)) + Optional(exponential_marker + Optional(arith_sign) + integer)).setParseAction(lambda t: float(t[0]))
        int_num = Combine(Optional(arith_sign) + integer + Optional(exponential_marker + Optional('+') + integer)).setParseAction(lambda t: int(t[0]))

        def parse_date_str(token):
            y, _, m, _, d = token
            try:
                date_object = date(*map(int, (y, m, d)))
            except ValueError:
                raise QueryException('Date %s-%s-%s is out of range' % (y, m, d))
            return date_object

        date_str = (integer('year') + '-' + integer('month') + '-' + integer('day')).setParseAction(parse_date_str)

        # define query tokens
        identifier = Word(alphas, alphanums + '_$-').setName('identifier')
        variable_name = delimitedList(identifier, '.', combine=True)
        value_string = date_str | real_num | int_num | variable_name | quoted_string_excluding_quotes

        # Define a where expression
        where_expression = Forward()
        binary_operator_statement = (variable_name + binary_op + value_string).setParseAction(self.binary_op_as_q)
        free_text_statement = quotedString.copy().setParseAction(self.freetext_as_q)
        operator_statement = binary_operator_statement | free_text_statement
        where_condition = Group(operator_statement | ('(' + where_expression + ')'))
        where_expression << where_condition + ZeroOrMore((and_ | or_) + where_expression)

        # define the full grammar
        query_statement = Forward()
        query_statement << Group(where_expression).setResultsName("where")
        return query_statement

    def binary_op_as_q(self, token):
        """
        Convert a parsed token of variable_name OPERATOR variable_name into a Q object
        """
        assert self._is_bound
        variable_name, op, value_string_or_variable_name = token
        variable = self.variables.get(variable_name.lower())
        if variable:
            if isinstance(value_string_or_variable_name, str) and not isinstance(value_string_or_variable_name, StringValue) and value_string_or_variable_name.lower() in self.variables:
                value_string_or_f = F(self.variables[value_string_or_variable_name.lower()].attr)
            else:
                value_string_or_f = value_string_or_variable_name
            result = variable.value_to_q(variable=variable, op=op, value_string_or_f=value_string_or_f)
            if result is None:
                raise QueryException('Unknown value "%s" for variable "%s"' % (value_string_or_f, variable.name))
            return result
        raise QueryException(f'Unknown variable "{variable_name}", available variables: {list(self.variables.keys())}')

    def freetext_as_q(self, token):
        assert any(v.freetext for v in self.variables.values())
        assert len(token) == 1
        token = token[0].strip('"')

        return reduce(
            operator.or_,
            [
                Q(**{variable.attr + '__' + variable.op_to_q_op(':'): token})
                for variable in self.variables.values()
                if variable.freetext
            ]
        )

    def to_query_string(self):
        """
        Based on the data in the request, return the equivalent query string that you can use with parse() to create a query set.
        """
        form = self.form

        if self.request() is None:
            return ''

        request = self.request()
        if request_data(request).get(ADVANCED_QUERY_PARAM, '').strip():
            return request_data(request).get(ADVANCED_QUERY_PARAM)
        elif form.is_valid():
            def expr(field, is_list, value):
                if is_list:
                    return '(' + ' OR '.join([expr(field, is_list=False, value=x) for x in field.value_list]) + ')'
                return ''.join([
                    field.name,
                    self.variables[field.name].gui_op,
                    value_to_query_string_value_string(self.variables[field.name], value)],
                )

            result = [
                expr(field, field.is_list, field.value)
                for field in form.fields.values()
                if field.name != FREETEXT_SEARCH_NAME and field.value not in (None, '') or field.value_list not in (None, [])
            ]

            if FREETEXT_SEARCH_NAME in form.fields:
                freetext = form.fields[FREETEXT_SEARCH_NAME].value
                if freetext:
                    result.append(
                        '(%s)' % ' or '.join([
                            f'{variable.name}:{to_string_surrounded_by_quote(freetext)}'
                            for variable in self.variables.values()
                            if variable.freetext]
                        )
                    )
            return ' and '.join(result)
        else:
            return ''

    def to_q(self):
        """
        Create a query set based on the data in the request.
        """
        return self.parse(self.to_query_string())

    @classmethod
    @dispatch(
        variables=EMPTY,
    )
    def variables_from_model(cls, variables, **kwargs):
        return create_members_from_model(
            member_params_by_member_name=variables,
            default_factory=cls.get_meta().member_class.from_model,
            **kwargs
        )

    @classmethod
    @dispatch(
        variables=EMPTY,
    )
    def from_model(cls, *, rows=None, model=None, variables, include=None, exclude=None, extra_fields=None, **kwargs):
        """
        Create an entire form based on the fields of a model. To override a field parameter send keyword arguments in the form
        of "the_name_of_the_fields__param". For example:

        .. code:: python

            class Foo(Model):
                foo = IntegerField()

            Table.from_model(data=request.GET, model=Foo, fields__foo__help_text='Overridden help text')

        :param include: fields to include. Defaults to all
        :param exclude: fields to exclude. Defaults to none (except that AutoField is always excluded!)

        """
        model, rows = model_and_rows(model, rows)
        assert model is not None or rows is not None, "model or rows must be specified"
        variables = cls.variables_from_model(model=model, include=include, exclude=exclude, extra=extra_fields, variables=variables)
        return cls(rows=rows, model=model, variables=variables, **kwargs)
