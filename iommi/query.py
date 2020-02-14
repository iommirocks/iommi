import operator
from datetime import date
from functools import reduce
from typing import (
    Any,
    Dict,
    Type,
    Union,
)

from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from django.db.models import (
    F,
    Model,
    Q,
    QuerySet,
)
from pyparsing import (
    CaselessLiteral,
    Combine,
    Forward,
    Group,
    Keyword,
    Optional,
    ParseException,
    ParseResults,
    QuotedString,
    Word,
    ZeroOrMore,
    alphanums,
    alphas,
    delimitedList,
    nums,
    oneOf,
    quotedString,
)
from tri_declarative import (
    EMPTY,
    Namespace,
    Refinable,
    Shortcut,
    class_shortcut,
    declarative,
    dispatch,
    evaluate,
    refinable,
    setattr_path,
    setdefaults_path,
    with_meta,
)
from tri_struct import Struct

from iommi._web_compat import (
    Template,
    render_template,
)
from iommi.base import (
    Endpoint,
    EvaluatedRefinable,
    MISSING,
    Part,
    bind_members,
    collect_members,
    model_and_rows,
    no_copy_on_bind,
    path_join,
    request_data,
)
from iommi.form import (
    Form,
    bool_parse,
)
from iommi.from_model import (
    AutoConfig,
    NoRegisteredNameException,
    create_members_from_model,
    get_name_field,
    member_from_model,
)


# TODO: short form for boolean values? "is_us_person" or "!is_us_person"

class QueryException(Exception):
    pass


PRECEDENCE = {
    'and': 3,  # pragma: no mutate
    'or': 2,  # pragma: no mutate
}
assert PRECEDENCE['and'] > PRECEDENCE['or']  # pragma: no mutate

Q_OPERATOR_BY_QUERY_OPERATOR = {
    '>': 'gt',
    '=>': 'gte',
    '>=': 'gte',
    '<': 'lt',
    '<=': 'lte',
    '=<': 'lte',
    '=': 'iexact',
    ':': 'icontains',
}

FREETEXT_SEARCH_NAME = 'freetext'

_variable_factory_by_django_field_type = {}


def register_variable_factory(django_field_class, *, shortcut_name=MISSING, factory=MISSING):
    assert shortcut_name is not MISSING or factory is not MISSING
    if factory is MISSING:
        factory = Shortcut(call_target__attribute=shortcut_name)

    _variable_factory_by_django_field_type[django_field_class] = factory


def to_string_surrounded_by_quote(v):
    str_v = '%s' % v
    return '"%s"' % str_v.replace('"', '\\"')


def value_to_str_for_query(variable, v):
    if type(v) == bool:
        return {True: '1', False: '0'}.get(v)
    if type(v) in (int, float):
        return str(v)
    if isinstance(v, Model):
        name_field = variable.name_field
        if name_field is None:
            try:
                name_field = get_name_field(model=type(v))
            except NoRegisteredNameException as e:
                raise NoRegisteredNameException(f'{type(v).__name__} has no registered name field. Please register a name with register_name_field or specify name_field.')
        try:
            v = getattr(v, name_field)
        except AttributeError:
            raise NoRegisteredNameException(f'{type(v).__name__} has no attribute {name_field}. Please register a name with register_name_field or specify name_field.')
    return to_string_surrounded_by_quote(v)


def build_query_expression(*, field, variable, value):
    if isinstance(value, Model):
        try:
            # We ignore the return value on purpose here. We are after the raise.
            get_name_field(model=type(value))
        except NoRegisteredNameException:
            return f'{field._name}.pk={value.pk}'

    return f'{field._name}{variable.query_operator_for_form}{value_to_str_for_query(variable, value)}'


def case_sensitive_query_operator_to_q_operator(op):
    return {'=': 'exact', ':': 'contains'}.get(op) or Q_OPERATOR_BY_QUERY_OPERATOR[op]


