import re
from contextlib import contextmanager
from datetime import datetime
from decimal import (
    Decimal,
    InvalidOperation,
)
from functools import reduce
from itertools import groupby
from operator import or_
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

from django.core.exceptions import ObjectDoesNotExist
from django.db import (
    IntegrityError,
    models,
)
from django.db.models import (
    Case,
    IntegerField,
    Model,
    Q,
    QuerySet,
    When,
)
from django.http.response import HttpResponseBase
from django.template import Context
from django.utils.functional import Promise
from django.utils.translation import gettext

from iommi.endpoint import DISPATCH_PREFIX
from iommi.struct import Struct

from iommi._db_compat import field_defaults_factory
from iommi._web_compat import (
    csrf,
    format_html,
    HttpResponseRedirect,
    render_template,
    Template,
    URLValidator,
    validate_email,
    ValidationError,
)
from iommi.action import (
    Action,
    Actions,
    group_actions,
)
from iommi.attrs import Attrs
from iommi.base import (
    build_as_view_wrapper,
    capitalize,
    get_display_name,
    items,
    MISSING,
    NOT_BOUND_MESSAGE,
    values,
)
from iommi.datetime_parsing import (
    parse_relative_date,
    parse_relative_datetime,
)
from iommi.declarative import declarative
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    flatten,
    getattr_path,
    Namespace,
    setattr_path,
    setdefaults_path,
)
from iommi.shortcut import Shortcut
from iommi.declarative.with_meta import with_meta
from iommi.error import Errors
from iommi.evaluate import (
    evaluate,
    evaluate_strict,
)
from iommi.fragment import (
    build_and_bind_h_tag,
    Fragment,
    Header,
    Tag,
)
from iommi.from_model import (
    AutoConfig,
    create_members_from_model,
    get_search_fields,
    member_from_model,
    NoRegisteredSearchFieldException,
)
from iommi.member import (
    bind_members,
    refine_done_members,
)
from iommi.page import (
    Page,
)
from iommi.part import (
    Part,
    request_data,
)
from iommi.refinable import (
    evaluated_refinable,
    EvaluatedRefinable,
    Prio,
    Refinable,
    refinable,
    RefinableMembers,
    SpecialEvaluatedRefinable,
)
from iommi.shortcut import with_defaults
from iommi.sort_after import sort_after

# Prevent django templates from calling That Which Must Not Be Called
Namespace.do_not_call_in_templates = True

FULL_FORM_FROM_REQUEST = 'full_form_from_request'  # pragma: no mutate The string is just to make debugging nice
INITIALS_FROM_GET = 'initials_from_get'  # pragma: no mutate The string is just to make debugging nice


@contextmanager
def validation_errors_reported_on(obj):
    try:
        yield
    except ValidationError as e:
        for msg in e.messages:
            obj.add_error(msg)


def bool_parse(string_value, **_):
    s = string_value.lower()
    if s in ('1', 'true', 't', 'yes', 'y', 'on'):
        return True
    elif s in ('0', 'false', 'f', 'no', 'n', 'off'):
        return False
    else:
        raise ValueError('%s is not a valid boolean value' % string_value)


def many_to_many_factory_read_from_instance(field, instance):
    return getattr_path(instance, field.attr).all()


def many_to_many_factory_write_to_instance(field, instance, value):
    getattr_path(instance, field.attr).set(value or [])


_field_factory_by_field_type = {}


def register_field_factory(django_field_class, *, shortcut_name=MISSING, factory=MISSING, **kwargs):
    assert shortcut_name is not MISSING or factory is not MISSING
    if factory is MISSING:
        factory = Shortcut(call_target__attribute=shortcut_name, **kwargs)
    else:
        assert not kwargs, 'Can not provide both a factory and additional defaults separately'

    _field_factory_by_field_type[django_field_class] = factory


def create_object__post_handler(*, form, **kwargs):
    return create_or_edit_object__post_handler(form=form, is_create=True, **kwargs)


def edit_object__post_handler(*, form, **kwargs):
    return create_or_edit_object__post_handler(form=form, is_create=False, **kwargs)


def find_unique_prefixes(attributes):
    result = set()
    for attribute in attributes:
        prefix, _, _ = attribute.rpartition('__')
        parts = prefix.split('__')
        for i in range(len(parts)):
            result.add(tuple(parts[: i + 1]))
    return ['__'.join(p) for p in sorted(sorted(result), key=len)]


def save_nested_forms(form, request, **_):
    did_fail = False
    for nested_form in form.nested_forms.values():
        for action in nested_form.actions.values():
            if action.post_handler is None:
                continue
            if action.post_handler and action.invoke_callback(action.post_handler) is None:
                did_fail = True

    if not did_fail:
        if 'post_save' in form.extra:
            form.invoke_callback(form.extra.post_save)

        request.method = 'GET'

        redirect_to = form.extra.get('redirect_to', lambda **_: request.POST.get('next', '.'))
        target = form.invoke_callback(redirect_to)
        assert isinstance(target, str), 'redirect_to must return a str'
        return HttpResponseRedirect(target)


def create_or_edit_object__post_handler(*, form, is_create, **_):
    if not form.is_valid():
        return

    if is_create:
        assert form.instance is None
        form.instance = form.invoke_callback(form.extra.new_instance)

        # `own_evaluate_parameters` can't be used here because it is calculated too early when the instance doesn't exist yet. So instead we have to insert it manually when we get it.
        # noinspection PyProtectedMember
        form._evaluate_parameters['instance'] = form.instance

        for field in values(form.fields):
            # two phase save for creation in django, have to save main object before related stuff
            if not field.extra.get('django_related_field', False):
                form.apply_field(field=field, instance=form.instance)

        with validation_errors_reported_on(form):
            form.instance.validate_unique()
            if hasattr(form.instance, 'validate_constraints'):
                form.instance.validate_constraints()
        if not form.is_valid():
            return

        # two phase save for creation in django...
        form.invoke_callback(form.extra.pre_save_all_but_related_fields)
        form.instance.save()
        form.invoke_callback(form.extra.on_save_all_but_related_fields)

    form.apply(form.instance)

    if not is_create:
        with validation_errors_reported_on(form):
            form.instance.validate_unique()
            if hasattr(form.instance, 'validate_constraints'):
                form.instance.validate_constraints()
        if not form.is_valid():
            return

    attributes = filter(None, [f.attr for f in form.fields.values()])

    form.invoke_callback(form.extra.pre_save)
    for prefix in find_unique_prefixes(attributes):
        model_object = form.instance
        if prefix:  # Might be ''
            model_object = getattr_path(model_object, prefix)
        model_object.save()
    form.invoke_callback(form.extra.on_save)

    return create_or_edit_object_redirect(
        is_create, form.extra.redirect_to, form.extra.redirect, form
    )


def default_endpoints__config(field: 'Field', **_) -> dict:
    return dict(
        name=field._name,
    )


def default_endpoints__validate(field: 'Field', **_) -> dict:
    return dict(
        valid=not bool(field._errors),
        errors=list(field._errors),
    )


