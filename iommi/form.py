import re
from datetime import datetime
from decimal import (
    Decimal,
    InvalidOperation,
)
from functools import reduce
from operator import or_
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Set,
    Tuple,
    Type,
    Union,
    Optional
)

from django.db.models import (
    Case,
    IntegerField,
    Model,
    Q,
    QuerySet,
    When,
)
from django.utils.translation import gettext

from iommi.datetime_parsing import (
    parse_relative_date,
    parse_relative_datetime,
)
from iommi.debug import iommi_debug_on
from tri_declarative import (
    class_shortcut,
    declarative,
    dispatch,
    EMPTY,
    flatten,
    getattr_path,
    Namespace,
    Refinable,
    refinable,
    setattr_path,
    setdefaults_path,
    Shortcut,
    with_meta,
)
from tri_struct import Struct

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
    get_display_name,
    items,
    MISSING,
    capitalize,
    values,
)
from iommi.error import Errors
from iommi.evaluate import (
    evaluate,
    evaluate_strict,
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
    collect_members,
)
from iommi.page import (
    Page,
)
from iommi.fragment import (
    Fragment,
    Header,
)
from iommi.part import (
    Part,
    request_data,
)
from iommi.traversable import (
    EvaluatedRefinable,
    evaluated_refinable,
)
from iommi.reinvokable import reinvokable

# Prevent django templates from calling That Which Must Not Be Called
Namespace.do_not_call_in_templates = True


FULL_FORM_FROM_REQUEST = 'full_form_from_request'  # pragma: no mutate The string is just to make debugging nice
INITIALS_FROM_GET = 'initials_from_get'  # pragma: no mutate The string is just to make debugging nice


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
    getattr_path(instance, field.attr).set(value)


_field_factory_by_field_type = {}


def register_field_factory(django_field_class, *, shortcut_name=MISSING, factory=MISSING):
    assert shortcut_name is not MISSING or factory is not MISSING
    if factory is MISSING:
        factory = Shortcut(call_target__attribute=shortcut_name)

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
            result.add(tuple(parts[:i+1]))
    return ['__'.join(p) for p in sorted(sorted(result), key=len)]


def create_or_edit_object__post_handler(*, form, is_create, **_):
    if is_create:
        assert form.instance is None
        form.instance = form.model()
        for field in values(form.fields):  # two phase save for creation in django, have to save main object before related stuff
            if not field.extra.get('django_related_field', False):
                form.apply_field(field=field, instance=form.instance)

    try:
        form.instance.validate_unique()
    except ValidationError as e:
        form.errors.update(set(e.messages))
        form._valid = False  # pragma: no mutate. False here is faster, but setting it to None is also fine, it just means _valid will be calculated the next time form.is_valid() is called

    if not form.is_valid():
        return

    if is_create:  # two phase save for creation in django...
        form.instance.save()

    form.apply(form.instance)

    if not is_create:
        try:
            form.instance.validate_unique()
        except ValidationError as e:
            form.errors.update(set(e.messages))
            form._valid = False  # pragma: no mutate. False here is faster, but setting it to None is also fine, it just means _valid will be calculated the next time form.is_valid() is called

    if form.is_valid():
        attributes = filter(None, [f.attr for f in form.fields.values()])
        for prefix in find_unique_prefixes(attributes):
            model_object = form.instance
            if prefix:  # Might be ''
                model_object = getattr_path(model_object, prefix)
            model_object.save()

        form.extra.on_save(form=form, instance=form.instance)

        return create_or_edit_object_redirect(is_create, form.extra.redirect_to, form.get_request(), form.extra.redirect, form)


def default_endpoints__config(field: 'Field', **_) -> dict:
    return dict(
        name=field._name,
    )