def choice_queryset_value_to_q(variable, op, value_string_or_f):
    if op != '=':
        raise QueryException(f'Invalid operator "{op}" for variable "{variable._name}"')
    if variable.attr is None:
        return Q()
    if isinstance(value_string_or_f, str) and value_string_or_f.lower() == 'null':
        return Q(**{variable.attr: None})
    try:
        instance = variable.form.choices.get(**{variable.name_field: str(value_string_or_f)})
    except MultipleObjectsReturned:
        raise QueryException(f'Found more than one object for name "{value_string_or_f}"')
    except ObjectDoesNotExist:
        return None
    return Q(**{variable.attr + '__pk': instance.pk})


def boolean_value_to_q(variable, op, value_string_or_f):
    if isinstance(value_string_or_f, str):
        value_string_or_f = bool_parse(value_string_or_f)
    return Variable.value_to_q(variable, op, value_string_or_f)


@with_meta
class Variable(Part):
    """
    Class that describes a variable that you can search for.

    See :doc:`Query` for more complete examples.
    """

    attr = EvaluatedRefinable()
    form: Namespace = Refinable()
    query_operator_for_form: str = EvaluatedRefinable()
    freetext = EvaluatedRefinable()
    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    model_field = Refinable()
    choices = EvaluatedRefinable()
    name_field = Refinable()

    @dispatch(
        query_operator_for_form='=',
        attr=MISSING,
        form=Namespace(
            include=False,
            required=False,
        ),
    )
    def __init__(self, **kwargs):
        """
        Parameters with the prefix `form__` will be passed along downstream to the `Field` instance if applicable. This can be used to tweak the basic style interface.

        :param form__include: set to `True` to display a GUI element for this variable in the basic style interface.
        :param form__call_target: the factory to create a `Field` for the basic GUI, for example `Field.choice`. Default: `Field`
        """

        super(Variable, self).__init__(**kwargs)

    def on_bind(self) -> None:
        # TODO: why don't we do this centrally?
        if self.attr is MISSING:
            self.attr = self._name

        # Not strict evaluate on purpose
        self.model = evaluate(self.model, **self.evaluate_parameters)

    def own_evaluate_parameters(self):
        return dict(query=self._parent, variable=self)

    @staticmethod
    @refinable
    def query_operator_to_q_operator(op: str) -> str:
        return Q_OPERATOR_BY_QUERY_OPERATOR[op]

    @staticmethod
    @refinable
    def value_to_q(variable, op, value_string_or_f) -> Q:
        if variable.attr is None:
            return Q()
        negated = False
        if op in ('!=', '!:'):
            negated = True
            op = op[1:]
        if isinstance(value_string_or_f, str) and value_string_or_f.lower() == 'null':
            r = Q(**{variable.attr: None})
        else:
            r = Q(**{variable.attr + '__' + variable.query_operator_to_q_operator(op): value_string_or_f})
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
    @class_shortcut(
        form__call_target__attribute='text',
    )
    def text(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        query_operator_to_q_operator=case_sensitive_query_operator_to_q_operator,
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
        query_operator_to_q_operator=lambda op: 'exact',
        value_to_q=choice_queryset_value_to_q,
    )
    def choice_queryset(cls, choices: QuerySet, call_target=None, **kwargs):
        """
        Field that has one value out of a set.
        """
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
    def foreign_key(cls, model_field, call_target, **kwargs):
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
        query.get_q()
        errors = query.form.get_errors()
        # These dicts contains sets that we don't want in the JSON response, so convert to list
        if 'fields' in errors:
            errors['fields'] = {x: list(y) for x, y in errors['fields'].items()}
        if 'global' in errors:
            errors['global'] = list(errors['global'])
        return errors
    except QueryException as e:
        return {'global': [str(e)]}


class QueryAutoConfig(AutoConfig):
    rows = Refinable()