def float_parse(string_value: str, **_):
    try:
        return float(string_value)
    except ValueError:
        # Acrobatics so we get equal formatting in python 2/3
        raise ValueError("could not convert string to float: %s" % string_value)


def int_parse(string_value, **_):
    return int(string_value)


def choice_is_valid(field, parsed_data, **_):
    return parsed_data in field.choices, f'{parsed_data} not in available choices'


def choice_parse(form, field, string_value):
    for choice in field.choices:
        if string_value == field.invoke_callback(field.choice_id_formatter, choice=choice):
            return choice

    if string_value in [None, '']:
        return None

    return string_value


def choice_queryset__is_valid(field, parsed_data, **_):
    return (
        field.choices.filter(pk=parsed_data.pk).exists(),
        f'{", ".join(field.raw_data) if field.is_list else field.raw_data} not in available choices',
    )


def choice_queryset__endpoint_handler(*, form, field, value, page_size=40, **_):
    from django.core.paginator import (
        EmptyPage,
        Paginator,
    )

    page = int(form.get_request().GET.get('page', 1))
    choices = field.extra.filter_and_sort(form=form, field=field, value=value)
    try:
        paginator = Paginator(choices, page_size)
        result = paginator.page(page)
        has_more = result.has_next()
    except EmptyPage:
        result = []
        has_more = False

    return dict(
        results=field.extra.model_from_choices(form, field, result),
        page=page,
        pagination=dict(
            more=has_more,
        ),
    )


def choice_queryset__extra__model_from_choices(form, field, choices):
    def traverse():
        for choice in choices:
            yield Struct(
                id=field.invoke_callback(field.choice_id_formatter, choice=choice),
                text=field.invoke_callback(field.choice_display_name_formatter, choice=choice),
            )

    return list(traverse())


def choice_queryset__extra__filter_and_sort(field, value, **_):
    assert field.search_fields is not None, f'There are no search_fields specified for {field._name}'
    assert isinstance(field.search_fields, (tuple, list))
    if not value:
        return field.choices.order_by(*field.search_fields)

    q_objects = []

    def create_q_objects(suffix):
        q_objects.extend([Q(**{search_field + suffix: value}) for search_field in field.search_fields])

    create_q_objects(suffix='')
    create_q_objects(suffix='__istartswith')
    create_q_objects(suffix='__icontains')

    when_clauses = [When(q, then=rank) for rank, q in enumerate(q_objects)]
    choices = field.choices.annotate(
        iommi_ranking=Case(*when_clauses, default=len(q_objects) + 1, output_field=IntegerField())
    )

    return choices.filter(reduce(or_, q_objects)).order_by('iommi_ranking', *field.search_fields)


def choice_queryset__parse(field, string_value, **_):
    try:
        return field.choices.get(pk=string_value) if string_value else None
    except field.model.DoesNotExist as e:
        raise ValidationError(str(e))


datetime_iso_formats = [
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d %H',
]


def datetime_parse(string_value, **_):
    for iso_format in datetime_iso_formats:
        try:
            return datetime.strptime(string_value, iso_format)
        except ValueError:
            pass
    result = parse_relative_datetime(string_value)
    if result is None:
        formats = ', '.join('"%s"' % x for x in datetime_iso_formats)
        raise ValidationError(
            f'Time data "{string_value}" does not match any of the formats "now", {formats}, and is not a relative date like "2d" or "2 weeks ago"'
        )
    return result


def datetime_render_value(value, **_):
    return value.strftime(datetime_iso_formats[0]) if value else ''


date_iso_format = '%Y-%m-%d'


def date_parse(string_value, **_):
    extra_information = ''
    try:
        return datetime.strptime(string_value, date_iso_format).date()
    except ValueError as e:
        if 'out of range' in str(e) or 'unconverted data remains' in str(e):
            extra_information = ' (out of range)'

    result = parse_relative_date(string_value)
    if result is None:
        formats = ', '.join('"%s"' % x for x in datetime_iso_formats)
        raise ValidationError(
            f'Time data "{string_value}" does not match any of the formats "now", {formats}, and is not a relative date like "2d" or "2 weeks ago"{extra_information}'
        )
    return result


def date_render_value(value, **_):
    return value.strftime(date_iso_format) if value else ''


time_iso_formats = [
    '%H:%M:%S',
    '%H:%M',
    '%H',
]


def time_parse(string_value, **_):
    if string_value.lower() == 'now':
        return datetime.now().time()
    for time_iso_format in time_iso_formats:
        try:
            return datetime.strptime(string_value, time_iso_format).time()
        except ValueError:
            pass
    formats = ', '.join('"%s"' % x for x in time_iso_formats)
    raise ValidationError(f'Time data "{string_value}" does not match any of the formats "now" or {formats}')


def time_render_value(value, **_):
    return value.strftime(time_iso_formats[0]) if value else ''


def decimal_parse(string_value, **_):
    try:
        return Decimal(string_value)
    except InvalidOperation:
        raise ValidationError(f"Invalid literal for Decimal: '{string_value}'")


def url_parse(string_value, **_):
    return URLValidator()(string_value) or string_value


def file_write_to_instance(field, instance, value):
    if value:
        Field.write_to_instance(field=field, instance=instance, value=value)


def email_parse(string_value, **_):
    return validate_email(string_value) or string_value


def phone_number_is_valid(parsed_data, **_):
    return (
        re.match(r'^\+\d{1,3}(([ \-])?\(\d+\))?(([ \-])?\d+)+$', parsed_data, re.IGNORECASE),
        'Please use format +<country code> (XX) XX XX. Example of US number: +1 (212) 123 4567 or +1 212 123 4567',
    )


def default_input_id(field, **_):
    return f'id_{field.iommi_path.replace("/", "__")}'


def file__raw_data(form, field, **_):
    request = form.get_request()
    if field.iommi_path not in request.FILES:
        return None
    return request.FILES[field.iommi_path]


def boolean_tristate__parse(string_value, **_):
    if not string_value:
        return None
    return bool_parse(string_value)


def render_fragment(fragment):
    if fragment is None:
        return ''

    return str(fragment)


