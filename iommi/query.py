import operator
from datetime import datetime
from functools import reduce
from typing import (
    Callable,
    Type,
    Union,
)

from django.conf import settings
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
from django.utils import timezone
from django.utils.translation import (
    gettext_lazy,
    pgettext,
)
from pyparsing import (
    alphanums,
    alphas,
    Char,
    Forward,
    Group,
    Keyword,
    oneOf,
    ParseException,
    ParseResults,
    QuotedString,
    quotedString,
    Word,
    ZeroOrMore
)

from iommi._web_compat import (
    render_template,
    Template,
    ValidationError
)
from iommi.action import (
    Action,
)
from iommi.base import (
    items,
    keys,
    MISSING,
    model_and_rows,
    NOT_BOUND_MESSAGE,
    values
)
from iommi.declarative import declarative
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    getattr_path,
    Namespace,
    setdefaults_path
)
from iommi.endpoint import path_join
from iommi.evaluate import (
    evaluate,
    evaluate_strict,
)
from iommi.form import (
    bool_parse,
    boolean_tristate__parse,
    date_parse,
    float_parse,
    Form,
    int_parse,
    time_parse
)
from iommi.fragment import (
    Fragment,
)
from iommi.from_model import (
    AutoConfig,
    create_members_from_model,
    get_search_fields,
    member_from_model,
    NoRegisteredSearchFieldException
)
from iommi.member import (
    bind_member,
    bind_members,
    refine_done_members,
    reify_conf,
)
from iommi.part import (
    Part,
)
from iommi.refinable import (
    EvaluatedRefinable,
    Prio,
    Refinable,
    refinable,
    RefinableMembers,
    SpecialEvaluatedRefinable
)
from iommi.shortcut import (
    Shortcut,
    with_defaults,
)
from iommi.struct import Struct


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

FREETEXT_SEARCH_NAME = 'freetext_search'

_filter_factory_by_django_field_type = {}


def register_filter_factory(django_field_class, *, shortcut_name=MISSING, factory=MISSING, **kwargs):
    assert shortcut_name is not MISSING or factory is not MISSING
    if factory is MISSING:
        factory = Shortcut(call_target__attribute=shortcut_name, **kwargs)

    _filter_factory_by_django_field_type[django_field_class] = factory


def to_string_surrounded_by_quote(v):
    str_v = '%s' % v
    return '"%s"' % str_v.replace('"', '\\"')


def value_to_str_for_query(filter, v):
    if isinstance(v, bool):
        return {True: '1', False: '0'}.get(v)
    if type(v) in (int, float):
        return str(v)
    if isinstance(v, datetime) and timezone.is_aware(v):
        v = timezone.make_naive(v, timezone=timezone.utc)
    if isinstance(v, Model):
        model = type(v)
        search_field = filter.search_fields[-1]
        try:
            v = getattr_path(v, search_field)
        except AttributeError:
            raise NoRegisteredSearchFieldException(
                f'{model.__name__} has no attribute {search_field}. Please register search fields with register_search_fields or specify search_fields.'
            )
    return to_string_surrounded_by_quote(v)


def build_query_expression(*, filter, value):
    if isinstance(value, Model):
        return f'{filter.query_name}.pk={value.pk}'

    return f'{filter.query_name}{filter.query_operator_for_field}{value_to_str_for_query(filter, value)}'


def case_sensitive_query_operator_to_q_operator(op):
    return {'=': 'exact', ':': 'contains'}.get(op) or Q_OPERATOR_BY_QUERY_OPERATOR[op]


def boolean__query_operator_to_q_operator(op):
    if op != '=':
        raise QueryException(f'Invalid operator "{op}" for boolean filter. The only valid operator is "=".')
    return 'exact'


def choice_queryset_value_to_q(filter, op, value_string_or_f, **_):
    if op != '=':
        raise QueryException(f'Invalid operator "{op}" for filter "{filter._name}"')
    if filter.attr is None:
        return Q()
    if isinstance(value_string_or_f, str) and value_string_or_f.lower() == 'null':
        return Q(**{filter.attr: None})
    try:
        instance = None
        for search_field in filter.search_fields:
            try:
                instance = filter.choices.get(**{search_field: str(value_string_or_f)})
                break
            except ObjectDoesNotExist:
                pass
    except MultipleObjectsReturned:
        raise QueryException(f'Found more than one object for name "{value_string_or_f}"')
    if instance is None:
        return None
    return Q(**{filter.attr + '__pk': instance.pk})


