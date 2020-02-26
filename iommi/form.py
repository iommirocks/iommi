import re
from datetime import datetime
from decimal import (
    Decimal,
    InvalidOperation,
)
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Set,
    Tuple,
    Type,
    Union,
)

from django.db.models import (
    Model,
    Q,
    QuerySet,
)
from django.http import HttpResponseRedirect
from tri_declarative import (
    class_shortcut,
    declarative,
    dispatch,
    EMPTY,
    evaluate,
    evaluate_strict,
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
    evaluated_refinable,
    MISSING,
)
from iommi.error import Errors
from iommi.from_model import (
    AutoConfig,
    create_members_from_model,
    get_name_field,
    member_from_model,
)
from iommi.member import (
    bind_members,
    collect_members,
)
from iommi.page import (
    Fragment,
    Page,
)
from iommi.part import (
    Part,
    request_data,
)
from iommi.traversable import (
    EvaluatedRefinable,
    bound_members,
)

# Prevent django templates from calling That Which Must Not Be Called
Namespace.do_not_call_in_templates = True


def capitalize(s):
    return s[0].upper() + s[1:] if s else s


FULL_FORM_FROM_REQUEST = 'full_form_from_request'  # pragma: no mutate The string is just to make debugging nice
INITIALS_FROM_GET = 'initials_from_get'  # pragma: no mutate The string is just to make debugging nice


def bool_parse(string_value):
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


def create_or_edit_object__post_handler(*, form, is_create, **_):
    if is_create:
        assert form.instance is None
        form.instance = form.model()
        for field in form.fields.values():  # two phase save for creation in django, have to save main object before related stuff
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
        form.instance.save()

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

        return dict(
            results=field.extra.model_from_choices(form, field, result),
            page=page,
            pagination=dict(
                more=has_more,
            ),
        )
    except EmptyPage:
        return dict(result=[])


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
        return field.choices
    return field.choices.filter(Q((get_name_field(model=field.model) + '__icontains', value)))


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
    raise ValidationError('Time data "%s" does not match any of the formats %s' % (string_value, ', '.join('"%s"' % x for x in datetime_iso_formats)))


def datetime_render_value(value, **_):
    return value.strftime(datetime_iso_formats[0]) if value else ''


date_iso_format = '%Y-%m-%d'


def date_parse(string_value, **_):
    try:
        return datetime.strptime(string_value, date_iso_format).date()
    except ValueError as e:
        raise ValidationError(str(e))


def date_render_value(value, **_):
    return value.strftime(date_iso_format) if value else ''


time_iso_format = '%H:%M:%S'


def time_parse(string_value, **_):
    try:
        return datetime.strptime(string_value, time_iso_format).time()
    except ValueError as e:
        raise ValidationError(str(e))


def time_render_value(value, **_):
    return value.strftime(time_iso_format) if value else ''