@no_copy_on_bind
@declarative(Variable, '_variables_dict')
@with_meta
class Query(Part):
    """
    Declare a query language. Example:

    .. code:: python

        class CarQuery(Query):
            make = Variable.choice(choices=['Toyota', 'Volvo', 'Ford])
            model = Variable()

        query_set = Car.objects.filter(
            CarQuery().bind(request=request).get_q()
        )
    """

    form: Namespace = Refinable()
    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    rows = Refinable()
    template: Union[str, Template] = EvaluatedRefinable()

    member_class = Refinable()
    form_class = Refinable()

    class Meta:
        member_class = Variable
        form_class = Form

    @dispatch(
        endpoints__errors__func=default_endpoint__errors,
        variables=EMPTY,
        auto=EMPTY,
    )
    def __init__(self, *, model=None, rows=None, variables=None, _variables_dict=None, auto, **kwargs):
        model, rows = model_and_rows(model, rows)

        assert isinstance(variables, dict)

        if auto:
            auto = QueryAutoConfig(**auto)
            assert not _variables_dict, "You can't have an auto generated Query AND a declarative Query at the same time"
            assert not model, "You can't use the auto feature and explicitly pass model. Either pass auto__model, or we will set the model for you from auto__rows"
            assert not rows, "You can't use the auto feature and explicitly pass rows. Either pass auto__rows, or we will set rows for you from auto__model (.objects.all())"
            model, rows, variables = self._from_model(
                model=auto.model,
                rows=auto.rows,
                variables=variables,
                include=auto.include,
                exclude=auto.exclude,
                additional=auto.additional,
            )

        setdefaults_path(
            kwargs,
            form__call_target=self.get_meta().form_class,
        )

        self._form = None
        self.query_advanced_value = None

        super(Query, self).__init__(
            model=model,
            rows=rows,
            **kwargs
        )

        collect_members(self, name='variables', items=variables, items_dict=_variables_dict, cls=self.get_meta().member_class)

        def generate_fields_declaration():
            field_class = self.get_meta().form_class.get_meta().member_class
            yield field_class(
                _name=FREETEXT_SEARCH_NAME,
                display_name='Search',
                required=False,
                include=False,
            )

            for name, variable in self.declared_members.variables.items():
                if variable.attr is None:
                    continue
                yield setdefaults_path(
                    Namespace(),
                    variable.form,
                    _name=name,
                    attr=name if variable.attr is MISSING else variable.attr,
                    call_target__cls=field_class,
                )()

        self.form: Form = self.form(
            _name='form',
            _fields_dict={x._name: x for x in generate_fields_declaration()},
            attrs__method='get',
            actions__submit__attrs__value='Filter',
        )
        self.declared_members.form = self.form

        # Variables need to be at the end to not steal the short names
        self.declared_members.variables = self.declared_members.pop('variables')

    @dispatch(
        render__call_target=render_template,
        context=EMPTY,
    )
    def __html__(self, *, context=None, render=None):
        if not self.bound_members.variables.bound_members:
            return ''

        setdefaults_path(
            render,
            context=context,
            template=self.template,
        )

        context['query'] = self

        return render(request=self.get_request())

    def on_bind(self) -> None:
        bind_members(self, name='variables')

        request = self.get_request()
        self.query_advanced_value = request_data(request).get(self.get_advanced_query_param(), '') if request else ''

        if any(v.freetext for v in self.variables.values()):
            self.form.declared_members.fields[FREETEXT_SEARCH_NAME].include = True

        def generate_fields_unapplied_config():
            for name, variable in self.variables.items():
                assert variable.attr, f"{name} cannot be a part of a query, it has no attr so we don't know what to search for"
                params = setdefaults_path(
                    Namespace(),
                    _name=name,
                    attr=variable.attr,
                    model_field=variable.model_field,
                )
                if not variable.include:
                    params.include = False
                yield name, params

        self.form.unapplied_config.fields = Struct(generate_fields_unapplied_config())
        self.form.bind(parent=self)

        self.bound_members.form = self.form

        bind_members(self, name='endpoints')

    def own_evaluate_parameters(self):
        return dict(query=self)

    def get_advanced_query_param(self):
        return path_join(self.iommi_path, '-query')

    def parse_query_string(self, query_string: str) -> Q:
        assert self._is_bound
        query_string = query_string.strip()
        if not query_string:
            return Q()
        parser = self._create_grammar()
        try:
            tokens = parser.parseString(query_string, parseAll=True)
        except ParseException:
            raise QueryException('Invalid syntax for query')
        return self._compile(tokens)

    def _compile(self, tokens) -> Q:
        items = []
        for token in tokens:
            if isinstance(token, ParseResults):
                items.append(self._compile(token))
            elif isinstance(token, Q):
                items.append(token)
            elif token in ('and', 'or'):
                items.append(token)
        return self._rpn_to_q(self._tokens_to_rpn(items))

    @staticmethod
    def _rpn_to_q(tokens):
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
    def _tokens_to_rpn(tokens):
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

    def _create_grammar(self):
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
        binary_operator_statement = (variable_name + binary_op + value_string).setParseAction(self._binary_op_to_q)
        free_text_statement = quotedString.copy().setParseAction(self._freetext_to_q)
        operator_statement = binary_operator_statement | free_text_statement
        where_condition = Group(operator_statement | ('(' + where_expression + ')'))
        where_expression << where_condition + ZeroOrMore((and_ | or_) + where_expression)

        # define the full grammar
        query_statement = Forward()
        query_statement << Group(where_expression).setResultsName("where")
        return query_statement

    def _binary_op_to_q(self, token):
        """
        Convert a parsed token of variable_name OPERATOR variable_name into a Q object
        """
        assert self._is_bound
        variable_name, op, value_string_or_variable_name = token

        if variable_name.endswith('.pk'):
            variable = self.variables.get(variable_name.lower()[:-len('.pk')])
            if op != '=':
                raise QueryException('Only = is supported for primary key lookup')

            try:
                pk = int(value_string_or_variable_name)
            except ValueError:
                raise QueryException(f'Could not interpret {value_string_or_variable_name} as an integer')

            return Q(**{f'{variable.attr}__pk': pk})

        variable = self.variables.get(variable_name.lower())
        if variable:
            if isinstance(value_string_or_variable_name, str) and not isinstance(value_string_or_variable_name, StringValue) and value_string_or_variable_name.lower() in self.variables:
                value_string_or_f = F(self.variables[value_string_or_variable_name.lower()].attr)
            else:
                value_string_or_f = value_string_or_variable_name
            result = variable.value_to_q(variable=variable, op=op, value_string_or_f=value_string_or_f)
            if result is None:
                raise QueryException(f'Unknown value "{value_string_or_f}" for variable "{variable._name}"')
            return result
        raise QueryException(f'Unknown variable "{variable_name}", available variables: {list(self.variables.keys())}')

    def _freetext_to_q(self, token):
        assert any(v.freetext for v in self.variables.values())
        assert len(token) == 1
        token = token[0].strip('"')

        return reduce(
            operator.or_,
            [
                Q(**{variable.attr + '__' + variable.query_operator_to_q_operator(':'): token})
                for variable in self.variables.values()
                if variable.freetext
            ]
        )

    def get_query_string(self):
        """
        Based on the data in the request, return the equivalent query string that you can use with parse_query_string() to create a query set.
        """
        form = self.form
        request = self.get_request()

        if request is None:
            return ''

        if request_data(request).get(self.get_advanced_query_param(), '').strip():
            return request_data(request).get(self.get_advanced_query_param())
        elif form.is_valid():
            def expr(field, is_list, value):
                if is_list:
                    return '(' + ' OR '.join([expr(field, is_list=False, value=x) for x in field.value]) + ')'
                return build_query_expression(field=field, variable=self.variables[field._name], value=value)

            result = [
                expr(field, field.is_list, field.value)
                for field in form.fields.values()
                if field._name != FREETEXT_SEARCH_NAME and field.value not in (None, '', [])
            ]

            if FREETEXT_SEARCH_NAME in form.fields:
                freetext = form.fields[FREETEXT_SEARCH_NAME].value
                if freetext:
                    result.append(
                        '(%s)' % ' or '.join([
                            f'{variable._name}:{to_string_surrounded_by_quote(freetext)}'
                            for variable in self.variables.values()
                            if variable.freetext]
                        )
                    )
            return ' and '.join(result)
        else:
            return ''

    def get_q(self):
        """
        Create a query set based on the data in the request.
        """
        return self.parse_query_string(self.get_query_string())

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
    def _from_model(cls, *, rows=None, model=None, variables, include=None, exclude=None, additional=None):
        model, rows = model_and_rows(model, rows)
        assert model is not None or rows is not None, "model or rows must be specified"
        variables = cls.variables_from_model(model=model, include=include, exclude=exclude, additional=additional, variables=variables)
        return model, rows, variables