choice_queryset_value_to_q.iommi_needs_attr = True


def default_filter__is_valid_filter(name, filter, **_):
    return (
        filter.attr or filter.value_to_q,
        f"{name} cannot be a part of a query, it has no attr or value_to_q so we don't know what to search for. If you want to include it anyway you can define the callback is_valid_filter which should return a boolean and a string with an error message if the boolean is False. The simplest way to do that would be is_valid_filter=lambda **_: (True, '') (filter__is_valid_filter=lambda **_: (True, '') for a Column)",
    )


def choice_queryset__is_valid_filter(name, filter, **_):
    return (
        filter.attr,
        f"{name} cannot be a part of a query, it has no attr so we don't know what to search for. If you want to include it anyway you can define the callback is_valid_filter which should return a boolean and a string with an error message if the boolean is False. The simplest way to do that would be is_valid_filter=lambda **_: (True, '') (filter__is_valid_filter=lambda **_: (True, '') for a Column)",
    )


class Filter(Part):
    """
    Class that describes a filter that you can search for.

    See :doc:`Query` for more complete examples.
    """

    attr = EvaluatedRefinable()
    field: Namespace = Refinable()
    query_operator_for_field: str = EvaluatedRefinable()
    freetext = EvaluatedRefinable()
    model: Type[Model] = SpecialEvaluatedRefinable()
    model_field = Refinable()
    model_field_name = Refinable()
    choices = EvaluatedRefinable()
    search_fields = Refinable()
    unary = Refinable()
    is_valid_filter = Refinable()
    query_name = EvaluatedRefinable()
    pk_lookup_to_q = Refinable()

    @with_defaults(
        query_operator_for_field='=',
        attr=MISSING,
        search_fields=MISSING,
        field__required=False,
        is_valid_filter=default_filter__is_valid_filter,
        query_name=lambda filter, **_: filter.iommi_name(),
    )
    def __init__(self, **kwargs):
        """
        Parameters with the prefix `field__` will be passed along downstream to the `Field` instance if applicable. This can be used to tweak the basic style interface.

        :param field__include: set to `True` to display a GUI element for this filter in the basic style interface.
        :param field__call_target: the factory to create a `Field` for the basic GUI, for example `Field.choice`. Default: `Field`
        """
        super(Filter, self).__init__(**kwargs)

    def on_refine_done(self):
        if 'choice' in getattr(self, 'iommi_shortcut_stack', []):
            assert (
                self.iommi_namespace.get('choices') is not None
            ), 'To use Filter.choice, you must pass the choices list'

        model_field = self.model_field
        if model_field and model_field.remote_field:
            self.model = model_field.remote_field.model
        super(Filter, self).on_refine_done()

    def on_bind(self) -> None:
        if self.attr is MISSING:
            self.attr = self._name

        # Not strict evaluate on purpose
        self.model = evaluate(self.model, **self.iommi_evaluate_parameters())

        if self.model and self.include and self.attr:
            try:
                self.search_fields = get_search_fields(model=self.model)
            except NoRegisteredSearchFieldException:
                self.search_fields = ['pk']

    def own_evaluate_parameters(self):
        return dict(filter=self)

    def __html__(self, *, render=None):
        assert False, (
            "Filters aren't rendered directly. You either render the Field corresponding to the filter, "
            "or the entire Query object."
        )

    @staticmethod
    @refinable
    def query_operator_to_q_operator(op: str) -> str:
        return Q_OPERATOR_BY_QUERY_OPERATOR[op]

    @staticmethod
    @refinable
    def parse(string_value, **_):
        return string_value

    @staticmethod
    @refinable
    def value_to_q(filter, op, value_string_or_f, **_) -> Q:
        if filter.attr is None:
            return Q()
        negated = False
        if op in ('!=', '!:'):
            negated = True
            op = op[1:]
        is_str = isinstance(value_string_or_f, str)
        if is_str and value_string_or_f.lower() == 'null':
            r = Q(**{filter.attr: None})
        else:
            if is_str:
                value_string_or_f = filter.parse(filter=filter, string_value=value_string_or_f, op=op)
            r = Q(**{filter.attr + '__' + filter.query_operator_to_q_operator(op): value_string_or_f})
        if negated:
            return ~r
        else:
            return r

    @classmethod
    @dispatch
    def from_model(cls, model=None, model_field_name=None, model_field=None, **kwargs):
        return reify_conf(cls._from_model(model=model, model_field_name=model_field_name, model_field=model_field, **kwargs))

    @classmethod
    @dispatch
    def _from_model(cls, model, model_field_name=None, model_field=None, **kwargs):
        return member_from_model(
            cls=cls,
            model=model,
            factory_lookup=_filter_factory_by_django_field_type,
            model_field_name=model_field_name,
            model_field=model_field,
            defaults_factory=lambda model_field: {},  # TODO: this is wrong! but base_defaults_factory doesn't work either.. there's no display_name on Filter
            **kwargs,
        )

    @classmethod
    @with_defaults(
        field__call_target__attribute='text',
        query_operator_for_field=':',
    )
    def text(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults
    def textarea(cls, **kwargs):
        return cls.text(**kwargs)

    @classmethod
    @with_defaults(
        query_operator_to_q_operator=case_sensitive_query_operator_to_q_operator,
    )
    def case_sensitive(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='choice',
    )
    def choice(cls, **kwargs):
        """
        Field that has one value out of a set.
        """
        instance = cls(**kwargs)
        instance = instance.refine(
            Prio.shortcut,
            field__choices=kwargs.get('choices'),
        )
        return instance

    @classmethod
    @with_defaults(
        field__call_target__attribute='multi_choice',
    )
    def multi_choice(cls, **kwargs):
        """
        Field that has one value out of a set.
        """
        instance = cls(**kwargs)
        instance = instance.refine(
            Prio.shortcut,
            field__choices=kwargs.get('choices'),
        )
        return instance

    @classmethod
    def checkboxes(cls, **kwargs):
        return cls.multi_choice(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='choice_queryset',
        query_operator_to_q_operator=lambda op: 'exact',
        value_to_q=choice_queryset_value_to_q,
        is_valid_filter=choice_queryset__is_valid_filter,
    )
    def choice_queryset(cls, choices: QuerySet | Callable[..., QuerySet] = None, **kwargs):
        """
        Field that has one value out of a set.
        """
        if 'model' not in kwargs:
            assert isinstance(
                choices, QuerySet
            ), 'The convenience feature to automatically get the parameter model set only works for QuerySet instances'
            kwargs['model'] = choices.model

        setdefaults_path(
            kwargs,
            dict(
                field__choices=choices,
                field__model=kwargs['model'],
                choices=choices,
            ),
        )
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='multi_choice_queryset',
    )
    def multi_choice_queryset(cls, **kwargs):
        return cls.choice_queryset(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='boolean',
        parse=bool_parse,
        unary=True,
        query_operator_to_q_operator=boolean__query_operator_to_q_operator,
    )
    def boolean(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='boolean_tristate',
        parse=boolean_tristate__parse,
        query_operator_to_q_operator=boolean__query_operator_to_q_operator,
        unary=True,
    )
    def boolean_tristate(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='number',
        query_operator_to_q_operator=case_sensitive_query_operator_to_q_operator,
    )
    def number(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='integer',
        parse=int_parse,
    )
    def integer(cls, **kwargs):
        return cls.number(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='float',
        parse=float_parse,
    )
    def float(cls, **kwargs):
        return cls.number(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='url',
    )
    def url(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='time',
        parse=time_parse,
    )
    def time(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='date',
        parse=date_parse,
        extra_evaluated__is_tz_aware=lambda **_: settings.USE_TZ,
    )
    def datetime(cls, **kwargs):
        if isinstance(kwargs.get('attr'), str):
            kwargs['attr'] = kwargs['attr'] + '__date'
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='date',
        parse=date_parse,
    )
    def date(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='email',
    )
    def email(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='decimal',
    )
    def decimal(cls, **kwargs):
        return cls.number(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='file',
    )
    def file(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='duration',
    )
    def duration(cls, **kwargs):
        return cls.text(**kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='foreign_key',
    )
    def foreign_key(cls, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.foreign_related_fields[0].model.objects.all(),
        )
        return cls.choice_queryset(model_field=model_field, **kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='foreign_key_reverse',
    )
    def foreign_key_reverse(cls, *, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.remote_field.model.objects.all(),
            extra__django_related_field=True,
        )
        return cls.multi_choice_queryset(model_field=model_field, **kwargs)

    @classmethod
    @with_defaults(
        field__call_target__attribute='many_to_many',
    )
    def many_to_many(cls, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.remote_field.model.objects.all(),
            extra__django_related_field=True,
        )
        return cls.multi_choice_queryset(model_field=model_field, **kwargs)

    @classmethod
    @with_defaults
    def many_to_many_reverse(cls, model_field, **kwargs):
        return cls.many_to_many(model_field=model_field, **kwargs)