def default_endpoints__validate(field: 'Field', **_) -> dict:
    return dict(
        valid=not bool(field.errors),
        errors=list(field.errors),
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


def choice_choice_to_option(form, field, choice):
    del form
    return choice, "%s" % choice, "%s" % choice, choice == field.value


def choice_parse(form, field, string_value):
    for c in field.choices:
        option = field.choice_to_option(form=form, field=field, choice=c)
        if option[1] == string_value:
            return option[0]

    if string_value in [None, '']:
        return None

    return string_value


def choice_queryset__is_valid(field, parsed_data, **_):
    return field.choices.filter(pk=parsed_data.pk).exists(), f'{field.raw_data or ", ".join(field.raw_data_list)} not in available choices'


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
            option = field.choice_to_option(form=form, field=field, choice=choice)
            yield Struct(
                id=option[1],
                text=option[2],
            )

    return list(traverse())


def choice_queryset__extra__filter_and_sort(field, value, **_):
    if not value:
        return field.choices.order_by(*field.search_fields)

    q_objects = []

    def create_q_objects(suffix):
        q_objects.extend([
            Q(**{search_field + suffix: value})
            for search_field in field.search_fields]
        )

    create_q_objects(suffix='')
    create_q_objects(suffix='__istartswith')
    create_q_objects(suffix='__icontains')

    when_clauses = [When(q, then=rank) for rank, q in enumerate(q_objects)]
    choices = field.choices.annotate(iommi_ranking=Case(*when_clauses, default=len(q_objects) + 1, output_field=IntegerField()))

    return choices.filter(reduce(or_, q_objects)).order_by('iommi_ranking', *field.search_fields)


def choice_queryset__parse(field, string_value, **_):
    try:
        return field.choices.get(pk=string_value) if string_value else None
    except field.model.DoesNotExist as e:
        raise ValidationError(str(e))


def choice_queryset__choice_to_option(field, choice, **_):
    return choice, choice.pk, "%s" % choice, choice == field.value


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
        raise ValidationError(f'Time data "{string_value}" does not match any of the formats "now", {formats}, and is not a relative date like "2d" or "2 weeks ago"')
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
        raise ValidationError(f'Time data "{string_value}" does not match any of the formats "now", {formats}, and is not a relative date like "2d" or "2 weeks ago"{extra_information}')
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
    return re.match(r'^\+\d{1,3}(([ \-])?\(\d+\))?(([ \-])?\d+)+$', parsed_data, re.IGNORECASE), 'Please use format +<country code> (XX) XX XX. Example of US number: +1 (212) 123 4567 or +1 212 123 4567'


def multi_choice_choice_to_option(field, choice, **_):
    return choice, "%s" % choice, "%s" % choice, field.value and choice in field.value


def multi_choice_queryset_choice_to_option(field, choice, **_):
    return choice, choice.pk, "%s" % choice, field.value and choice in field.value


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
class Field(Part):
    """
    Class that describes a field, i.e. what input controls to render, the label, etc.

    See :doc:`Form` for more complete examples.

    The life cycle of the data is:
        1. `raw_data`/`raw_data_list`: will be set if the corresponding key is present in the HTTP request
        2. `parsed_data`: set if parsing is successful, which only happens if the previous step succeeded
        3. `value`: set if validation is successful, which only happens if the previous step succeeded

    """

    tag: str = EvaluatedRefinable()
    attr: str = EvaluatedRefinable()
    display_name: str = EvaluatedRefinable()

    # raw_data/raw_data contains the strings grabbed directly from the request data
    # It is useful that they are evaluated for example when doing file upload. In that case the data is on request.FILES, not request.POST so we can use this to grab it from there
    raw_data: str = Refinable()  # raw_data is evaluated, but in a special way
    raw_data_list: List[str] = Refinable()  # raw_data_list is evaluated, but in a special way

    parse_empty_string_as_none: bool = EvaluatedRefinable()
    # parsed_data/parsed_data contains data that has been interpreted, but not checked for validity or access control
    parsed_data: Any = Refinable()  # parsed_data is evaluated, but in a special way so gets no EvaluatedRefinable type

    initial: Any = Refinable()  # initial is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = EvaluatedRefinable()

    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    required: bool = EvaluatedRefinable()

    input: Fragment = Refinable()
    label: Fragment = Refinable()
    non_editable_input: Fragment = Refinable()
    help: Fragment = Refinable()

    is_list: bool = EvaluatedRefinable()
    is_boolean: bool = EvaluatedRefinable()
    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    model_field = Refinable()
    model_field_name = Refinable()

    editable: bool = EvaluatedRefinable()
    strip_input: bool = EvaluatedRefinable()

    choices: Callable[..., List[Any]] = Refinable()  # choices is evaluated, but in a special way so gets no EvaluatedRefinable type
    choice_to_option: Callable[..., Tuple[Any, str, str, bool]] = Refinable()
    choice_to_optgroup: Optional[Callable[..., Optional[str]]] = Refinable()
    search_fields = Refinable()
    errors: Errors = Refinable()

    empty_label: str = EvaluatedRefinable()
    empty_choice_tuple: Tuple[Any, str, str, bool] = EvaluatedRefinable()

    @reinvokable
    @dispatch(
        tag=None,
        attr=MISSING,
        display_name=MISSING,
        attrs__class=EMPTY,
        attrs__style=EMPTY,
        parse_empty_string_as_none=True,
        required=True,
        is_list=False,
        is_boolean=False,
        editable=True,
        strip_input=True,
        endpoints__config__func=default_endpoints__config,
        endpoints__validate__func=default_endpoints__validate,
        errors=EMPTY,
        label__call_target=Fragment,
        label__attrs__for=default_input_id,
        help__call_target=Fragment,
        input__call_target=Fragment,
        input__attrs__id=default_input_id,
        input__attrs__name=lambda field, **_: field.iommi_path,
        input__extra__placeholder='',
        non_editable_input__call_target=Fragment,
        non_editable_input__attrs__type=None,
        initial=MISSING,
        choice_to_optgroup=None,
    )
    def __init__(self, **kwargs):
        """
        Note that, in addition to the parameters with the defined behavior below, you can pass in any keyword argument you need yourself, including callables that conform to the protocol, and they will be added and evaluated as members.

        All these parameters can be callables, and if they are, will be evaluated with the keyword arguments form and field. The only exceptions are `is_valid` (which gets `form`, `field` and `parsed_data`), `render_value` (which takes `form`, `field` and `value`) and `parse` (which gets `form`, `field`, `string_value`). Example of using a lambda to specify a value:

        .. code:: python

            Field(attrs__id=lambda form, field: 'my_id_%s' % field._name)

        :param after: Set the order of columns, see the `howto <https://docs.iommi.rocks/en/latest/howto.html#how-do-i-change-the-order-of-the-fields>`_ for an example.
        :param is_valid: validation function. Should return a tuple of `(bool, reason_for_failure_if_bool_is_false)` or raise ValidationError. Default: `lambda form, field, parsed_data: (True, '')`
        :param parse: Parse function. Default just returns the string input unchanged: `lambda form, field, string_value: string_value`. This function can raise `ValueError` or `ValidationError` to produce a field error message.
        :param initial: Initial value of the field
        :param attr: The attribute path to apply or get the data from. For example using `foo__bar__baz` will result in `your_instance.foo.bar.baz` will be set by the `apply()` function. Defaults to same as name
        :param attrs: A dict containing any custom html attributes to be sent to the `input__template`.
        :param display_name: The text in the HTML label tag. Default: `capitalize(name).replace('_', ' ')`
        :param template: django template filename for the entire row. Normally you shouldn't need to override on this level. Prefer overriding `input__template`, `label__template` or `error__template` as needed.
        :param template_string: You can inline a template string here if it's more convenient than creating a file. Default: `None`
        :param input__template: Django template filename for the template for just the input control.
        :param label__template: Django template filename for the template for just the label tab.
        :param required: If the field is a required field. Default: `True`
        :param help_text: The help text will be grabbed from the django model if specified and available.

        :param editable: Default: `True`
        :param strip_input: Runs the input data through standard python .strip() before passing it to the parse function (can NOT be callable). Default: `True`
        :param render_value: Render the parsed and validated value into a string. Default just converts to unicode: `lambda form, field, value: unicode(value)`
        :param is_list: Interpret request data as a list (can NOT be a callable). Default: `False``
        :param read_from_instance: Callback to retrieve value from edited instance. Invoked with parameters field and instance.
        :param write_to_instance: Callback to write value to instance. Invoked with parameters field, instance and value.
        :param choice_to_option: Callback to generate the choice data given a choice value. It will get the keyword arguments `form`, `field` and `choice`. It should return a 4-tuple: `(choice, internal_value, display_name, is_selected)`
        :param choice_to_optgroup Callback to generate the optgroup for the given choice.  It will get the keywoard argument `choice`. It should return None if the choice should not be grouped.
        """

        model_field = kwargs.get('model_field')
        if model_field and model_field.remote_field:
            kwargs['model'] = model_field.remote_field.model

        super(Field, self).__init__(**kwargs)

        # value/value_data_list is the final step that contains parsed and valid data
        self.value = None

        self.non_editable_input = Namespace({
            **flatten(self.input),
            **self.non_editable_input,
            '_name': 'non_editable_input',
        })()
        self.input = self.input(_name='input')
        self.label = self.label(_name='label')
        self.help = self.help(_name='help')

    @property
    def form(self):
        return self.iommi_parent().iommi_parent()

    # noinspection PyUnusedLocal
    @staticmethod
    @refinable
    def is_valid(form: 'Form', field: 'Field', parsed_data: Any, **_) -> Tuple[bool, str]:
        return True, ''

    # noinspection PyUnusedLocal
    @staticmethod
    @refinable
    def parse(form: 'Form', field: 'Field', string_value: str, **_) -> Any:
        del form, field
        return string_value

    @staticmethod
    @refinable
    def post_validation(form: 'Form', field: 'Field', **_) -> None:
        pass

    @staticmethod
    @refinable
    def render_value(form: 'Form', field: 'Field', value: Any) -> str:
        if isinstance(value, (list, QuerySet)):
            return ', '.join(field.render_value(form=form, field=field, value=v) for v in value)
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

    def on_bind(self) -> None:
        form = self.iommi_parent().iommi_parent()
        if self.attr is MISSING:
            self.attr = self._name
        if self.display_name is MISSING:
            self.display_name = get_display_name(self)

        self.errors = Errors(parent=self, **self.errors)

        if form.editable is False:
            self.editable = False

        # Not strict evaluate on purpose
        self.model = evaluate(self.model, **self.iommi_evaluate_parameters())

        self.choices = evaluate_strict(self.choices, **self.iommi_evaluate_parameters())

        self.initial = evaluate_strict(self.initial, **self.iommi_evaluate_parameters())
        self._read_initial()

        self._read_raw_data()

        self.parsed_data = evaluate_strict(self.parsed_data, **self.iommi_evaluate_parameters())
        self._parse()

        self._validate()

        self.input = self.input.bind(parent=self)
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

        if self.model and self.include:
            try:
                self.search_fields = get_search_fields(model=self.model)
            except NoRegisteredSearchFieldException:
                self.search_fields = ['pk']
                if iommi_debug_on():
                    print(f'Warning: falling back to primary key as lookup and sorting on {self._name}. \nTo get rid of this warning and get a nicer lookup and sorting use register_search_fields for model {self.model}.')

    def _parse(self):
        if self.parsed_data is not None:
            return

        if not self.editable:
            return

        if self.form.mode is INITIALS_FROM_GET and self.raw_data is None and self.raw_data_list is None:
            return

        if self.is_list:
            if self.raw_data_list is not None:
                self.parsed_data = [self._parse_raw_value(x) for x in self.raw_data_list]
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
        try:
            return self.parse(form=self.form, field=self, string_value=raw_data)
        except ValueError as e:
            assert str(e) != ''
            self.errors.add(str(e))
        except ValidationError as e:
            for message in e.messages:
                msg = "%s" % message
                assert msg != ''
                self.errors.add(msg)

    def _validate(self):
        form = self.form
        if (not self.editable) or (form.mode is INITIALS_FROM_GET and self.raw_data is None and not self.raw_data_list):
            self.value = self.initial
            return

        value = None
        if self.is_list:
            if self.parsed_data is not None:
                value = [self._validate_parsed_data(x) for x in self.parsed_data if x is not None]
        else:
            if self.parsed_data is not None:
                value = self._validate_parsed_data(self.parsed_data)

        if not self.errors:
            if form.mode is FULL_FORM_FROM_REQUEST and self.required and value in [None, '']:
                self.errors.add('This field is required')
            else:
                self.value = value

    def _validate_parsed_data(self, value):
        is_valid, error = self.is_valid(
            form=self.form,
            field=self,
            parsed_data=value)
        if is_valid and not self.errors and self.parsed_data is not None and not self.is_list:
            value = self.parsed_data
        elif not is_valid and self.form.mode:
            if not isinstance(error, set):
                error = {error}
            for e in error:
                assert error != ''
                self.errors.add(e)
        return value

    def _read_initial(self):
        form = self.iommi_parent().iommi_parent()
        if self.initial is MISSING and self.include and form.instance is not None:
            if self.attr:
                initial = self.read_from_instance(self, form.instance)
                self.initial = initial

        if self.initial is MISSING:
            self.initial = None

    def _read_raw_data(self):
        if self.raw_data is not None:
            self.raw_data = evaluate_strict(self.raw_data, **self.iommi_evaluate_parameters())
            return
        if self.raw_data_list is not None:
            self.raw_data_list = evaluate_strict(self.raw_data_list, **self.iommi_evaluate_parameters())
            return

        form = self.iommi_parent().iommi_parent()

        if self.is_list:
            if self.raw_data_list is not None:
                return
            try:
                # django and similar
                # noinspection PyUnresolvedReferences
                raw_data_list = form._request_data.getlist(self.iommi_path)
            except AttributeError:  # pragma: no cover
                # werkzeug and similar
                raw_data_list = form._request_data.get(self.iommi_path)

            if raw_data_list and self.strip_input:
                raw_data_list = [x.strip() for x in raw_data_list]

            if raw_data_list is not None:
                self.raw_data_list = raw_data_list
        else:
            if self.raw_data is not None:
                return
            self.raw_data = form._request_data.get(self.iommi_path)
            if self.raw_data and self.strip_input:
                self.raw_data = self.raw_data.strip()

    def own_evaluate_parameters(self):
        return dict(field=self)

    @property
    def rendered_value(self):
        if self.errors:
            return self.raw_data
        return self.render_value(form=self.form, field=self, value=self.value)

    @property
    def choice_to_options_selected(self):
        if self.value is None:
            return []

        if self.is_list:
            return [
                self.choice_to_option(form=self.iommi_parent(), field=self, choice=v)
                for v in self.value
            ]
        else:
            return [self.choice_to_option(form=self.iommi_parent(), field=self, choice=self.value)]

    @property
    def choice_tuples(self):
        result = []
        if not self.required and not self.is_list:
            result.append(self.empty_choice_tuple + (0,))
        for i, choice in enumerate(self.choices):
            result.append(self.choice_to_option(form=self.form, field=self, choice=choice) + (i + 1,))

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
                group_name = self.choice_to_optgroup(choice=choice, **self.iommi_evaluate_parameters())
                if current_group_name != group_name:
                    current_group_name = group_name
                    current_group = []
                    groups.append((current_group_name, current_group))
                current_group.append(choice_tuple)
            return groups

    @classmethod
    def from_model(cls, model, model_field_name=None, model_field=None, **kwargs):
        return member_from_model(
            cls=cls,
            model=model,
            factory_lookup=_field_factory_by_field_type,
            factory_lookup_register_function=register_field_factory,
            defaults_factory=field_defaults_factory,
            model_field_name=model_field_name,
            model_field=model_field,
            **kwargs)

    @dispatch(
        render=EMPTY,
    )
    def __html__(self, *, render=None):
        assert not render
        if self.is_boolean:
            if 'checked' not in self.input.attrs and self.value:
                self.input.attrs.checked = ''
        else:
            if 'value' not in self.input.attrs:
                self.input.attrs.value = self.rendered_value

        if not self.editable:
            self.non_editable_input.children['text'] = self.rendered_value
            self.input = self.non_editable_input

        if self.template:
            return render_template(self.get_request(), self.template, self.iommi_evaluate_parameters())

        return Fragment(
            _name=self._name,
            tag=self.tag,
            attrs=self.attrs,
            children=dict(
                label=render_fragment(self.label),
                input=render_fragment(self.input),
                help=render_fragment(self.help),
                errors=render_fragment(self.errors),
            ),
        ).bind(parent=self._parent).__html__()

    @classmethod
    @class_shortcut(
        input__attrs__type='hidden',
        attrs__style__display='none',
    )
    def hidden(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        input__attrs__type='text',
    )
    def text(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        input__tag='textarea',
        input__attrs__type=None,
        input__attrs__value=None,
        input__children__text=lambda field, **_: field.rendered_value,
        input__attrs__readonly=lambda field, **_: True if field.editable is False else None,
    )
    def textarea(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        parse=int_parse,
    )
    def integer(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        parse=float_parse,
    )
    def float(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        input__attrs__type='password',
    )
    def password(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    # Boolean field. Tries hard to parse a boolean value from its input.
    @classmethod
    @class_shortcut(
        parse=bool_parse,
        required=False,
        is_boolean=True,
    )
    def boolean(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        required=True,
        is_list=False,
        empty_label='---',
        is_valid=choice_is_valid,
        choice_to_option=choice_choice_to_option,
        parse=choice_parse,
    )
    def choice(cls, call_target=None, **kwargs):
        """
        Shortcut for single choice field. If required is false it will automatically add an option first with the value '' and the title '---'. To override that text pass in the parameter empty_label.
        :param choice_to_option: callable with three arguments: form, field, choice. Convert from a choice object to a tuple of (choice, value, label, selected), the last three for the <option> element
        """
        assert 'choices' in kwargs

        setdefaults_path(
            kwargs,
            empty_choice_tuple=(None, '', kwargs['empty_label'], True),
        )

        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute="choice",
        choices=[True, False],
        choice_to_option=lambda form, field, choice, **_: (
                choice,
                'true' if choice else 'false',
                'Yes' if choice else 'No',
                choice == field.value,
        ),
        parse=boolean_tristate__parse,
        required=False,
    )
    def boolean_tristate(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute="choice",
        parse=choice_queryset__parse,
        choice_to_option=choice_queryset__choice_to_option,
        endpoints__choices__func=choice_queryset__endpoint_handler,
        is_valid=choice_queryset__is_valid,
        extra__filter_and_sort=choice_queryset__extra__filter_and_sort,
        extra__model_from_choices=choice_queryset__extra__model_from_choices,
    )
    def choice_queryset(cls, choices, call_target=None, **kwargs):
        if 'model' not in kwargs:
            if isinstance(choices, QuerySet):
                kwargs['model'] = choices.model
            elif 'model_field' in kwargs:
                kwargs['model'] = kwargs['model_field'].remote_field.model
            else:
                assert False, 'The convenience feature to automatically get the parameter model set only works for QuerySet instances or if you specify model_field'

        setdefaults_path(
            kwargs,
            choices=(lambda form, **_: choices.all()) if isinstance(choices, QuerySet) else choices,  # clone the QuerySet if needed
        )

        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice',
        input__attrs__multiple=True,
        choice_to_option=multi_choice_choice_to_option,
        is_list=True,
    )
    def multi_choice(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice_queryset',
        input__attrs__multiple=True,
        choice_to_option=multi_choice_queryset_choice_to_option,
        is_list=True,
    )
    def multi_choice_queryset(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice',
        input__attrs__id=None,
        extra_evaluated__id=default_input_id,
    )
    def radio(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        parse=datetime_parse,
        render_value=datetime_render_value,
    )
    def datetime(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        parse=date_parse,
        render_value=date_render_value,
    )
    def date(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        parse=time_parse,
        render_value=time_render_value,
    )
    def time(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        parse=decimal_parse,
    )
    def decimal(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        input__attrs__type='url',
        parse=url_parse,
    )
    def url(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        input__attrs__type='file',
        raw_data=file__raw_data,
        write_to_instance=file_write_to_instance,
    )
    def file(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='file',
        template='iommi/form/image_row.html',
    )
    def image(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    # Shortcut to create a fake input that performs no parsing but is useful to separate sections of a form.
    @classmethod
    @class_shortcut(
        editable=False,
        attr=None,
    )
    def heading(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        editable=False,
        attr=None,
    )
    def info(cls, value, call_target=None, **kwargs):
        """
        Shortcut to create an info entry.
        """
        setdefaults_path(
            kwargs,
            initial=value,

        )
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        input__attrs__type='email',
        parse=email_parse,
    )
    def email(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        is_valid=phone_number_is_valid,
    )
    def phone_number(cls, call_target=None, **kwargs):
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
            read_from_instance=many_to_many_factory_read_from_instance,
            write_to_instance=many_to_many_factory_write_to_instance,
            extra__django_related_field=True,
        )
        return call_target(model_field=model_field, **kwargs)