@with_meta
class Field(Part, Tag):
    # language=rst
    """
    Class that describes a field, i.e. what input controls to render, the label, etc.

    See :doc:`Form` for more complete examples.

    The life cycle of the data is:

        1. `raw_data`: will be set if the corresponding key is present in the HTTP request
        2. `parsed_data`: set if parsing is successful, which only happens if the previous step succeeded
        3. `value`: set if validation is successful, which only happens if the previous step succeeded

    """

    tag: str = EvaluatedRefinable()
    attr: str = EvaluatedRefinable()
    display_name: str = EvaluatedRefinable()

    # raw_data/raw_data contains the strings grabbed directly from the request data
    # It is useful that they are evaluated for example when doing file upload. In that case the data is on request.FILES, not request.POST so we can use this to grab it from there
    raw_data: str = Refinable()  # raw_data is evaluated, but in a special way

    parse_empty_string_as_none: bool = EvaluatedRefinable()
    # parsed_data/parsed_data contains data that has been interpreted, but not checked for validity or access control
    parsed_data: Any = SpecialEvaluatedRefinable()

    initial: Any = SpecialEvaluatedRefinable()
    template: Union[str, Template] = EvaluatedRefinable()

    attrs: Attrs = SpecialEvaluatedRefinable()
    required: bool = EvaluatedRefinable()

    input: Fragment = Refinable()
    label: Fragment = Refinable()
    non_editable_input: Fragment = Refinable()
    help: Fragment = Refinable()

    is_list: bool = EvaluatedRefinable()
    is_boolean: bool = EvaluatedRefinable()
    model: Optional[Type[Model]] = SpecialEvaluatedRefinable()
    model_field: Optional[models.Field] = Refinable()
    model_field_name = Refinable()

    editable: bool = EvaluatedRefinable()
    strip_input: bool = EvaluatedRefinable()

    choices: Callable[..., List[Any]] = SpecialEvaluatedRefinable()
    choice_id_formatter: Callable[..., str] = Refinable()
    choice_display_name_formatter: Callable[..., str] = Refinable()
    choice_to_optgroup: Optional[Callable[..., Optional[str]]] = Refinable()

    search_fields = Refinable()
    errors: Errors = Refinable()

    empty_label: str = EvaluatedRefinable()

    group: str = EvaluatedRefinable()

    class Meta:
        attrs__class = EMPTY
        attrs__style = EMPTY
        errors = EMPTY

    @with_defaults(
        tag='div',
        input__attrs__type='text',
        input__tag='input',
        label__tag='label',
        help__attrs__class__helptext=True,
        help__tag='div',
        attr=MISSING,
        display_name=MISSING,
        parse_empty_string_as_none=True,
        required=True,
        is_list=False,
        is_boolean=False,
        editable=True,
        strip_input=True,
        endpoints__config__func=default_endpoints__config,
        endpoints__validate__func=default_endpoints__validate,
        label__call_target=Fragment,
        label__attrs__for=default_input_id,
        help__call_target=Fragment,
        input__call_target=Fragment,
        input__attrs__id=default_input_id,
        input__attrs__name=lambda field, **_: field.iommi_path,
        input__extra__placeholder='',
        non_editable_input=dict(
            call_target=Fragment,
            children__text=lambda fragment, field, **_: None if fragment.tag == 'input' else field.rendered_value,
            attrs__value=lambda fragment, field, **_: field.rendered_value if fragment.tag == 'input' else None,
            attrs__disabled=lambda fragment, field, **_: True if fragment.tag == 'input' else None,
        ),
        initial=MISSING,
        choice_to_optgroup=None,
        choice_id_formatter=lambda choice, **_: '%s' % choice,
        choice_display_name_formatter=lambda choice, **_: '%s' % choice,
        group=MISSING,
        empty_label='---',
    )
    def __init__(self, **kwargs):
        # language=rst
        """
        Note that, in addition to the parameters with the defined behavior below, you can pass in any keyword argument you need yourself, including callables that conform to the protocol, and they will be added and evaluated as members.

        All these parameters can be callables, and if they are, will be evaluated with the keyword arguments form and field. The only exceptions are `is_valid` (which gets `form`, `field` and `parsed_data`), `render_value` (which takes `form`, `field` and `value`) and `parse` (which gets `form`, `field`, `string_value`). Example of using a lambda to specify a value:

        .. code-block:: python

                Field(attrs__id=lambda form, field: 'my_id_%s' % field._name)

        :param after: Set the order of columns, see the `howto <https://docs.iommi.rocks/en/latest/cookbook_forms.html#how-do-i-change-the-order-of-the-fields>`_ for an example.
        :param initial: Initial value of the field
        :param attr: The attribute path to apply or get the data from. For example using `foo__bar__baz` will result in `your_instance.foo.bar.baz` will be set by the `apply()` function. Defaults to same as name
        :param attrs: A dict containing any custom html attributes to be sent to the `input__template`.
        :param display_name: The text in the HTML label tag. Default: `capitalize(name).replace('_', ' ')`
        :param template: Django template filename or `Template` instance for the entire row. Normally you shouldn't need to override on this level. Prefer overriding `input__template`, `label__template` or `error__template` as needed.
        :param input__template: Django template filename or `Template` instance for the template for just the input control.
        :param label__template: Django template filename or `Template` instance for the template for just the label tab.
        :param required: If the field is a required field. Default: `True`
        :param help_text: The help text will be grabbed from the django model if specified and available.

        :param editable: Is this field editable.
        :param strip_input: Runs the input data through standard python .strip() before passing it to the parse function (can NOT be callable). Default: `True`
        :param is_list: Interpret request data as a list (can NOT be a callable). Default: `False``
        :param read_from_instance: Callback to retrieve value from edited instance. Invoked with parameters field and instance.
        :param write_to_instance: Callback to write value to instance. Invoked with parameters field, instance and value.
        :param choice_id_formatter: Callback given the keyword argument `choice` in addition to standard parameters, to obtain the string value to represent the identity of a given `choice`. Default implementation will use `str(choice)`
        :param choice_display_name_formatter: Callback given the keyword argument `choice` in addition to standard parameters, to obtain the display name representing a given choice to the end user. Default implementation will use `str(choice)`
        :param choice_to_optgroup Callback to generate the optgroup for the given choice. It will get the keyword argument `choice`. It should return None if the choice should not be grouped.
        """
        super(Field, self).__init__(**kwargs)

    def on_refine_done(self):
        if 'choice' in getattr(self, 'iommi_shortcut_stack', []):
            assert (
                self.iommi_namespace.get('choices') is not None
            ), 'To use Field.choice, you must pass the choices list'

        model_field = self.model_field
        if model_field and model_field.remote_field:
            self.model = model_field.remote_field.model
        elif isinstance(self.model, SpecialEvaluatedRefinable):
            self.model = None

        # value/value_data_list is the final step that contains parsed and valid data
        self.value = None

        self.non_editable_input = Namespace(
            {
                **flatten(self.input),
                **self.non_editable_input,
                '_name': 'non_editable_input',
            }
        )().refine_done(parent=self)
        self.input = self.input(_name='input').refine_done(parent=self)
        self.label = self.label(_name='label').refine_done(parent=self)
        self.help = self.help(_name='help').refine_done(parent=self)
        self._parsed_data = self.parsed_data
        self._raw_data = self.raw_data

        super(Field, self).on_refine_done()

    @property
    def form(self):
        return self.iommi_evaluate_parameters()['form']

    # noinspection PyUnusedLocal
    @staticmethod
    @refinable
    def is_valid(form: 'Form', field: 'Field', parsed_data: Any, **_) -> Tuple[bool, str]:
        # language=rst
        """
        Validation function. Should return a tuple of `(bool, reason_for_failure_if_bool_is_false)` or raise ValidationError.

        .. code-block:: python

            form = Form.create(
                auto__model=Artist,
                fields__name__is_valid=lambda parsed_data, **_: (parsed_data.startswith('H'), 'Must start with H!'),
            )

            # @test
            show_output(form.bind(request=req('post', **{'-submit': '', 'name': 'blizzard of ozz'})))
            # @end
        """

        return True, ''

    # noinspection PyUnusedLocal
    @staticmethod
    @refinable
    def parse(form: 'Form', field: 'Field', string_value: str, **_) -> Any:
        # language=rst
        """
        Parse function. Default just returns the string input unchanged. This function can raise `ValueError` or `ValidationError` to produce a field error message.
        """

        del form, field
        return string_value

    @staticmethod
    @refinable
    def post_validation(form: 'Form', field: 'Field', **_) -> None:
        pass

    @staticmethod
    @refinable
    def render_value(form: 'Form', field: 'Field', value: Any, **kwargs) -> str:
        # language=rst
        """
        Render the parsed and validated value into a string. Default just converts to `str`.

        .. code-block:: python

            sentinel = '!!custom!!'
            form = Form(
                fields__foo=Field(
                    initial='not sentinel value',
                    render_value=lambda form, field, value, **_: sentinel,
                )
            )

            # @test
            show_output(form)
            assert sentinel in form.bind(request=req('get')).__html__()
            # @end
        """

        if isinstance(value, (list, QuerySet)):
            return ', '.join(field.render_value(form=form, field=field, value=v, **kwargs) for v in value)
        else:
            return f'{value}' if value is not None else ''

    # grab help_text from model if applicable
    # noinspection PyProtectedMember
    @staticmethod
    @evaluated_refinable
    def help_text(field, **_):
        if field.model_field is None:
            return ''
        return field.model_field.help_text or ''

    @staticmethod
    @refinable
    def read_from_instance(field: 'Field', instance: Any) -> Any:
        return getattr_path(instance, field.attr)

    @staticmethod
    @refinable
    def write_to_instance(field: 'Field', instance: Any, value: Any) -> None:
        setattr_path(instance, field.attr, value)

    def add_error(self, msg):
        assert msg
        self._errors.add(msg)
        self.form._valid = False

    def bind_from_instance(self):
        self.raw_data = self._raw_data
        self.parsed_data = self._parsed_data
        self._errors = set()
        self.choices = evaluate_strict(self.choices, **self.iommi_evaluate_parameters())
        self.editable = evaluate_strict(self.editable, **self.iommi_evaluate_parameters())
        self.initial = evaluate_strict(self.initial, **self.iommi_evaluate_parameters())
        self._read_initial()

        if not self.editable:
            self.value = self.initial
        else:
            self._read_raw_data()

            self.parsed_data = evaluate_strict(self.parsed_data, **self.iommi_evaluate_parameters())
            self._parse()

            self._validate()

        if self.editable:
            self.input = self.input.bind(parent=self)
        else:
            self.input = self.non_editable_input.bind(parent=self)

        if self.is_boolean:
            if 'checked' not in self.input.attrs and self.value:
                self.input.attrs.checked = ''
                self.input.attrs.pop('value', None)
        else:
            if 'value' not in self.input.attrs:
                self.input.attrs.value = self.rendered_value

    def on_bind(self) -> None:
        self._errors: Set[str] = set()

        form = self.form
        assert form is not None, "Each field needs a form."

        form.all_fields[self._name] = self

        if self.attr is MISSING:
            self.attr = self._name
        if self.display_name is MISSING:
            self.display_name = get_display_name(self)

        self.errors = Errors(parent=self, **self.errors)

        if not form.editable:
            self.editable = False

        # Not strict evaluate on purpose
        self.model = evaluate(self.model, **self.iommi_evaluate_parameters())

        self.bind_from_instance()

        self.label = self.label.bind(parent=self)
        if self.label is not None:
            assert not self.label.children
            self.label.children = dict(text=evaluate_strict(self.display_name, **self.iommi_evaluate_parameters()))
        if self.display_name is None:
            self.label = None

        self.non_editable_input = self.non_editable_input.bind(parent=self)

        self.help = self.help.bind(parent=self)
        if self.help is not None:
            help_text = evaluate_strict(self.help_text, **self.iommi_evaluate_parameters())
            self.help.children = dict(text=help_text)
        else:
            help_text = ''
        if not help_text:
            # To render cleanly in templates:
            self.help = ''

        if self.model and self.include and not self.search_fields:
            try:
                self.search_fields = get_search_fields(model=self.model)
            except NoRegisteredSearchFieldException:
                self.search_fields = ['pk']

    def _parse(self):
        if self.parsed_data is not None:
            return

        if self.form.mode is INITIALS_FROM_GET and self.raw_data is None:
            return

        if self.is_list:
            if self.raw_data is not None:
                self.parsed_data = [self._parse_raw_value(x) for x in self.raw_data]
            else:
                self.parsed_data = None
        elif self.is_boolean:
            self.parsed_data = self._parse_raw_value('0' if self.raw_data is None else self.raw_data)
        else:
            if self.raw_data == '' and self.parse_empty_string_as_none:
                self.parsed_data = None
            elif self.raw_data is not None:
                self.parsed_data = self._parse_raw_value(self.raw_data)
            else:
                self.parsed_data = None

    def _parse_raw_value(self, raw_data):
        with validation_errors_reported_on(self):
            try:
                return self.parse(form=self.form, field=self, string_value=raw_data)
            except ValueError as e:
                msg = str(e)
                assert msg != ''
                self.add_error(msg)

    def _validate(self):
        form = self.form
        if form.mode is INITIALS_FROM_GET and (self.raw_data is None or (self.raw_data == [] and self.is_list)):
            self.value = self.initial
            return

        value = None
        if self.is_list:
            if self.parsed_data is not None:
                value = [self._validate_parsed_data(x) for x in self.parsed_data if x is not None]
        else:
            if self.parsed_data is not None:
                value = self._validate_parsed_data(self.parsed_data)

        if not self._errors:
            if (
                form.mode is FULL_FORM_FROM_REQUEST
                and self.required
                and (value == [] if self.is_list else value in [None, ''])
            ):
                self.add_error(gettext('This field is required'))
            else:
                self.value = value
        else:
            assert self.form._valid is False

    def _validate_parsed_data(self, value):
        is_valid, error = self.is_valid(form=self.form, field=self, parsed_data=value)
        if is_valid and not self.errors and self.parsed_data is not None and not self.is_list:
            value = self.parsed_data
        elif not is_valid and self.form.mode:
            if not isinstance(error, set):
                error = {error}
            for e in error:
                self.add_error(e)
        return value

    def _read_initial(self):
        form = self.form
        if self.initial is MISSING and self.include and self.attr:
            if form.instance is not None:
                self.initial = self.read_from_instance(self, form.instance)
            elif form.model is not None:
                try:
                    self.initial = self.read_from_instance(self, form.model())
                except (ObjectDoesNotExist, AttributeError, ValueError):
                    pass

        if self.initial is MISSING:
            self.initial = None

    def _read_raw_data(self):
        # The client might have refined raw_data. If so evaluate it.
        if self.raw_data is not None:
            self.raw_data = evaluate_strict(self.raw_data, **self.iommi_evaluate_parameters())
            if self.raw_data is not None:
                return

        # Otherwise get it from the request
        form = self.form

        if self.is_list:
            try:
                # django and similar
                # noinspection PyUnresolvedReferences
                raw_data = form._request_data.getlist(self.iommi_path)
            except AttributeError:  # pragma: no cover
                # werkzeug and similar
                raw_data = form._request_data.get(self.iommi_path)

            if raw_data and self.strip_input:
                raw_data = [x.strip() for x in raw_data]

            if raw_data is not None:
                self.raw_data = raw_data
        else:
            self.raw_data = form._request_data.get(self.iommi_path)
            if self.raw_data and self.strip_input:
                self.raw_data = self.raw_data.strip()

    def own_evaluate_parameters(self):
        return dict(field=self)

    def get_errors(self):
        return self._errors

    @property
    def rendered_value(self):
        if self.errors:
            return self.raw_data
        return self.invoke_callback(self.render_value, value=self.value)

    def _build_option(self, choice):
        # The legacy structure is `(choice, id, display_name, is_selected)`
        return (
            choice,
            self.invoke_callback(self.choice_id_formatter, choice=choice),
            self.invoke_callback(self.choice_display_name_formatter, choice=choice),
            ((choice == self.value) if not self.is_list else (self.value is not None and choice in self.value)),
        )

    @property
    def choice_to_options_selected(self):
        if self.value is None:
            return []

        if self.is_list:
            return [self._build_option(v) for v in self.value]
        else:
            return [self._build_option(self.value)]

    @property
    def choice_tuples(self):
        result = []
        if not self.required and not self.is_list:
            result.append(
                # choice, id, display_name, selected, index
                (None, '', (self.empty_label), (not bool(self.value)), 0)
            )
        for i, choice in enumerate(self.choices):
            result.append(self._build_option(choice) + (i + 1,))

        return result

    @property
    def grouped_choice_tuples(self):
        if self.choice_to_optgroup is None:
            return [(None, self.choice_tuples)]
        else:
            groups = []
            current_group_name = None
            current_group = []
            groups.append((current_group_name, current_group))
            for choice_tuple in self.choice_tuples:
                choice = choice_tuple[0]
                group_name = self.invoke_callback(self.choice_to_optgroup, choice=choice)
                if current_group_name != group_name:
                    current_group_name = group_name
                    current_group = []
                    groups.append((current_group_name, current_group))
                current_group.append(choice_tuple)
            return groups

    @classmethod
    def from_model(cls, model=None, model_field_name=None, model_field=None, **kwargs):
        return member_from_model(
            cls=cls,
            model=model,
            factory_lookup=_field_factory_by_field_type,
            factory_lookup_register_function=register_field_factory,
            defaults_factory=field_defaults_factory,
            model_field_name=model_field_name,
            model_field=model_field,
            **kwargs,
        )

    @dispatch(
        render=EMPTY,
    )
    def __html__(self, *, render=None):
        assert not render
        if self.template:
            return render_template(self.get_request(), self.template, self.iommi_evaluate_parameters())

        f = Fragment(
            _name=self._name,
            tag=self.tag,
            attrs=self.attrs,
        ).bind(parent=self._parent)

        f.children['label'] = self.label
        f.children['input'] = self.input
        f.children['help'] = self.help
        f.children['errors'] = self.errors

        f.children = sort_after(f.children)

        return f.__html__()

    @classmethod
    @with_defaults(
        input__attrs__type='hidden',
        attrs__style__display='none',
    )
    def hidden(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        input__attrs__type='text',
    )
    def text(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        input__tag='textarea',
        input__attrs__type=None,
        input__attrs__value=None,
        input__children__text=lambda field, **_: field.rendered_value,
        input__attrs__readonly=lambda field, **_: True if field.editable is False else None,
    )
    def textarea(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults
    def number(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        parse=int_parse,
    )
    def integer(cls, **kwargs):
        return cls.number(**kwargs)

    @classmethod
    @with_defaults(
        parse=float_parse,
    )
    def float(cls, **kwargs):
        return cls.number(**kwargs)

    @classmethod
    @with_defaults(
        input__attrs__type='password',
    )
    def password(cls, **kwargs):
        return cls(**kwargs)

    # Boolean field. Tries hard to parse a boolean value from its input.
    @classmethod
    @with_defaults(
        parse=bool_parse,
        required=False,
        is_boolean=True,
    )
    def boolean(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        required=True,
        is_list=False,
        is_valid=choice_is_valid,
        input__attrs__multiple=lambda field, **_: True if field.is_list else None,
        parse=choice_parse,
    )
    def choice(cls, **kwargs):
        """
        Shortcut for single choice field. If required is false it will automatically add an option first with the value '' and the title '---'. To override that text pass in the parameter empty_label.
        """
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        choices=[True, False],
        choice_id_formatter=lambda choice, **_: 'true' if choice else 'false',
        choice_display_name_formatter=lambda choice, **_: gettext('Yes') if choice else gettext('No'),
        parse=boolean_tristate__parse,
        required=False,
    )
    def boolean_tristate(cls, **kwargs):
        return cls.choice(**kwargs)

    @classmethod
    @with_defaults(
        parse=choice_queryset__parse,
        choice_id_formatter=lambda choice, **_: choice.pk,
        endpoints__choices__func=choice_queryset__endpoint_handler,
        is_valid=choice_queryset__is_valid,
        extra__filter_and_sort=choice_queryset__extra__filter_and_sort,
        extra__model_from_choices=choice_queryset__extra__model_from_choices,
    )
    def choice_queryset(cls, choices: QuerySet = None, **kwargs):
        if 'model' not in kwargs:
            if isinstance(choices, QuerySet):
                kwargs['model'] = choices.model
            elif 'model_field' in kwargs:
                pass
            else:
                assert (
                    False
                ), 'The convenience feature to automatically get the parameter model set only works for QuerySet instances or if you specify model_field'

        instance = cls.choice(**kwargs)
        instance = instance.refine(
            Prio.shortcut,
            choices=(
                (lambda form, **_: choices.all()) if isinstance(choices, QuerySet) else choices
            ),  # clone the QuerySet if needed
        )
        return instance

    @classmethod
    @with_defaults(
        is_list=True,
    )
    def multi_choice(cls, **kwargs):
        return cls.choice(**kwargs)

    @classmethod
    @with_defaults(
        is_list=True,
    )
    def multi_choice_queryset(cls, **kwargs):
        return cls.choice_queryset(**kwargs)

    @classmethod
    @with_defaults(
        input__attrs__id=None,
        extra_evaluated__id=default_input_id,
    )
    def radio(cls, **kwargs):
        return cls.choice(**kwargs)

    @classmethod
    @with_defaults(
        parse=datetime_parse,
        render_value=datetime_render_value,
    )
    def datetime(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        parse=date_parse,
        render_value=date_render_value,
    )
    def date(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        parse=time_parse,
        render_value=time_render_value,
    )
    def time(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        parse=decimal_parse,
    )
    def decimal(cls, **kwargs):
        return cls.number(**kwargs)

    @classmethod
    @with_defaults(
        input__attrs__type='url',
        parse=url_parse,
    )
    def url(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        input__attrs__type='file',
        raw_data=file__raw_data,
        write_to_instance=file_write_to_instance,
    )
    def file(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        template='iommi/form/image_row.html',
    )
    def image(cls, **kwargs):
        return cls.file(**kwargs)

    # Shortcut to create a fake input that performs no parsing but is useful to separate sections of a form.
    @classmethod
    @with_defaults(
        editable=False,
        attr=None,
    )
    def heading(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        editable=False,
        attr=None,
    )
    def info(cls, value, **kwargs):
        """
        Shortcut to create an info entry.
        """
        instance = cls(**kwargs)
        instance = instance.refine(
            Prio.shortcut,
            initial=value,
        )
        return instance

    @classmethod
    @with_defaults(
        input__attrs__type='email',
        parse=email_parse,
    )
    def email(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        is_valid=phone_number_is_valid,
    )
    def phone_number(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        template=Template(''),
        editable=False,
    )
    def non_rendered(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults
    def foreign_key(cls, model_field, model, **kwargs):
        del model
        setdefaults_path(
            kwargs,
            choices=model_field.foreign_related_fields[0].model.objects.all(),
        )
        return cls.choice_queryset(model_field=model_field, **kwargs)

    @classmethod
    @with_defaults(
        editable=False,
        display_name=lambda field, **_: capitalize(field.model_field.related_model._meta.verbose_name_plural),
        help_text=None,
    )
    def foreign_key_reverse(cls, *, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=lambda field, **_: field.model_field.remote_field.model.objects.all(),
            read_from_instance=lambda field, instance, **_: getattr_path(instance, field.attr).all(),
            extra__django_related_field=True,
        )
        return cls.multi_choice_queryset(model_field=model_field, **kwargs)

    @classmethod
    @with_defaults
    def many_to_many(cls, model_field, **kwargs):
        setdefaults_path(
            kwargs,
            choices=model_field.remote_field.model.objects.all(),
            read_from_instance=many_to_many_factory_read_from_instance,
            write_to_instance=many_to_many_factory_write_to_instance,
            extra__django_related_field=True,
        )
        return cls.multi_choice_queryset(model_field=model_field, **kwargs)

    @classmethod
    @with_defaults(
        display_name=lambda field, **_: capitalize(field.model_field.remote_field.model._meta.verbose_name_plural),
        help_text=None,
    )
    def many_to_many_reverse(cls, model_field, **kwargs):
        return cls.many_to_many(model_field=model_field, **kwargs)


def is_django_promise_with_string_proxy(redirect_to):
    return (
        isinstance(redirect_to, Promise)
        and redirect_to._proxy____kw == {}
        and len(redirect_to._proxy____args) == 1
        and isinstance(redirect_to._proxy____args[0], str)
    )


def create_or_edit_object_redirect(is_create, redirect_to, redirect, form):
    assert (
        redirect_to is None or isinstance(redirect_to, str) or is_django_promise_with_string_proxy(redirect_to)
    ), 'redirect_to must be a str'
    if redirect_to is None:
        if is_create:
            redirect_to = "../"
        else:
            redirect_to = (
                "../../"  # We guess here that the path ends with '<pk>/edit/' so this should end up at a good place
            )
    response = redirect(redirect_to=redirect_to, **form.iommi_evaluate_parameters())
    assert isinstance(response, HttpResponseBase), 'redirect must return a http response'
    return response


def delete_object__post_handler(form, **_):
    instance = form.instance
    form.invoke_callback(form.extra.on_delete)
    if instance.pk is not None:  # Check if already deleted by the callback
        try:
            instance.delete()
        except IntegrityError as e:
            objects = getattr(e, 'restricted_objects', None)
            if objects is None:
                objects = getattr(e, 'protected_objects', None)
            if objects is None:
                # This message must match the one in Django exactly to get translations for free
                form.add_error((gettext("Cannot delete %(name)s") % {"name": str(instance)}) + str(e))
                return

            # This message must match the one in Django exactly to get translations for free
            # language=html
            form.add_error(
                Template(
                    """
                        {% load i18n %}
                        <p>{% blocktrans with escaped_object=object %}Deleting the {{ object_name }} '{{ escaped_object }}' would require deleting the following protected related objects:{% endblocktrans %}</p>

                        <ul>
                            {% for obj in restricted_objects %}
                                <li>
                                    {% if obj.get_absolute_url %}
                                        <a href="{{ obj.get_absolute_url }}">{{ obj }}</a>
                                    {% else %}
                                        {{ obj }}
                                    {% endif %}
                                </li>
                            {% endfor %}
                        </ul>
                    """
                ).render(
                    context=Context(
                        dict(
                            restricted_objects=objects,
                            object=instance,
                            object_name=instance._meta.verbose_name,
                        )
                    )
                )
            )
            return None

    return create_or_edit_object_redirect(
        is_create=False,
        redirect_to=form.extra.redirect_to,
        redirect=form.extra.redirect,
        form=form,
    )


# noinspection PyUnreachableCode
if False:
    # These are needed to make makemessages collect these strings
    gettext('create')
    gettext('edit')
    gettext('delete')


class FormAutoConfig(AutoConfig):
    instance = Refinable()
    type = Refinable()  # one of 'create', 'edit', 'delete'


class FieldGroup(Fragment):
    group = Refinable()

    def own_evaluate_parameters(self):
        return dict(group=self.group, **super().own_evaluate_parameters())


@declarative(Part, '_fields_dict', add_init_kwargs=False)
@with_meta
class Form(Part):
    # language=rst
    """
    Describe a Form. Example:

    .. code-block:: python

        class MyForm(Form):
            a = Field()
            b = Field.email()

        form = MyForm().bind(request=request)

    You can also create an instance of a form with this syntax if it's more convenient:

    .. code-block:: python

        form = Form(
            fields=dict(
                a=Field(),
                b=Field.email(),
            ),
        ).bind(request=request)

    In the common case the fields namespace will contain only instances of `Field`, but
    iommi actually supports arbitrary `Part` objects. For example:

    .. code-block:: python

        form = Form(
            fields=dict(
                # Display a and b inside a box
                box=html.div(
                    attrs__class__box=True,
                    children__a=Field(),
                    children__b=Field.email(),
                ),
                # And c regularly
                c=Field(),
            )
        )

    So that writing the application logic (e.g. validation and post handlers) is independent
    of minor changes to the layout, after bind the `fields` namespace of the form will contain
    only instances of `Field` keyed by their `_name` independently of how deep they are in the
    hierarchy. Given the above, an appropriate post_handler would be:

    .. code-block:: python

        def post_handler(form, **_):
            if not form.is_valid():
                return

            print(form.fields.a.value, form.fields.b.value, form.fields.c.value)
            # And not:
            # print(form.fields.box.a.value, form.fields.box.b.value, form.fields.c.value)

        # @test
        post_handler(form.bind(request=req('post')))
        # @end
    """

    actions: Namespace = RefinableMembers()
    actions_template: Union[str, Template] = Refinable()
    # Only for nested forms: The attribute of the parent forms instance to use as this forms instance (default _name)
    attr: str = EvaluatedRefinable()
    attrs: Attrs = SpecialEvaluatedRefinable()
    editable: bool = Refinable()
    h_tag: Union[Fragment, str] = SpecialEvaluatedRefinable()
    title: Fragment = SpecialEvaluatedRefinable()
    template: Union[str, Template] = EvaluatedRefinable()
    errors: Errors = Refinable()

    model: Type[Model] = SpecialEvaluatedRefinable()
    member_class: Type[Field] = Refinable()
    action_class: Type[Action] = Refinable()
    page_class: Type[Page] = Refinable()
    auto: Namespace = Refinable()
    fields: Namespace = RefinableMembers()
    instance: Any = Refinable()
    field_group: Namespace = Refinable()

    class Meta:
        member_class = Field
        action_class = Action
        page_class = Page
        fields = EMPTY
        actions = EMPTY
        auto = EMPTY
        errors = EMPTY

    @with_defaults(
        model=None,
        instance=None,
        editable=True,
        attrs__action='',
        attrs__method='post',
        attrs__enctype='multipart/form-data',
        h_tag__call_target=Header,
        field_group__call_target=FieldGroup,
        template='iommi/form/form.html',
        actions_template='iommi/form/actions.html',
        attr=MISSING,
    )
    def __init__(self, **kwargs):
        super(Form, self).__init__(
            **kwargs,
        )

    def on_refine_done(self):
        extra_member_defaults = dict()
        if self.auto:
            auto = FormAutoConfig(**self.auto).refine_done(parent=self)
            assert (
                not self.model
            ), "You can't use the auto feature and explicitly pass model. Either pass auto__model, or we will set the model for you from auto__instance"
            if auto.model is None:
                auto.model = auto.instance.__class__

            model, fields_from_auto = self._from_model(
                model=auto.model,
                include=auto.include,
                exclude=auto.exclude,
                default_included=auto.default_included,
            )
            if auto.instance is not None:
                self.instance = auto.instance

            self.model = model
        else:
            fields_from_auto = None

        extra_action_defaults = Namespace()
        crud_type = self.extra.get('crud_type')
        if 'title' not in self.iommi_namespace and crud_type is not None:
            self.title = lambda form, **_: capitalize(
                gettext('%(crud_type)s %(model_name)s')
                % dict(
                    crud_type=gettext(crud_type),
                    model_name=(form.model or form.instance)._meta.verbose_name,
                )
            )
            extra_action_defaults = setdefaults_path(
                extra_action_defaults,
                submit__display_name=gettext('Save') if crud_type == 'edit' else capitalize(gettext(crud_type)),
            )

        # Submit is special.
        # We used to have an automatic action submit button. Now we instead if something is inj
        # the actions submit space assume you want to define it as a primary button (unless you
        # explicitly specify differently). That way we get no button if you don't explicitly opt
        # into it, by either directly defining something inside the submit namespace or using
        # Form.edit/delete/...
        if 'submit' in self.actions:
            setdefaults_path(self.actions, submit__call_target__attribute='primary')

        assert isinstance(self.fields, dict)

        refine_done_members(
            self,
            name='actions',
            members_from_namespace=self.actions,
            extra_member_defaults=extra_action_defaults,
            cls=self.get_meta().action_class,
            members_cls=Actions,
        )
        refine_done_members(
            self,
            name='fields',
            members_from_namespace=self.fields,
            members_from_declared=self.get_declared('_fields_dict'),
            members_from_auto=fields_from_auto,
            cls=self.get_meta().member_class,
            extra_member_defaults=extra_member_defaults,
        )

        super(Form, self).on_refine_done()

    def on_bind(self) -> None:
        self._errors: Set[str] = set()
        self._valid = None
        self.mode = INITIALS_FROM_GET
        self.parent_form = None

        request = self.get_request()
        self._request_data = request_data(request)

        self.instance = evaluate_strict(self.instance, **self.iommi_evaluate_parameters())

        # If this is a nested form register it with the parent, need
        # to do this early because is_target needs self.parent_form
        if self.iommi_parent() is not None:
            self.parent_form = self.iommi_parent().iommi_evaluate_parameters().get('form', None)
            if self.parent_form is not None:
                self.parent_form.nested_forms[self._name] = self
            if self.attr is MISSING:
                self.attr = self._name
        else:
            assert self.attr is MISSING, "Set Form.attr only if the form is nested in another form."

        if self.instance is None and self.parent_form is not None and self.parent_form.instance is not None:
            self.instance = self.read_nested_form_from_instance(self, self.parent_form.instance)

        self._evaluate_parameters['instance'] = self.instance
        self.editable = evaluate_strict(self.editable, **self.iommi_evaluate_parameters())

        self.title = evaluate_strict(self.title, **self.iommi_evaluate_parameters())
        build_and_bind_h_tag(self)

        # Actions have to be bound first because is_target() needs it
        bind_members(self, name='actions')

        if self._request_data is not None and self.is_target():
            self.mode = FULL_FORM_FROM_REQUEST

        self.all_fields = Namespace()
        self.nested_forms = Namespace()
        bind_members(self, name='fields', lazy=False)
        bind_members(self, name='endpoints')

        self.parts = self.fields
        self.fields = self.all_fields

        self.errors = Errors(parent=self, **self.errors)

        self.validate()

    def own_evaluate_parameters(self):
        return dict(form=self, instance=self.instance)

    @property
    def is_nested_form(self) -> bool:
        """Is this form nested in a parent form?"""
        return self.parent_form is not None

    @property
    def form_tag(self) -> str:
        if self.is_nested_form:
            return "div"
        else:
            return "form"

    # property for jinja2 compatibility
    @property
    def render_actions(self):
        # For now we do not support actions in child forms.
        if self.is_nested_form:
            return ''
        assert self._is_bound, NOT_BOUND_MESSAGE
        non_grouped_actions, grouped_actions = group_actions(self.actions)
        return render_template(
            self.get_request(),
            self.actions_template,
            dict(
                actions=self.iommi_bound_members().actions,
                non_grouped_actions=non_grouped_actions,
                grouped_actions=grouped_actions,
                form=self,
            ),
        )

    @classmethod
    @dispatch()
    def fields_from_model(cls, **kwargs):
        return create_members_from_model(
            member_class=cls.get_meta().member_class,
            **kwargs,
        )

    @classmethod
    @dispatch()
    def _from_model(cls, model, *, include=None, exclude=None, default_included=True):
        fields = cls.fields_from_model(model=model, include=include, exclude=exclude, default_included=default_included)
        return model, fields

    def is_target(self):
        self.iommi_path  # Make sure path tree is calculated top down.
        declared_members = object.__getattribute__(self.actions, '_declared_members')
        this_form_is_target = any(f'-{action.iommi_path}' in self._request_data for action in values(declared_members))

        if this_form_is_target:
            return True
        if self.parent_form is not None:
            return self.parent_form.is_target()
        return False

    def is_valid(self):
        """
        Is the form valid?  Can be called inside forms post_validation hook to determine if the
        individual fields were all valid.
        """
        assert self._is_bound, NOT_BOUND_MESSAGE
        assert self._valid is not None, "Internal error: Once a form is bound we should know if it is valid or not"
        return self._valid

    def validate(self):
        # When validate is called at the end of bind, self._valid will be either
        # False because a field's add_error was called during the fields bind.
        # Or it will still be None. In that latter case set it to True here,
        # so that we can call is_valid inside post_validation hook to check if
        # everything up until this point was valid.
        if self._valid is None:
            self._valid = True
        for field in values(self.fields):
            with validation_errors_reported_on(field):
                field.invoke_callback(field.post_validation)

        for nested_form in values(self.nested_forms):
            # At this point the nested forms are already validated, because
            # their on_bind has run.
            if not nested_form.is_valid():
                self._valid = False

        if self.mode is FULL_FORM_FROM_REQUEST:
            with validation_errors_reported_on(self):
                self.invoke_callback(self.post_validation)

        return self

    @staticmethod
    @refinable
    def post_validation(form, **_):
        pass

    def add_error(self, msg):
        # language=rst
        """
        Explicitly add an error message to the forms global error set.

        Example:

        .. code-block:: python

            def post_validation(form, **_):
                form.add_error('global error')

            form = Form.create(
                auto__model=Album,
                post_validation=post_validation,
            )
            # @test
            form = form.bind(request=req('post', **{'-submit': '',}))
            assert form.get_errors()['global'] == {'global error'}
            show_output(form)
            # @end
        """
        assert msg
        self._errors.add(msg)
        self._valid = False

    # property for jinja2 compatibility
    @property
    def render_fields(self):
        assert self._is_bound, NOT_BOUND_MESSAGE

        r = []
        for group, parts in groupby(values(self.parts), key=lambda x: getattr(x, 'group', MISSING)):
            if group is not MISSING:
                current_group = self.field_group(_name=f'iommi_field_group_{group}', group=group).bind(parent=self)
                r.append(current_group.iommi_open_tag())

                r.extend([part.__html__() for part in parts])

                r.append(current_group.iommi_close_tag())
            else:
                r.extend([part.__html__() for part in parts])

        # We need to preserve all other GET parameters, so we can e.g. filter in two forms on the same page, and keep sorting after filtering
        own_field_paths = {f.iommi_path for f in values(self.fields)}
        for k, v in items(self.get_request().GET):
            if k not in own_field_paths and not k.startswith('-') and not k.startswith(DISPATCH_PREFIX):
                r.append(format_html('<input type="hidden" name="{}" value="{}" />', k, v))

        return format_html('{}\n' * len(r), *r)

    @dispatch(
        render__call_target=render_template,
    )
    def __html__(self, *, render=None):
        setdefaults_path(
            render,
            template=self.template,
            context=self.iommi_evaluate_parameters().copy(),
        )

        request = self.get_request()
        render.context.update(csrf(request))

        return render(request=request)

    def apply(self, instance):
        """
        Write the new values specified in the form into the instance specified.
        """
        # TODO: Add child form errors to the assert message?
        assert self.is_valid(), f'errors: {self.get_errors()}'
        for field in values(self.fields):
            self.apply_field(instance=instance, field=field)
        for nested_form in values(self.nested_forms):
            nested_form.write_nested_form_to_instance(form=nested_form, instance=instance)

        return instance

    @staticmethod
    @refinable
    def write_nested_form_to_instance(form, instance):
        """
        Write the nested_form to the instance.

        This is analogous to `Field.write_to_instance` but for nested forms.
        """
        if form.attr == '':
            i = instance
        else:
            i = getattr_path(instance, form.attr)
        form.apply(instance=i)

    @staticmethod
    @refinable
    def read_nested_form_from_instance(form: 'Form', instance: Any) -> Any:
        """
        Read the nested forms instance from the parent forms instance.

        This is analogous to `Field.read_from_instance` but for nested forms.
        """
        if form.attr == '':
            return instance
        else:
            return getattr_path(instance, form.attr)

    @staticmethod
    def apply_field(instance, field):
        if not field.editable:
            field.value = field.initial

        if field.attr is not None:
            field.write_to_instance(field, instance, field.value)

    def get_errors(self):
        """
        Get a dict containing two keys:

        - `global` for errors global to the entire form.
        - `fields` for errors specific to fields. This is itself a dict with a key for each field.
        """
        assert self._is_bound, NOT_BOUND_MESSAGE
        r = {}
        if self._errors:
            r['global'] = self._errors
        field_errors = {x._name: x.get_errors() for x in values(self.fields) if x.get_errors()}
        if field_errors:
            r['fields'] = field_errors
        return r

    @classmethod
    @with_defaults(
        extra__pre_save_all_but_related_fields=lambda **kwargs: None,  # pragma: no mutate
        extra__on_save_all_but_related_fields=lambda **kwargs: None,  # pragma: no mutate
        extra__pre_save=lambda **kwargs: None,  # pragma: no mutate
        extra__on_save=lambda **kwargs: None,  # pragma: no mutate
        extra__on_delete=lambda **kwargs: None,  # pragma: no mutate
        extra__redirect=lambda redirect_to, **_: HttpResponseRedirect(redirect_to),
        extra__redirect_to=None,
        auto=EMPTY,
    )
    def crud(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    @with_defaults(
        extra__is_create=True,
        extra__new_instance=lambda form, **_: form.model(),
        actions__submit__post_handler=create_object__post_handler,
        extra__crud_type='create',
    )
    def create(cls, **kwargs):
        return cls.crud(**kwargs)

    @classmethod
    @with_defaults(
        extra__is_create=False,
        actions__submit__post_handler=edit_object__post_handler,
        extra__crud_type='edit',
    )
    def edit(cls, **kwargs):
        return cls.crud(**kwargs)

    @classmethod
    @with_defaults(
        actions__submit__call_target__attribute='delete',
        actions__submit__post_handler=delete_object__post_handler,
        extra__crud_type='delete',
        editable=False,
        fields__iommi_default_text=dict(
            call_target=Fragment,
            include=lambda form, **_: list(form.iommi_namespace.fields.keys()) == ['iommi_default_text'],
            after=0,
            tag='p',
            children__text=lambda instance, **_: (
                gettext('Are you sure you want to delete the %(model_name)s "%(instance)s"?')
                % dict(model_name=instance._meta.verbose_name, instance=str(instance))
            ),
        ),
    )
    def delete(cls, **kwargs):
        return cls.crud(**kwargs)

    def as_view(self):
        return build_as_view_wrapper(self)