Filter.value_to_q.iommi_needs_attr = True


class StringValue(str):
    pass


def default_endpoint__errors(query, **_):
    try:
        query.get_q()
        errors = query.form.get_errors()
        # These dicts contains sets that we don't want in the JSON response, so convert to list
        if 'fields' in errors:
            errors['fields'] = {x: list(y) for x, y in items(errors['fields'])}
        if 'global' in errors:
            errors['global'] = list(errors['global'])
        return errors
    except QueryException as e:
        return {'global': [str(e)]}


class QueryAutoConfig(AutoConfig):
    """
    :param rows: A `QuerySet` object. If this field is specified, the `model` attribute will be automatically derived. This cannot be a callable, in that case set `model` and use `rows=lambda...` instead of `auto__rows`.
    """
    rows = Refinable()


class Advanced(Fragment):
    toggle: Namespace = Refinable()

    @with_defaults(
        toggle__call_target=Action,
        toggle__attrs__href='#',
        toggle__attrs__class__iommi_query_toggle_simple_mode=True,
        toggle__attrs={'data-advanced-mode': 'simple'},
    )
    def __init__(self, **kwargs):
        super(Advanced, self).__init__(**kwargs)

    def on_refine_done(self):
        self.toggle = self.toggle(
            _name='toggle',
            display_name=gettext_lazy('Switch to advanced search'),
        ).refine_done(parent=self)
        super(Advanced, self).on_refine_done()

    def on_bind(self) -> None:
        super(Advanced, self).on_bind()
        self.toggle = self.toggle.bind(parent=self)