def decimal_parse(string_value, **_):
    try:
        return Decimal(string_value)
    except InvalidOperation:
        raise ValidationError("Invalid literal for Decimal: '%s'" % string_value)


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

    attr: str = EvaluatedRefinable()
    display_name: str = EvaluatedRefinable()

    # raw_data/raw_data contains the strings grabbed directly from the request data
    # It is useful that they are evaluated for example when doing file upload. In that case the data is on request.FILES, not request.POST so we can use this to grab it from there
    raw_data: str = Refinable()  # raw_data is evaluated, but in a special way
    raw_data_list: List[str] = Refinable()  # raw_data_list is evaluated, but in a special way

    parse_empty_string_as_none: bool = EvaluatedRefinable()
    initial: Any = Refinable()  # initial is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = EvaluatedRefinable()

    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    required: bool = EvaluatedRefinable()

    input: Fragment = Refinable()
    label: Fragment = Refinable()
    non_editable_input: Fragment = Refinable()

    is_list: bool = EvaluatedRefinable()
    is_boolean: bool = EvaluatedRefinable()
    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    model_field = Refinable()
    field_name = Refinable()

    editable: bool = EvaluatedRefinable()
    strip_input: bool = EvaluatedRefinable()

    choices: Callable[['Form', 'Field', str], List[Any]] = Refinable()  # choices is evaluated, but in a special way so gets no EvaluatedRefinable type
    choice_to_option: Callable[['Form', 'Field', str], Tuple[Any, str, str, bool]] = Refinable()
    errors: Errors = Refinable()

    empty_label: str = EvaluatedRefinable()
    empty_choice_tuple = EvaluatedRefinable()

    @dispatch(
        attr=MISSING,
        display_name=MISSING,
        attrs__class=EMPTY,
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
        input__call_target=Fragment,
        input__attrs__id=default_input_id,
        input__attrs__name=lambda field, **_: field.iommi_path,
        input__extra__placeholder='',
        non_editable_input__call_target=Fragment,
        non_editable_input__attrs__type=None,
        initial=MISSING,
    )
    def __init__(self, **kwargs):
        """
        Note that, in addition to the parameters with the defined behavior below, you can pass in any keyword argument you need yourself, including callables that conform to the protocol, and they will be added and evaluated as members.

        All these parameters can be callables, and if they are, will be evaluated with the keyword arguments form and field. The only exceptions are `is_valid` (which gets `form`, `field` and `parsed_data`), `render_value` (which takes `form`, `field` and `value`) and `parse` (which gets `form`, `field`, `string_value`). Example of using a lambda to specify a value:

        .. code:: python

            Field(attrs__id=lambda form, field: 'my_id_%s' % field._name)

        :param after: Set the order of columns, see the `howto <https://docs.iommi.rocks/en/latest/howto.html#how-do-i-change-the-order-of-the-fields>`_ for an example.
        :param is_valid: validation function. Should return a tuple of `(bool, reason_for_failure_if_bool_is_false)` or raise ValidationError. Default: `lambda form, field, parsed_data: (True, '')`
        :param parse: parse function. Default just returns the string input unchanged: `lambda form, field, string_value: string_value`
        :param initial: initial value of the field
        :param attr: the attribute path to apply or get the data from. For example using `foo__bar__baz` will result in `your_instance.foo.bar.baz` will be set by the `apply()` function. Defaults to same as name
        :param attrs: a dict containing any custom html attributes to be sent to the `input__template`.
        :param display_name: the text in the HTML label tag. Default: `capitalize(name).replace('_', ' ')`
        :param template: django template filename for the entire row. Normally you shouldn't need to override on this level. Prefer overriding `input__template`, `label__template` or `error__template` as needed.
        :param template_string: You can inline a template string here if it's more convenient than creating a file. Default: `None`
        :param input__template: django template filename for the template for just the input control.
        :param label__template: django template filename for the template for just the label tab.
        :param errors__template: django template filename for the template for just the errors output. Default: `'iommi/form/errors.html'`
        :param required: if the field is a required field. Default: `True`
        :param help_text: The help text will be grabbed from the django model if specified and available.

        :param editable: Default: `True`
        :param strip_input: runs the input data through standard python .strip() before passing it to the parse function (can NOT be callable). Default: `True`
        :param render_value: render the parsed and validated value into a string. Default just converts to unicode: `lambda form, field, value: unicode(value)`
        :param is_list: interpret request data as a list (can NOT be a callable). Default: `False``
        :param read_from_instance: callback to retrieve value from edited instance. Invoked with parameters field and instance.
        :param write_to_instance: callback to write value to instance. Invoked with parameters field, instance and value.
        """

        super(Field, self).__init__(**kwargs)

        # parsed_data/parsed_data contains data that has been interpreted, but not checked for validity or access control
        self.parsed_data = None

        # value/value_data_list is the final step that contains parsed and valid data
        self.value = None

        self._choice_tuples = None

        self.non_editable_input = Namespace({
            **flatten(self.input),
            **self.non_editable_input,
            '_name': 'non_editable_input',
        })()
        self.input = self.input(_name='input')
        self.label = self.label(_name='label')

    @property
    def form(self):
        return self._parent._parent

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
        assert self.template

        form = self._parent._parent
        if self.attr is MISSING:
            self.attr = self._name
        if self.display_name is MISSING:
            self.display_name = capitalize(self._name).replace('_', ' ') if self._name else ''

        self.errors = Errors(parent=self, **self.errors)

        if form.editable is False:
            self.editable = False

        # Not strict evaluate on purpose
        self.model = evaluate(self.model, **self._evaluate_parameters)

        self.choices = evaluate_strict(self.choices, **self._evaluate_parameters)
        self.initial = evaluate_strict(self.initial, **self._evaluate_parameters)

        self._read_initial()
        self._read_raw_data()

        self._parse()
        self._validate()

        self.input = self.input.bind(parent=self)
        self.label = self.label.bind(parent=self)
        assert not self.label.children
        self.label.children = dict(text=self.display_name)
        self.non_editable_input = self.non_editable_input.bind(parent=self)

    def _parse(self):
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
        form = self._parent._parent
        if self.initial is MISSING and self.include and form.instance is not None:
            if self.attr:
                initial = self.read_from_instance(self, form.instance)
                self.initial = initial

        if self.initial is MISSING:
            self.initial = None

    def _read_raw_data(self):
        if self.raw_data is not None:
            self.raw_data = evaluate_strict(self.raw_data, **self._evaluate_parameters)
            return
        if self.raw_data_list is not None:
            self.raw_data_list = evaluate_strict(self.raw_data_list, **self._evaluate_parameters)
            return

        form = self._parent._parent

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
                self.choice_to_option(form=self._parent, field=self, choice=v)
                for v in self.value
            ]
        else:
            return [self.choice_to_option(form=self._parent, field=self, choice=self.value)]

    @property
    def choice_tuples(self):
        if self._choice_tuples is not None:
            return self._choice_tuples

        self._choice_tuples = []
        if not self.required and not self.is_list:
            self._choice_tuples.append(self.empty_choice_tuple + (0,))
        for i, choice in enumerate(self.choices):
            self._choice_tuples.append(self.choice_to_option(form=self.form, field=self, choice=choice) + (i + 1,))

        return self._choice_tuples

    @classmethod
    def from_model(cls, model, field_name=None, model_field=None, **kwargs):
        return member_from_model(
            cls=cls,
            model=model,
            factory_lookup=_field_factory_by_field_type,
            factory_lookup_register_function=register_field_factory,
            defaults_factory=field_defaults_factory,
            field_name=field_name,
            model_field=model_field,
            **kwargs)

    @dispatch(
        context=EMPTY,
        render=EMPTY,
    )
    def __html__(self, *, context=None, render=None):
        assert not render
        context = {
            'form': self.form,
            'field': self,
        }
        if self.is_boolean:
            if 'checked' not in self.input.attrs and self.value:
                self.input.attrs.checked = ''
        else:
            if 'value' not in self.input.attrs:
                self.input.attrs.value = self.rendered_value

        if not self.editable:
            assert not self.non_editable_input.children
            self.non_editable_input.children['text'] = self.rendered_value
            self.input = self.non_editable_input

        return render_template(self.get_request(), self.template, context)

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
        input__text=lambda field, **_: field.rendered_value,
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
        parse=lambda string_value, **_: bool_parse(string_value),
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
    form.instance.delete()
    return HttpResponseRedirect('../..')


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
            ]
        ).bind(request=request)

    See tri.declarative docs for more on this dual style of declaration.