def create_or_edit_object_redirect(is_create, redirect_to, request, redirect, form):
    if redirect_to is None:
        if is_create:
            redirect_to = "../"
        else:
            redirect_to = "../../"  # We guess here that the path ends with '<pk>/edit/' so this should end up at a good place
    return redirect(request=request, redirect_to=redirect_to, form=form)


def delete_object__post_handler(form, **_):
    instance = form.instance
    form.extra.on_delete(form=form, instance=instance)
    if instance.pk is not None:  # Check if already deleted by the callback
        instance.delete()
    return HttpResponseRedirect('../..')


# noinspection PyUnreachableCode
if False:
    # These are needed to make makemessages collect these strings
    gettext('create')
    gettext('edit')
    gettext('delete')


class FormAutoConfig(AutoConfig):
    instance = Refinable()
    type = Refinable()  # one of 'create', 'edit', 'delete'


@declarative(Field, '_fields_dict')
@with_meta
class Form(Part):
    """
    Describe a Form. Example:

    .. code:: python

        class MyForm(Form):
            a = Field()
            b = Field.email()

        form = MyForm().bind(request=request)

    You can also create an instance of a form with this syntax if it's more convenient:

    .. code:: python

        form = MyForm(
            fields=dict(
                a=Field(),
                b=Field.email(),
            ),
        ).bind(request=request)

    See tri.declarative docs for more on this dual style of declaration.
"""
    actions: Namespace = Refinable()
    actions_template: Union[str, Template] = Refinable()
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    editable: bool = Refinable()
    h_tag: Union[Fragment, str] = Refinable()  # h_tag is evaluated, but in a special way so gets no EvaluatedRefinable type
    title: Union[Fragment, str] = Refinable()  # title is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = EvaluatedRefinable()

    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    member_class: Type[Field] = Refinable()
    action_class: Type[Action] = Refinable()
    page_class: Type[Page] = Refinable()

    class Meta:
        member_class = Field
        action_class = Action
        page_class = Page

    @reinvokable
    @dispatch(
        model=None,
        editable=True,
        fields=EMPTY,
        attrs__action='',
        attrs__method='post',
        attrs__enctype='multipart/form-data',
        actions__submit__call_target__attribute='primary',
        auto=EMPTY,
        h_tag__call_target=Header,
    )
    def __init__(self, *, instance=None, fields: Dict[str, Field] = None, _fields_dict: Dict[str, Field] = None, actions: Dict[str, Any] = None, model=None, auto=None, title=MISSING, **kwargs):

        if auto:
            auto = FormAutoConfig(**auto)
            assert not _fields_dict, "You can't have an auto generated Form AND a declarative Form at the same time"
            assert not model, "You can't use the auto feature and explicitly pass model. Either pass auto__model, or we will set the model for you from auto__instance"
            assert not instance, "You can't use the auto feature and explicitly pass instance. Pass auto__instance (None in the create case)"
            if auto.model is None:
                auto.model = auto.instance.__class__

            model, fields = self._from_model(
                model=auto.model,
                fields=fields,
                include=auto.include,
                exclude=auto.exclude,
            )
            instance = auto.instance
            if title is MISSING and auto.type is not None:
                title = capitalize(gettext('%(crud_type)s %(model_name)s') % dict(crud_type=gettext(auto.type), model_name=model._meta.verbose_name))

                setdefaults_path(
                    actions,
                    submit__display_name=gettext('Save') if auto.type == 'edit' else capitalize(gettext(auto.type)),
                )

        super(Form, self).__init__(model=model, title=title, **kwargs)

        assert isinstance(fields, dict)

        self.fields = None
        self.errors: Set[str] = set()
        self._valid = None
        self.instance = instance
        self.mode = INITIALS_FROM_GET

        collect_members(self, name='actions', items=actions, cls=self.get_meta().action_class)
        collect_members(self, name='fields', items=fields, items_dict=_fields_dict, cls=self.get_meta().member_class)

    def on_bind(self) -> None:
        assert self.actions_template
        self._valid = None
        request = self.get_request()
        self._request_data = request_data(request)

        self.title = evaluate_strict(self.title, **self.iommi_evaluate_parameters())
        if isinstance(self.h_tag, Namespace):
            if self.title not in (None, MISSING):
                self.h_tag = self.h_tag(
                    _name='h_tag',
                    children__text=capitalize(self.title),
                ).bind(parent=self)
            else:
                self.h_tag = ''
        else:
            self.h_tag = self.h_tag.bind(parent=self)

        # Actions have to be bound first because is_target() needs it
        bind_members(self, name='actions', cls=Actions)

        if self._request_data is not None and self.is_target():
            self.mode = FULL_FORM_FROM_REQUEST

        bind_members(self, name='fields')
        bind_members(self, name='endpoints')

        self.is_valid()

        self.errors = Errors(parent=self, errors=self.errors)

    def own_evaluate_parameters(self):
        return dict(form=self)

    # property for jinja2 compatibility
    @property
    def render_actions(self):
        assert self._is_bound, 'The form has not been bound. You need to call bind() before you can render it.'
        non_grouped_actions, grouped_actions = group_actions(self.actions)
        return render_template(
            self.get_request(),
            self.actions_template,
            dict(
                actions=self.iommi_bound_members().actions,
                non_grouped_actions=non_grouped_actions,
                grouped_actions=grouped_actions,
                form=self,
            ))

    @classmethod
    @dispatch(
        fields=EMPTY,
    )
    def fields_from_model(cls, fields, **kwargs):
        return create_members_from_model(
            member_class=cls.get_meta().member_class,
            member_params_by_member_name=fields,
            **kwargs
        )

    @classmethod
    @dispatch(
        fields=EMPTY,
    )
    def _from_model(cls, model, *, fields, include=None, exclude=None):
        fields = cls.fields_from_model(model=model, include=include, exclude=exclude, fields=fields)
        return model, fields

    def is_target(self):
        return any(action.is_target() for action in values(self.actions))

    def is_valid(self):
        if self._valid is None:
            self.validate()
            for field in values(self.fields):
                if field.errors:
                    self._valid = False
                    break
            else:
                self._valid = not self.errors
        return self._valid

    def validate(self):
        for field in values(self.fields):
            field.post_validation(**field.iommi_evaluate_parameters())
        self.post_validation(**self.iommi_evaluate_parameters())
        return self

    @staticmethod
    @refinable
    def post_validation(form, **_):
        pass

    def add_error(self, msg):
        self.errors.add(msg)

    # property for jinja2 compatibility
    @property
    def render_fields(self):
        r = []
        for field in values(self.fields):
            r.append(field.__html__())

        # We need to preserve all other GET parameters, so we can e.g. filter in two forms on the same page, and keep sorting after filtering
        own_field_paths = {f.iommi_path for f in values(self.fields)}
        for k, v in items(self.get_request().GET):
            if k not in own_field_paths and not k.startswith('-'):
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
        assert self.is_valid()
        for field in values(self.fields):
            self.apply_field(instance=instance, field=field)
        return instance

    @staticmethod
    def apply_field(instance, field):
        if not field.editable:
            field.value = field.initial

        if field.attr is not None:
            field.write_to_instance(field, instance, field.value)

    def get_errors(self):
        self.is_valid()
        r = {}
        if self.errors:
            r['global'] = self.errors
        field_errors = {x._name: x.errors for x in values(self.fields) if x.errors}
        if field_errors:
            r['fields'] = field_errors
        return r

    @classmethod
    @class_shortcut(
        extra__on_save=lambda **kwargs: None,  # pragma: no mutate
        extra__on_delete=lambda **kwargs: None,  # pragma: no mutate
        extra__redirect=lambda redirect_to, **_: HttpResponseRedirect(redirect_to),
        extra__redirect_to=None,
        auto=EMPTY,
    )
    def crud(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='crud',
        extra__is_create=True,
        actions__submit__post_handler=create_object__post_handler,
        auto__type='create',
    )
    def create(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='crud',
        extra__is_create=False,
        actions__submit__post_handler=edit_object__post_handler,
        auto__type='edit',
    )
    def edit(cls, call_target, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='crud',
        actions__submit__call_target__attribute='delete',
        actions__submit__post_handler=delete_object__post_handler,
        auto__type='delete',
        editable=False,
    )
    def delete(cls, call_target, **kwargs):
        return call_target(**kwargs)

    def as_view(self):
        return build_as_view_wrapper(self)