@declarative(Filter, '_filters_dict', add_init_kwargs=False)
class Query(Part):
    # language=rst
    """
    Declare a query language. Example:

    .. code-block:: python

        class AlbumQuery(Query):
            year = Filter.integer()
            name = Filter()

        query_set = Album.objects.filter(
            AlbumQuery().bind(request=request).get_q()
        )
    """

    auto: QueryAutoConfig = Refinable()
    form: Namespace = Refinable()
    advanced: Namespace = Refinable()
    model: Type[Model] = SpecialEvaluatedRefinable()
    rows = Refinable()
    template: Union[str, Template] = EvaluatedRefinable()
    form_container: Fragment = EvaluatedRefinable()

    member_class: Type[Filter] = Refinable()
    form_class: Type[Form] = Refinable()

    # Filters need to be at the end to not steal the short names
    filters: Namespace = RefinableMembers()

    class Meta:
        member_class = Filter
        form_class = Form
        filters = EMPTY
        auto = EMPTY

    @with_defaults(
        endpoints__errors__func=default_endpoint__errors,
        form__attrs={'data-iommi-errors': lambda query, **_: query.endpoints.errors.iommi_path},
        form_container__call_target=Fragment,
        form_container__tag='span',
        form_container__attrs__class__iommi_query_form_simple=True,
        advanced__call_target=Advanced,
    )
    def __init__(self, **kwargs):
        super(Query, self).__init__(**kwargs)

    def on_refine_done(self):
        assert isinstance(self.filters, dict)

        if self.auto:
            auto = QueryAutoConfig(**self.auto).refine_done(parent=self)
            model, rows, filters_from_auto = self._from_model(
                model=auto.model,
                rows=auto.rows,
                include=auto.include,
                exclude=auto.exclude,
                default_included=auto.default_included,
            )

            assert self.model is None, (
                "You can't use the auto feature and explicitly pass model. "
                "Either pass auto__model, or we will set the model for you from auto__rows"
            )

            if self.model is None:
                self.model = model

            if self.rows is None:
                self.rows = rows
        else:
            filters_from_auto = None

        self.model, self.rows = model_and_rows(self.model, self.rows)

        self.query_advanced_value = None
        self.query_error = None

        refine_done_members(
            self,
            name='filters',
            members_from_namespace=self.filters,
            members_from_declared=self.get_declared('_filters_dict'),
            members_from_auto=filters_from_auto,
            cls=self.member_class,
        )

        self._on_refine_done_form()

        self.advanced = self.advanced(_name='advanced').refine_done(parent=self)
        self.form_container = self.form_container(_name='form_container').refine_done(parent=self)

        super(Query, self).on_refine_done()

    @dispatch(
        render__call_target=render_template,
    )
    def __html__(self, *, render=None):
        assert self._is_bound, NOT_BOUND_MESSAGE
        if not self.iommi_bound_members().filters.iommi_bound_members():
            return ''

        setdefaults_path(
            render,
            context=self.iommi_evaluate_parameters(),
            template=self.template,
        )

        return render(request=self.get_request())

    def _on_refine_done_form(self):
        field_class = self.form_class.get_meta().member_class

        declared_fields = Struct()

        freetext_search_config = self.iommi_namespace.form.get('fields', {}).get(FREETEXT_SEARCH_NAME, {})
        if freetext_search_config is not None:
            declared_fields[FREETEXT_SEARCH_NAME] = setdefaults_path(
                Namespace(),
                freetext_search_config,
                _name=FREETEXT_SEARCH_NAME,
                call_target__cls=field_class,
                display_name=gettext_lazy('Search'),
                required=False,
                include=lambda query, **_: any(filter.freetext for filter in values(query.filters)),
                help__include=False,
            )

        for name, filter in items(self.iommi_namespace.filters):
            _orig_include = getattr_path(filter, 'field__include', not filter.freetext)
            declared_fields[name] = setdefaults_path(
                Namespace(
                    include=(
                        lambda query, field, _orig_include=_orig_include, **_: (
                            field.iommi_name() in query.filters
                            and evaluate_strict(_orig_include, **query.iommi_evaluate_parameters())
                        )
                    )
                    if getattr(filter, 'include', None) is not False
                    else False,
                ),
                filter.field,
                _name=name,
                call_target__cls=field_class,
                model_field=filter.model_field,
                attr=name if filter.attr is MISSING else filter.attr,
                help__include=False,
            )

        # Remove fields from the form that correspond to non-included filters
        declared_filters = self.iommi_namespace.filters
        for name, field in items(declared_fields):
            if name == FREETEXT_SEARCH_NAME:
                continue
            # We need to check if it's in declared_filters first, otherwise we remove any injected fields
            if name in declared_filters and name not in self.iommi_namespace.filters:
                declared_fields[name] = field.refine_from_query(include=False)

        form_args = self.form

        # noinspection PyCallingNonCallable
        self.form: Form = (
            self.form_class(
                **setdefaults_path(
                    Namespace(),
                    form_args,
                    _name='form',
                    fields=declared_fields,
                    attrs__method='get',
                    actions__submit=dict(
                        attrs={'data-iommi-filter-button': ''},
                        display_name=pgettext(context='verb', message='Filter'),
                    ),
                )
            )
            .refine_done(parent=self)
        )

    def on_bind(self) -> None:
        # Prevent the nested form from thinking it's a part of a nested form set up
        if 'form' in self._evaluate_parameters:
            del self._evaluate_parameters['form']

        bind_members(self, name='filters')

        request = self.get_request()
        self.query_advanced_value = request.GET.get(self.get_advanced_query_param(), '').strip() if request else ''

        bind_members(self, name='endpoints')

        bind_member(self, name='form')
        bind_member(self, name='advanced')
        bind_member(self, name='form_container')

        self.filter_name_by_query_name = {x.query_name: name for name, x in items(self.filters)}

    @staticmethod
    @refinable
    def filter(query, rows, **_):
        if query.form:
            q = None
            try:
                q = query.get_q()
            except QueryException:
                # This exception is dumped into `query_error` inside `get_q` before being reraised, so it's fine to ignore it here.
                pass
            if q:
                rows = rows.filter(q)

        return query.invoke_callback(query.postprocess, rows=rows)

    @staticmethod
    @refinable
    def postprocess(rows, **_):
        return rows

    def own_evaluate_parameters(self):
        return dict(query=self)

    def get_advanced_query_param(self):
        return '-' + path_join(self.iommi_path, 'query')

    def parse_query_string(self, query_string: str) -> Q:
        assert self._is_bound, NOT_BOUND_MESSAGE
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

        A statement is a combination of three strings "<filter> <operator> <value>" or "<filter> <operator> <filter>".

        A value can be a string, integer or a real(floating) number or a (ISO YYYY-MM-DD) date.

        An operator must be one of "= != < > >= <= !:" and are translated into django __lte or equivalent suffixes.
        See self.as_q

        Example
        something < 10 AND other >= 2015-01-01 AND (foo < 1 OR bar > 1)

        """
        quoted_string_excluding_quotes = QuotedString('"', escChar='\\').setParseAction(
            lambda token: StringValue(token[0])
        )
        and_ = Keyword('and', caseless=True)
        or_ = Keyword('or', caseless=True)
        binary_op = oneOf('=> =< = < > >= <= : != !:', caseless=True).setResultsName('operator')

        # define query tokens
        identifier = Word(alphas, alphanums + '_$-.').setName('identifier')
        raw_value_chars = alphanums + '_$-+/$%*;?@[]\\^`{}|~.'
        raw_value = Word(raw_value_chars, raw_value_chars).setName('raw_value')
        value_string = quoted_string_excluding_quotes | raw_value

        # Define a where expression
        where_expression = Forward()
        binary_operator_statement = (identifier + binary_op + value_string).setParseAction(self._binary_op_to_q)
        unary_operator_statement = (identifier | (Char('!') + identifier)).setParseAction(self._unary_op_to_q)
        free_text_statement = quotedString.copy().setParseAction(self._freetext_to_q)
        operator_statement = binary_operator_statement | free_text_statement | unary_operator_statement
        where_condition = Group(operator_statement | ('(' + where_expression + ')'))
        where_expression << where_condition + ZeroOrMore((and_ | or_) + where_expression)

        # define the full grammar
        query_statement = Forward()
        query_statement << Group(where_expression).setResultsName("where")
        return query_statement

    def _unary_op_to_q(self, token):
        if len(token) == 1:
            (filter_name,) = token
            value = 'true'
        else:
            (op, filter_name) = token
            value = 'false'
            if op != '!':  # pragma: no cover. You can't actually get here because you'll get a syntax error earlier
                raise QueryException(f'Unknown unary filter operator "{op}", available operators: !')

        filter = self.filters.get(filter_name.lower())
        if filter:
            if not filter.unary:
                raise QueryException(
                    f'"{filter_name}" is not a unary filter, you must use it like "{filter_name}=something"'
                )
            result = filter.invoke_callback(filter.value_to_q, op='=', value_string_or_f=value)
            return result
        raise QueryException(
            f'Unknown unary filter "{filter_name}", available filters: {", ".join(list(keys(self.filters)))}'
        )

    def _binary_op_to_q(self, token):
        """
        Convert a parsed token of filter_name OPERATOR filter_name into a Q object
        """
        assert self._is_bound, NOT_BOUND_MESSAGE
        query_name, op, value_string_or_filter_name = token

        pk_lookup = False
        if query_name.endswith('.pk'):
            query_name = query_name[: -len('.pk')]
            pk_lookup = True

        filter_name = self.filter_name_by_query_name.get(query_name)
        if filter_name is None:
            raise QueryException(
                f'Unknown filter "{query_name}", available filters: {list(keys(self.filter_name_by_query_name))}'
            )

        filter = self._lowercase_filters().get(filter_name.lower())
        if filter is None:
            raise QueryException(
                f'Unknown filter "{query_name}", available filters: {list(keys(self.filter_name_by_query_name))}'
            )

        if pk_lookup:
            if op != '=':
                raise QueryException('Only = is supported for primary key lookup')

            try:
                pk = int(value_string_or_filter_name)
            except ValueError:
                pk = value_string_or_filter_name  # pk might be non-int

            if filter.pk_lookup_to_q:
                return filter.invoke_callback(filter.pk_lookup_to_q, pk=pk)
            else:
                if filter.attr is not None:
                    return Q(**{f'{filter.attr}__pk': pk})
                else:
                    return Q(pk=pk)

        if (
            isinstance(value_string_or_filter_name, str)
            and not isinstance(value_string_or_filter_name, StringValue)
            and value_string_or_filter_name.lower() in self.filters
        ):
            value_string_or_f = F(self.filters[value_string_or_filter_name.lower()].attr)
        else:
            value_string_or_f = value_string_or_filter_name
        try:
            result = filter.invoke_callback(filter.value_to_q, op=op, value_string_or_f=value_string_or_f)
        except ValidationError as e:
            raise QueryException(f'{e.message}')
        except ValueError as e:
            raise QueryException(f'Invalid value for filter "{query_name}": {e}')
        if result is None:
            raise QueryException(f'Unknown value "{value_string_or_f}" for filter "{query_name}"')
        return result

    def _freetext_to_q(self, token):
        if all(not v.freetext for v in values(self.filters)):
            raise QueryException('There are no freetext filters available')
        assert len(token) == 1
        token = token[0].strip('"')

        return reduce(
            operator.or_,
            [
                Q(**{filter.attr + '__' + filter.query_operator_to_q_operator(':'): token})
                for filter in values(self.filters)
                if filter.freetext
            ],
        )

    def get_query_string(self):
        """
        Based on the data in the request, return the equivalent query string that you can use with parse_query_string() to create a query set.
        """
        form = self.form
        request = self.get_request()

        if request is None:
            return ''

        if self.query_advanced_value:
            return self.query_advanced_value
        elif form.is_valid():

            def expr(field, is_list, value):
                if is_list:
                    return '(' + ' OR '.join([expr(field, is_list=False, value=x) for x in field.value]) + ')'
                return build_query_expression(filter=self.filters[field._name], value=value)

            result = [
                expr(field, field.is_list, field.value)
                for field in values(form.fields)
                if field._name != FREETEXT_SEARCH_NAME
                and field._name in self.filters
                and field.value not in (None, '', [])
            ]

            if FREETEXT_SEARCH_NAME in form.fields:
                freetext = form.fields[FREETEXT_SEARCH_NAME].value
                if freetext:
                    result.append(
                        '(%s)'
                        % ' or '.join(
                            [
                                f'{filter.query_name}:{to_string_surrounded_by_quote(freetext)}'
                                for filter in values(self.filters)
                                if filter.freetext
                            ]
                        )
                    )
                    assert result[-1] != '()'
            return ' and '.join(result)
        else:
            return ''

    def get_q(self):
        """
        Create a query set based on the data in the request.
        """
        try:
            return self.parse_query_string(self.get_query_string())
        except QueryException as e:
            self.query_error = str(e)
            raise

    def _lowercase_filters(self):
        if not hasattr(self, '_lowercase_filters_cache'):
            self._lowercase_filters_cache = {k.lower(): v for k, v in items(self.filters)}
        return self._lowercase_filters_cache

    @classmethod
    @dispatch()
    def filters_from_model(cls, **kwargs):
        return create_members_from_model(
            member_class=cls.get_meta().member_class,
            **kwargs,
        )

    @classmethod
    @dispatch()
    def _from_model(cls, *, rows=None, model=None, include=None, exclude=None, default_included=False):
        assert rows is None or isinstance(rows, QuerySet), (
            'auto__rows needs to be a QuerySet for filter generation to work. '
            'If it needs to be a lambda, provide a model with auto__model for filter generation, '
            'and pass the lambda as rows.'
        )

        model, rows = model_and_rows(model, rows)
        assert model is not None or rows is not None, "auto__model or auto__rows must be specified"
        filters = cls.filters_from_model(model=model, include=include, exclude=exclude, default_included=default_included)
        return model, rows, filters