"""
    actions: Namespace = Refinable()
    actions_template: Union[str, Template] = Refinable()
    attrs: Attrs = Refinable()  # attrs is evaluated, but in a special way so gets no EvaluatedRefinable type
    editable: bool = Refinable()
    h_tag: Fragment = Refinable()  # h_tag is evaluated, but in a special way so gets no EvaluatedRefinable type
    title: Fragment = Refinable()  # title is evaluated, but in a special way so gets no EvaluatedRefinable type
    template: Union[str, Template] = EvaluatedRefinable()

    model: Type[Model] = Refinable()  # model is evaluated, but in a special way so gets no EvaluatedRefinable type
    member_class: Type[Field] = Refinable()
    action_class: Type[Action] = Refinable()
    page_class: Type[Page] = Refinable()

    class Meta:
        member_class = Field
        action_class = Action
        page_class = Page

    @dispatch(
        model=None,
        editable=True,
        fields=EMPTY,
        attrs__action='',
        attrs__method='post',
        attrs__enctype='multipart/form-data',
        actions__submit__call_target__attribute='submit',
        auto=EMPTY,
        h_tag__call_target=Fragment,
        h_tag__tag=lambda form, **_: f'h{form.iommi_dunder_path.count("__")+1}',
    )
    def __init__(self, *, instance=None, fields: Dict[str, Field] = None, _fields_dict: Dict[str, Field] = None, actions: Dict[str, Any] = None, model, auto, title=None, **kwargs):

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
            if title is None and auto.type is not None:
                title = f'{auto.type.title()} {model._meta.verbose_name}'

                setdefaults_path(
                    actions,
                    submit__attrs__value=title,
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

        self.title = evaluate_strict(self.title, **self._evaluate_parameters)
        if isinstance(self.h_tag, Namespace):
            if self.title:
                self.h_tag = self.h_tag(text=self.title.capitalize()).bind(parent=self)
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
                actions=bound_members(self).actions,
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
        return any(action.is_target() for action in self.actions.values())

    def is_valid(self):
        if self._valid is None:
            self.validate()
            for field in self.fields.values():
                if field.errors:
                    self._valid = False
                    break
            else:
                self._valid = not self.errors
        return self._valid

    def validate(self):
        for field in self.fields.values():
            field.post_validation(form=self, field=field)
        self.post_validation(form=self)
        return self

    @staticmethod
    @refinable
    def post_validation(form):
        pass

    def add_error(self, msg):
        self.errors.add(msg)

    # property for jinja2 compatibility
    @property
    def render_fields(self):
        r = []
        for field in self.fields.values():
            r.append(field.__html__())

        # We need to preserve all other GET parameters, so we can e.g. filter in two forms on the same page, and keep sorting after filtering
        own_field_paths = {f.iommi_path for f in self.fields.values()}
        for k, v in self.get_request().GET.items():
            if k not in own_field_paths and not k.startswith('-'):
                r.append(format_html('<input type="hidden" name="{}" value="{}" />', k, v))

        return format_html('{}\n' * len(r), *r)

    @dispatch(
        render__call_target=render_template,
        context=EMPTY,
    )
    def __html__(self, *, context=None, render=None):
        setdefaults_path(
            render,
            context=context,
            template=self.template,
        )

        request = self.get_request()
        render.context.update(csrf(request))
        render.context['form'] = self

        return render(request=request)

    def apply(self, instance):
        """
        Write the new values specified in the form into the instance specified.
        """
        assert self.is_valid()
        for field in self.fields.values():
            self.apply_field(instance=instance, field=field)
        return instance

    @staticmethod
    def apply_field(instance, field):
        if not field.editable:
            field.value = field.initial

        if field.attr is not None:
            field.write_to_instance(field, instance, field.value)

    def get_errors(self):
        r = {}
        if self.errors:
            r['global'] = self.errors
        field_errors = {x._name: x.errors for x in self.fields.values() if x.errors}
        if field_errors:
            r['fields'] = field_errors
        return r

    @classmethod
    @class_shortcut(
        extra__on_save=lambda **kwargs: None,  # pragma: no mutate
        extra__redirect=lambda redirect_to, **_: HttpResponseRedirect(redirect_to),
        extra__redirect_to=None,
        auto=EMPTY,
    )
    def crud(cls, call_target, **kwargs):
        # if title is None:
        #     title = '%s %s' % ('Create' if extra.is_create else 'Save', model._meta.verbose_name.replace('_', ' '))
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
