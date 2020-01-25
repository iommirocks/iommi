import json
import re
from datetime import datetime
from decimal import (
    Decimal,
    InvalidOperation,
)
from itertools import (
    chain,
    groupby,
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

from django.http import HttpResponseRedirect
from iommi._db_compat import field_defaults_factory
from iommi._web_compat import (
    Template,
    URLValidator,
    ValidationError,
    csrf,
    format_html,
    get_template_from_string,
    mark_safe,
    render_template,
    render_to_string,
    slugify,
    validate_email,
)
from iommi.base import (
    DISPATCH_PATH_SEPARATOR,
    MISSING,
    PagePart,
    bind_members,
    collect_members,
    evaluate_attrs,
    no_copy_on_bind,
    render_template_name,
    request_data,
    setup_endpoint_proxies,
)
from iommi.page import Fragment
from iommi.render import Errors
from tri_declarative import (
    EMPTY,
    Namespace,
    Refinable,
    assert_kwargs_empty,
    class_shortcut,
    declarative,
    dispatch,
    evaluate,
    evaluate_recursive,
    getattr_path,
    refinable,
    setattr_path,
    setdefaults_path,
    with_meta,
)
from tri_struct import Struct

# Prevent django templates from calling That Which Must Not Be Called
Namespace.do_not_call_in_templates = True


def capitalize(s):
    return s[0].upper() + s[1:] if s else s


FULL_FORM_FROM_REQUEST = 'full_form_from_request'  # pragma: no mutate The string is just to make debugging nice
INITIALS_FROM_GET = 'initials_from_get'  # pragma: no mutate The string is just to make debugging nice

# This input is added to all forms. It is used to circumvent the fact that unchecked checkboxes are not sent as
# parameters in the request. More specifically, the problem occurs when the checkbox is checked by default,
# as it would not be possible to distinguish between the initial request and a subsequent request where the checkbox
# is unchecked. By adding this input, it is possible to make this distinction as subsequent requests will contain
# (at least) this key-value.
AVOID_EMPTY_FORM = '<input type="hidden" name="-{}" value="" />'


def dispatch_prefix_and_remaining_from_key(key):
    prefix, _, remaining_key = key.partition(DISPATCH_PATH_SEPARATOR)
    return prefix, remaining_key


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


def register_field_factory(field_class, factory):
    _field_factory_by_field_type[field_class] = factory


# TODO: extra param here should also be a dict
@dispatch  # pragma: no mutate
def create_members_from_model(default_factory, model, member_params_by_member_name, include=None, exclude=None, extra=None):
    def should_include(name):
        if exclude is not None and name in exclude:
            return False
        if include is not None:
            return name in include
        return True

    members = []

    # Validate include/exclude parameters
    field_names = {x.name for x in get_fields(model)}
    if include:
        not_existing = {x for x in include if x.partition('__')[0] not in field_names}
        assert not not_existing, 'You can only include fields that exist on the model: %s specified but does not exist' % ', '.join(sorted(not_existing))
    if exclude:
        not_existing = {x for x in exclude if x not in field_names}
        assert not not_existing, 'You can only exclude fields that exist on the model: %s specified but does not exist' % ', '.join(sorted(not_existing))

    extra_includes = [x for x in include if '__' in x] if include else []

    for field in get_fields(model):
        if should_include(field.name):
            foo = member_params_by_member_name.pop(field.name, {})
            if isinstance(foo, dict):
                subkeys = Namespace(**foo)
                subkeys.setdefault('call_target', default_factory)
                foo = subkeys(name=field.name, model=model, model_field=field)
            if foo is None:
                continue
            if isinstance(foo, list):
                members.extend(foo)
            else:
                assert foo.name, "Fields must have a name attribute"
                assert foo.name == field.name, f"Field {foo.name} has a name that doesn't match the model field it belongs to: {field.name}"
                members.append(foo)
    assert_kwargs_empty(member_params_by_member_name)
    all_members = members + (extra if extra is not None else []) + [default_factory(model=model, field_name=x) for x in extra_includes]
    return Struct({x.name: x for x in all_members})


def member_from_model(cls, model, factory_lookup, defaults_factory, factory_lookup_register_function=None, field_name=None, model_field=None, **kwargs):
    if model_field is None:
        assert field_name is not None, "Field can't be automatically created from model, you must specify it manually"

        sub_field_name, _, field_path_rest = field_name.partition('__')

        # noinspection PyProtectedMember
        model_field = model._meta.get_field(sub_field_name)

        if field_path_rest:
            result = member_from_model(
                cls=cls,
                model=model_field.remote_field.model,
                factory_lookup=factory_lookup,
                defaults_factory=defaults_factory,
                factory_lookup_register_function=factory_lookup_register_function,
                field_name=field_path_rest,
                **kwargs)
            result.name = field_name
            result.attr = field_name
            return result

    factory = factory_lookup.get(type(model_field), MISSING)

    if factory is MISSING:
        for django_field_type, foo in reversed(list(factory_lookup.items())):
            if isinstance(model_field, django_field_type):
                factory = foo
                break  # pragma: no mutate optimization

    if factory is MISSING:
        message = 'No factory for %s.' % type(model_field)
        if factory_lookup_register_function is not None:
            message += ' Register a factory with %s, you can also register one that returns None to not handle this field type' % factory_lookup_register_function.__name__
        raise AssertionError(message)

    if factory is None:
        return None

    factory = evaluate(factory, model_field=model_field, field_name=field_name)

    setdefaults_path(
        kwargs,
        name=field_name,
        call_target__cls=cls,
    )

    defaults = defaults_factory(model_field)
    if isinstance(factory, Namespace):
        factory = setdefaults_path(
            Namespace(),
            factory,
            defaults,
        )
    else:
        kwargs.update(**defaults)

    return factory(model_field=model_field, model=model, **kwargs)


@dispatch(
    fields=EMPTY,
)
def expand_member(cls, model, factory_lookup, defaults_factory, name, fields, field_name=None, model_field=None):
    if field_name is None:
        field_name = name

    if model_field is None:
        # noinspection PyProtectedMember
        model_field = model._meta.get_field(field_name)

    result = [
        member_from_model(
            cls=cls,
            model=model_field.remote_field.model,
            factory_lookup=factory_lookup,
            factory_lookup_register_function=register_field_factory,
            defaults_factory=defaults_factory,
            field_name=sub_model_field.name,
            name=name + '__' + sub_model_field.name,
            attr=field_name + '__' + sub_model_field.name,
            **fields.pop(sub_model_field.name, {})
        )
        for sub_model_field in get_fields(model=model_field.remote_field.model)
    ]
    assert_kwargs_empty(fields)
    return [x for x in result if x is not None]


def create_or_edit_object__post_handler(*, form, **_):
    if form.extra.is_create:
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

    if form.is_valid():
        if form.extra.is_create:  # two phase save for creation in django...
            form.instance.save()

        form.apply(form.instance)

        if not form.extra.is_create:
            try:
                form.instance.validate_unique()
            except ValidationError as e:
                form.errors.update(set(e.messages))
                form._valid = False  # pragma: no mutate. False here is faster, but setting it to None is also fine, it just means _valid will be calculated the next time form.is_valid() is called

        if form.is_valid():
            form.instance.save()

            form.extra.on_save(form=form, instance=form.instance)

            return create_or_edit_object_redirect(form.extra.is_create, form.extra.redirect_to, form.request(), form.extra.redirect, form)


def default_endpoint__config(field: 'Field', **_) -> dict:
    return dict(
        name=field.name,
    )


def default_endpoint__validate(field: 'Field', **_) -> dict:
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


def choice_is_valid(form, field, parsed_data, **_):
    del form
    return parsed_data in field.choices, f'{parsed_data} not in available choices'


def choice_post_validation(form, field):
    def choice_tuples_lazy():
        choice_tuples = (field.choice_to_option(form=form, field=field, choice=choice) for choice in field.choices)
        if not field.required and not field.is_list:
            choice_tuples = chain([field.empty_choice_tuple], choice_tuples)
        return choice_tuples

    field.choice_tuples = choice_tuples_lazy


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


def choice_queryset__endpoint_handler(*, form, field, value, **_):
    from django.core.paginator import EmptyPage, Paginator

    page_size = field.extra.get('endpoint_page_size', 40)
    page = int(form.request().GET.get('page', 1))
    choices = field.extra.filter_and_sort(form=form, field=field, value=value)
    try:
        paginator = Paginator(choices, page_size)
        result = paginator.page(page)
        has_more = result.has_next()

        return dict(
            results=field.extra.model_from_choices(form, field, result),
            page=page,
            more=has_more,
        )
    except EmptyPage:
        return dict(result=[])


def choice_queryset__extra__current_selection_json(form, field, **_):
    # Return a function here to make r callable from the template and not be evaluated here
    def result():
        if field.value is None and field.value_list is None:
            return 'null'
        if field.is_list:
            r = choice_queryset__extra__model_from_choices(form, field, field.value_list)
        else:
            r = choice_queryset__extra__model_from_choices(form, field, [field.value])[0]

        return mark_safe(json.dumps(r))

    return result


def choice_queryset__extra__model_from_choices(form, field, choices):
    def traverse():
        for choice in choices:
            option = field.choice_to_option(form=form, field=field, choice=choice)
            yield Struct(
                id=option[1],
                text=option[2],
            )

    return list(traverse())


def get_name_field(field):
    from django.db import models
    fields = [x.attname for x in get_fields(field.model_field.target_field.model) if isinstance(x, models.CharField)]
    if 'name' in fields:
        return 'name'
    else:
        name_fields = [x for x in fields if 'name' in x]
        if name_fields:
            return name_fields[0]

    assert fields, "Searching for a field requires it to have a character field we can use for searching. I couldn't find one to use as a guess you you must specify how to perform the search explicitly via `extra__endpoint_attrs`"
    return fields[0]


def choice_queryset__extra__filter_and_sort(field, value, **_):
    # TODO: too magical AND wrong. There should be a name registration system for this.
    if 'endpoint_attrs' not in field.extra and 'endpoint_attr' in field.extra:
        attrs = [field.extra.endpoint_attr]
    elif 'endpoint_attrs' in field.extra:
        attrs = field.extra.endpoint_attrs
    elif field.model_field:
        attrs = [get_name_field(field)]
    else:
        attrs = [field.attr]

    from django.db.models import Q
    qs = Q()
    for attr in attrs:
        qs |= Q((attr + '__icontains', value))
    return field.choices.filter(qs)


def choice_queryset__parse(field, string_value, **_):
    try:
        return field.model.objects.get(pk=string_value) if string_value else None
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
    return re.match(r'^\+\d{1,3}(( |-)?\(\d+\))?(( |-)?\d+)+$', parsed_data, re.IGNORECASE), 'Please use format +<country code> (XX) XX XX. Example of US number: +1 (212) 123 4567 or +1 212 123 4567'


def multi_choice_choice_to_option(field, choice, **_):
    return choice, "%s" % choice, "%s" % choice, field.value_list and choice in field.value_list


def multi_choice_queryset_choice_to_option(field, choice, **_):
    return choice, choice.pk, "%s" % choice, field.value_list and choice in field.value_list


# TODO: move this class.. maybe lots of other stuff from here
class Action(PagePart):
    tag = Refinable()
    attrs: Dict[str, Any] = Refinable()
    group = Refinable()
    template = Refinable()
    display_name = Refinable()

    @dispatch(
        tag='a',
        attrs=EMPTY,
    )
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.declared_action = None

    @dispatch(
        context=EMPTY,
        render=EMPTY,
    )
    def as_html(self, *, context=None, render=None):
        assert not render
        assert self._is_bound
        if self.template:
            return render_to_string(self.template, dict(**context, action=self))
        else:
            # TODO: use fragment rendering to avoid the bogus </input>
            return format_html(u'<{tag}{attrs}>{display_name}</{tag}>', tag=self.tag, attrs=self.attrs, display_name=self.display_name)

    def __repr__(self):
        return f'<Action: {self.name}>'

    @classmethod
    @class_shortcut(
        tag='button',
    )
    def button(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='button',
        tag='input',
        attrs__type='submit',
        attrs__value='Submit',
        attrs__accesskey='s',
        display_name='',
    )
    def submit(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        icon_classes=[],
    )
    def icon(cls, icon, *, display_name=None, call_target=None, icon_classes=None, **kwargs):
        icon_classes_str = ' '.join(['fa-' + icon_class for icon_class in icon_classes]) if icon_classes else ''
        if icon_classes_str:
            icon_classes_str = ' ' + icon_classes_str
        setdefaults_path(
            kwargs,
            display_name=format_html('<i class="fa fa-{}{}"></i> {}', icon, icon_classes_str, display_name),
        )
        return call_target(**kwargs)

    def on_bind(self) -> None:
        for k, v in self.parent._actions_unapplied_data.get(self.name, {}).items():
            setattr_path(self, k, v)
        self.attrs = evaluate_attrs(self.attrs, action=self)
        evaluated_attributes = [
            'tag',
            'group',
            'template',
            'display_name',
            'name',
            'after',
            'default_child',
            'style',
        ]
        for key in evaluated_attributes:
            self._evaluate_attribute(key)

        self.extra = evaluate_recursive(self.extra, **self.evaluate_attribute_kwargs())
        self.attrs = evaluate_attrs(self.attrs, **self.evaluate_attribute_kwargs())

    def _evaluate_attribute_kwargs(self):
        return dict(action=self)


def group_actions(actions_without_group: Dict[str, Action]):
    grouped_actions = {}
    if actions_without_group is not None:
        actions_with_group = (action for action in actions_without_group.values() if action.group is not None)

        grouped_actions: Dict[str, Tuple[str, str, List[Action]]] = [
            (group_name, slugify(group_name), list(actions_in_group))
            for group_name, actions_in_group in groupby(
                actions_with_group,
                key=lambda l: l.group
            )
        ]  # list(actions_in_group) because django templates touches the generator and then I can't iterate it

        for _, _, group_links in grouped_actions:
            for link in group_links:
                link.attrs.role = 'menuitem'

        actions_without_group = [action for action in actions_without_group.values() if action.group is None]

    return actions_without_group, grouped_actions


@with_meta
class Field(PagePart):
    """
    Class that describes a field, i.e. what input controls to render, the label, etc.

    The life cycle of the data is:
        1. raw_data/raw_data_list: will be set if the corresponding key is present in the HTTP request
        2. parsed_data/parsed_data_list: set if parsing is successful, which only happens if the previous step succeeded
        3. value/value_list: set if validation is successful, which only happens if the previous step succeeded

    The variables *_list should be used if the input is a list.
    """

    attr = Refinable()
    id = Refinable()
    display_name = Refinable()

    # raw_data/raw_data contains the strings grabbed directly from the request data
    raw_data = Refinable()
    raw_data_list = Refinable()

    parse_empty_string_as_none = Refinable()
    initial = Refinable()
    initial_list = Refinable()
    template: str = Refinable()
    template_string = Refinable()
    attrs: Dict[str, Any] = Refinable()
    input_template = Refinable()
    label_template = Refinable()
    errors_template = Refinable()
    required = Refinable()

    input = Refinable()
    label = Refinable()

    is_list = Refinable()
    is_boolean = Refinable()
    model = Refinable()
    model_field = Refinable()

    editable = Refinable()
    strip_input = Refinable()
    input_type = Refinable()

    choices: Callable[['Form', 'Field', str], List[Any]] = Refinable()
    choice_to_option: Callable[['Form', 'Field', str], Tuple[Any, str, str, bool]] = Refinable()
    choice_tuples = Refinable()
    errors: Errors = Refinable()

    empty_label = Refinable()
    empty_choice_tuple = Refinable()

    # TODO: are these two redundant?
    endpoint: Namespace = Refinable()
    endpoint_handler: Callable = Refinable()

    @dispatch(
        attr=MISSING,
        id=MISSING,
        display_name=MISSING,
        attrs__class=EMPTY,
        parse_empty_string_as_none=True,
        required=True,
        is_list=False,
        is_boolean=False,
        editable=True,
        strip_input=True,
        input_type='text',
        endpoint=EMPTY,
        endpoint__config=default_endpoint__config,
        endpoint__validate=default_endpoint__validate,
        input__call_target=Fragment,
        input__tag='input',
        label__call_target=Fragment,
        label__tag='label',
        errors=EMPTY,
        input__attrs__name=lambda field, **_: field.path(),
    )
    def __init__(self, **kwargs):
        """
        Note that, in addition to the parameters with the defined behavior below, you can pass in any keyword argument you need yourself, including callables that conform to the protocol, and they will be added and evaluated as members.

        All these parameters can be callables, and if they are, will be evaluated with the keyword arguments form and field. The only exceptions are is_valid (which gets form, field and parsed_data), render_value (which takes form, field and value) and parse (which gets form, field, string_value). Example of using a lambda to specify a value:

        .. code:: python

            Field(id=lambda form, field: 'my_id_%s' % field.name)

        :param name: the name of the field. This is the key used to grab the data from the form dictionary (normally request.GET or request.POST)
        :param is_valid: validation function. Should return a tuple of (bool, reason_for_failure_if_bool_is_false) or raise ValidationError. Default: lambda form, field, parsed_data: (True, '')
        :param parse: parse function. Default just returns the string input unchanged: lambda form, field, string_value: string_value
        :param initial: initial value of the field
        :param attr: the attribute path to apply or get the data from. For example using "foo__bar__baz" will result in `your_instance.foo.bar.baz` will be set by the apply() function. Defaults to same as name
        :param attrs: a dict containing any custom html attributes to be sent to the input_template.
        :param id: the HTML id attribute. Default: 'id_%s' % name
        :param display_name: the text in the HTML label tag. Default: capitalize(name).replace('_', ' ')
        :param template: django template filename for the entire row. Normally you shouldn't need to override on this level, see input_template, label_template and error_template below.
        :param template_string: You can inline a template string here if it's more convenient than creating a file. Default: None
        :param input_template: django template filename for the template for just the input control.
        :param label_template: django template filename for the template for just the label tab. Default: 'iommi/form/label.html'
        :param errors_template: django template filename for the template for just the errors output. Default: 'iommi/form/errors.html'
        :param required: if the field is a required field. Default: True
        :param help_text: The help text will be grabbed from the django model if specified and available.

        :param editable: default: True
        :param strip_input: runs the input data through standard python .strip() before passing it to the parse function (can NOT be callable). Default: True
        :param input_type: the type attribute on the standard input HTML tag. Default: 'text'
        :param render_value: render the parsed and validated value into a string. Default just converts to unicode: lambda form, field, value: unicode(value)
        :param is_list: interpret request data as a list (can NOT be a callable). Default False
        :param read_from_instance: callback to retrieve value from edited instance. Invoked with parameters field and instance.
        :param write_to_instance: callback to write value to instance. Invoked with parameters field, instance and value.
        """

        super(Field, self).__init__(**kwargs)

        if self.is_list:
            assert self.initial is None, 'The parameter initial is only valid if is_list is False, otherwise use initial_list'
        else:
            assert self.initial_list is None, 'The parameter initial_list is only valid if is_list is True, otherwise use initial'

        # parsed_data/parsed_data contains data that has been interpreted, but not checked for validity or access control
        self.parsed_data = None
        self.parsed_data_list = None

        # value/value_data_list is the final step that contains parsed and valid data
        self.value = None
        self.value_list = None

        self.choice_tuples = None

        self.declared_field = None

        self.input = self.input()
        self.label = self.label()

    def endpoint_kwargs(self):
        return dict(field=self)

    def children(self):
        assert self._is_bound
        return setup_endpoint_proxies(self.endpoint)

    @property
    def form(self):
        return self.parent

    @staticmethod
    @refinable
    def is_valid(form: 'Form', field: 'Field', parsed_data: Any, **_) -> Tuple[bool, str]:
        return True, ''

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
        return "%s" % value if value is not None else ''

    @staticmethod
    @refinable
    def render_value_list(form, field, value_list):
        if value_list:
            return ', '.join(field.render_value(form=form, field=field, value=value) for value in value_list)
        else:
            return ''

    # grab help_text from model if applicable
    # noinspection PyProtectedMember
    @staticmethod
    @refinable
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
        for k, v in self.parent._fields_unapplied_data.get(self.name, {}).items():
            setattr_path(self, k, v)

        form = self.parent
        if self.attr is MISSING:
            self.attr = self.name
        if self.id is MISSING:
            self.id = f'id_{self.path()}'.replace(DISPATCH_PATH_SEPARATOR, '__') if self.name else ''
        if self.display_name is MISSING:
            self.display_name = capitalize(self.name).replace('_', ' ') if self.name else ''

        # TODO: ??
        self.field = self
        self.errors = Errors(parent=self, **self.errors)

        if form.editable is False:
            self.editable = False

        self.declared_field = self._declared

    def _evaluate(self):
        """
        Evaluates callable/lambda members. After this function is called all members will be values.
        """
        evaluated_attributes = [
            'name',
            'show',
            'attr',
            'id',
            'display_name',
            'after',
            'parse_empty_string_as_none',
            'template',
            'template_string',
            'input_template',
            'label_template',
            'errors_template',
            'required',
            'initial',
            'is_list',
            'is_boolean',
            'model_field',
            'editable',
            'strip_input',
            'input_type',
            'choices',
            'choice_tuples',
            'empty_label',
            'empty_choice_tuple',
            'help_text',
            # This is useful for example when doing file upload. In that case the data is on request.FILES, not request.POST so we can use this to grab it from there
            'raw_data',
            'raw_data_list',
        ]
        for key in evaluated_attributes:
            self._evaluate_attribute(key)

        # non-strict because the model is callable at the end. Not ideal, but what can you do?
        self._evaluate_attribute('model', strict=False)

        self.attrs = evaluate_attrs(self.attrs, **self.evaluate_attribute_kwargs())

        self.extra = evaluate_recursive(self.extra, **self.evaluate_attribute_kwargs())

        self.input = self.input.bind(parent=self)
        self.label = self.label.bind(parent=self)
        # TODO: special class for label that does this?
        assert not self.label._children
        self.label._children = [self.display_name]

        if not self.editable:
            # TODO: style!
            self.input_template = 'iommi/form/non_editable.html'

    def _evaluate_attribute_kwargs(self):
        return dict(form=self.parent, field=self)

    @property
    def rendered_value(self):
        if self.errors:
            return self.raw_data
        if self.is_list:
            return self.render_value_list(form=self.form, field=self, value_list=self.value_list)
        else:
            return self.render_value(form=self.form, field=self, value=self.value)

    def __repr__(self):
        return '<{}.{} {}>'.format(self.__class__.__module__, self.__class__.__name__, self.name)

    def choice_to_options_selected(self):
        if self.is_list:
            if self.value_list is None:
                return

            for v in self.value_list:
                yield self.choice_to_option(form=self.parent, field=self, choice=v)
        else:
            if self.value is None:
                return
            yield self.choice_to_option(form=self.parent, field=self, choice=self.value)

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
    def as_html(self, *, context=None, render=None):
        assert not render
        context = {
            'form': self.form,
            'field': self,
        }
        if self.template_string is not None:
            return get_template_from_string(self.template_string, origin='iommi', name='Form.as_html').render(context, self.request())
        else:
            return render_template(self.request(), self.template, context)

    @classmethod
    @class_shortcut(
        input_type='hidden',
        attrs__style__display='none',
    )
    def hidden(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        input_type='text',
    )
    def text(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        input_template='iommi/form/text.html',
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
        input_type='password',
    )
    def password(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    # Boolean field. Tries hard to parse a boolean value from its input.
    @classmethod
    @class_shortcut(
        parse=lambda string_value, **_: bool_parse(string_value),
        required=False,
        input__attrs__type='checkbox',
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
        input_template='iommi/form/choice.html',
    )
    def choice(cls, call_target=None, **kwargs):
        """
        Shortcut for single choice field. If required is false it will automatically add an option first with the value '' and the title '---'. To override that text pass in the parameter empty_label.
        :param empty_label: default '---'
        :param choices: list of objects
        :param choice_to_option: callable with three arguments: form, field, choice. Convert from a choice object to a tuple of (choice, value, label, selected), the last three for the <option> element
        """
        assert 'choices' in kwargs

        original_post_validation = kwargs.get('post_validation')

        def _choice_post_validation(form, field):
            choice_post_validation(form=form, field=field)
            if original_post_validation:
                original_post_validation(form=form, field=field)

        kwargs['post_validation'] = _choice_post_validation

        setdefaults_path(
            kwargs,
            empty_choice_tuple=(None, '', kwargs['empty_label'], True),
        )

        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute="choice",
        choices=[True, False],
        parse=choice_parse,
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
        input_template='iommi/form/choice_select2.html',
        parse=choice_queryset__parse,
        choice_to_option=choice_queryset__choice_to_option,
        endpoint_handler=choice_queryset__endpoint_handler,
        is_valid=choice_queryset__is_valid,
        extra__filter_and_sort=choice_queryset__extra__filter_and_sort,
        extra__model_from_choices=choice_queryset__extra__model_from_choices,
        extra__current_selection_json=choice_queryset__extra__current_selection_json,
    )
    def choice_queryset(cls, choices, call_target=None, **kwargs):
        from django.db.models import QuerySet
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
        attrs__multiple=True,
        choice_to_option=multi_choice_choice_to_option,
        is_list=True,
    )
    def multi_choice(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice_queryset',
        attrs__multiple=True,
        choice_to_option=multi_choice_queryset_choice_to_option,
        is_list=True,
    )
    def multi_choice_queryset(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='choice',
        input_template='iommi/form/radio.html',
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
        input_type='url',
        parse=url_parse,
    )
    def url(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        input_type='file',
        # TODO: yuck!
        template_string="{% extends 'iommi/form/{style}/row.html' %}{% block extra_content %}{{ field.value }}{% endblock %}",
        input_template='iommi/form/file.html',
        write_to_instance=file_write_to_instance,
    )
    def file(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    # Shortcut to create a fake input that performs no parsing but is useful to separate sections of a form.
    @classmethod
    @class_shortcut(
        show=True,
        template='iommi/form/heading.html',
        editable=False,
        attr=None,
        # TODO: this type of thing seems like it's irrelevant after fields=[...] is removed
        name='@@heading@@',
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
        input_type='email',
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
        kwargs['model'] = model_field.remote_field.model
        return call_target(model_field=model_field, **kwargs)


def get_fields(model):
    # noinspection PyProtectedMember
    for field in model._meta.get_fields():
        yield field


@no_copy_on_bind
@declarative(Field, '_fields_dict')
@with_meta
class Form(PagePart):
    """
    Describe a Form. Example:

    .. code:: python

        class MyForm(Form):
            a = Field()
            b = Field.email()

        form = MyForm(request=request)

    You can also create an instance of a form with this syntax if it's more convenient:

    .. code:: python

        form = MyForm(request=request, fields=[Field(name='a'), Field.email(name='b')])

    See tri.declarative docs for more on this dual style of declaration.
"""
    is_full_form = Refinable()
    actions = Refinable()
    actions_template: Union[str, Template] = Refinable()
    attrs: Dict[str, Any] = Refinable()
    editable = Refinable()

    model = Refinable()
    """ :type: django.db.models.Model """
    endpoint: Namespace = Refinable()
    member_class: Type[Field] = Refinable()
    action_class: Type[Action] = Refinable()
    template: Union[str, Template] = Refinable()

    class Meta:
        member_class = Field
        action_class = Action

    def __repr__(self):
        return f'<Form: {self.name} at path {self.path() if self.parent else "<unbound>"}>'

    def children(self):
        assert self._is_bound
        return Struct(
            field=Struct(
                name='field',
                children=lambda: self.fields,
                default_child=True,  # TODO: unsure about this
                endpoint_kwargs=lambda: dict(form=self),
            ),
            actions=Struct(
                name='actions',
                children=lambda: self.actions,
                endpoint_kwargs=lambda: dict(form=self),
            ),
            # TODO: this is a potential name conflict with field and actions above
            **setup_endpoint_proxies(self.endpoint)
        )

    # TODO: should this just be _evaluate_attribute_kwargs?
    def endpoint_kwargs(self):
        return dict(form=self)

    @staticmethod
    @refinable
    def post_handler(form, **_):
        return None

    @dispatch(
        is_full_form=True,
        model=None,
        editable=True,
        fields=EMPTY,
        attrs__action='',
        attrs__method='post',
        endpoint=EMPTY,
        actions__submit__call_target=Action.submit,
    )
    def __init__(self, *, instance=None, fields: Dict[str, Field] = None, _fields_dict: Dict[str, Field] = None, actions: Dict[str, Any] = None, **kwargs):

        super(Form, self).__init__(**kwargs)

        assert isinstance(fields, dict)

        self.fields = None
        """ :type: Struct[str, Field] """
        self.errors: Set[str] = set()
        self._valid = None
        self.instance = instance
        self.mode = INITIALS_FROM_GET

        self._actions_unapplied_data = {}
        self.declared_actions = collect_members(items=actions, cls=self.get_meta().action_class, unapplied_config=self._actions_unapplied_data)
        self.actions = None

        self._fields_unapplied_data = {}
        self.declared_fields = collect_members(items=fields, items_dict=_fields_dict, cls=self.get_meta().member_class, unapplied_config=self._fields_unapplied_data)
        self.fields: Dict[str, Field] = None

    def on_bind(self) -> None:
        assert self.actions_template
        self._valid = None
        request = self.request()
        self._request_data = request_data(request) if request else None

        if self._request_data is not None and self.is_target():
            self.mode = FULL_FORM_FROM_REQUEST

        # TODO: seems a bit convoluted to do this and the None check above
        if self._request_data is None:
            self._request_data = {}

        self.actions = bind_members(declared_items=self.declared_actions, parent=self)
        self.fields = bind_members(declared_items=self.declared_fields, parent=self)

        if self.instance is not None:
            for field in self.fields.values():
                if field.attr:
                    initial = field.read_from_instance(field, self.instance)

                    # TODO: we always overwrite here, even if we got passed something.. seems strange
                    if field.is_list:
                        field.initial_list = initial
                    else:
                        field.initial = initial

        if self._request_data is not None:
            for field in self.fields.values():
                if field.is_list:
                    if field.raw_data_list is not None:
                        continue
                    try:
                        # django and similar
                        # noinspection PyUnresolvedReferences
                        raw_data_list = self._request_data.getlist(field.path())
                    except AttributeError:  # pragma: no cover
                        # werkzeug and similar
                        raw_data_list = self._request_data.get(field.path())

                    if raw_data_list and field.strip_input:
                        raw_data_list = [x.strip() for x in raw_data_list]

                    if raw_data_list is not None:
                        field.raw_data_list = raw_data_list
                else:
                    if field.raw_data is not None:
                        continue
                    field.raw_data = self._request_data.get(field.path())
                    if field.raw_data and field.strip_input:
                        field.raw_data = field.raw_data.strip()

        for field in self.fields.values():
            field._evaluate()

        self.attrs = evaluate_attrs(self.attrs, **self.evaluate_attribute_kwargs())

        self.is_valid()

    def _evaluate_attribute_kwargs(self):
        return dict(form=self)

    def render_actions(self):
        assert self._is_bound, 'The form has not been bound. You need to call bind() either explicitly, or pass data/request to the constructor to cause an indirect bind()'
        actions, grouped_actions = group_actions(self.actions)
        return render_template(
            self.request(),
            self.actions_template,
            dict(
                actions=actions,
                grouped_actions=grouped_actions,
                form=self,
            ))

    @classmethod
    @dispatch(
        fields=EMPTY,
    )
    def fields_from_model(cls, fields, **kwargs):
        return create_members_from_model(
            member_params_by_member_name=fields,
            default_factory=cls.get_meta().member_class.from_model,
            **kwargs
        )

    @classmethod
    @dispatch(
        fields=EMPTY,
    )
    def from_model(cls, *, model, fields, instance=None, include=None, exclude=None, extra_fields=None, **kwargs):
        """
        Create an entire form based on the fields of a model. To override a field parameter send keyword arguments in the form
        of "the_name_of_the_fields__param". For example:

        .. code:: python

            class Foo(Model):
                foo = IntegerField()

            Form.from_model(request=request, model=Foo, fields__foo__help_text='Overridden help text')

        :param include: fields to include. Defaults to all
        :param exclude: fields to exclude. Defaults to none (except that AutoField is always excluded!)

        """
        fields = cls.fields_from_model(model=model, include=include, exclude=exclude, extra=extra_fields, fields=fields)
        return cls(model=model, instance=instance, fields=fields, **kwargs)

    def own_target_marker(self):
        return f'-{self.path()}'

    def is_target(self):
        return self.own_target_marker() in self._request_data

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

    def parse_field_raw_value(self, field, raw_data):
        try:
            return field.parse(form=self, field=field, string_value=raw_data)
        except ValueError as e:
            assert str(e) != ''
            field.errors.add(str(e))
        except ValidationError as e:
            for message in e.messages:
                msg = "%s" % message
                assert msg != ''
                field.errors.add(msg)

    def parse(self):
        for field in self.fields.values():
            if not field.editable:
                continue

            if self.mode is INITIALS_FROM_GET and field.raw_data is None and field.raw_data_list is None:
                continue

            if field.is_list:
                if field.raw_data_list is not None:
                    field.parsed_data_list = [self.parse_field_raw_value(field, x) for x in field.raw_data_list]
                else:
                    field.parsed_data_list = None
            elif field.is_boolean:
                field.parsed_data = self.parse_field_raw_value(field, '0' if field.raw_data is None else field.raw_data)
            else:
                if field.raw_data == '' and field.parse_empty_string_as_none:
                    field.parsed_data = None
                elif field.raw_data is not None:
                    field.parsed_data = self.parse_field_raw_value(field, field.raw_data)
                else:
                    field.parsed_data = None

    def validate(self):
        self.parse()

        for field in self.fields.values():
            if (not field.editable) or (self.mode is INITIALS_FROM_GET and field.raw_data is None and field.raw_data_list is None):
                if field.is_list:
                    field.value_list = field.initial_list
                else:
                    field.value = field.initial
                continue

            value = None
            value_list = None
            if field.is_list:
                if field.parsed_data_list is not None:
                    value_list = [self.validate_field_parsed_data(field, x) for x in field.parsed_data_list if x is not None]
            else:
                if field.parsed_data is not None:
                    value = self.validate_field_parsed_data(field, field.parsed_data)

            if not field.errors:
                if self.mode is FULL_FORM_FROM_REQUEST and field.required and value in [None, ''] and not value_list:
                    field.errors.add('This field is required')
                else:
                    field.value = value
                    field.value_list = value_list

        for field in self.fields.values():
            field.post_validation(form=self, field=field)
        self.post_validation(form=self)
        return self

    @staticmethod
    @refinable
    def post_validation(form):
        pass

    def validate_field_parsed_data(self, field, value):
        is_valid, error = field.is_valid(
            form=self,
            field=field,
            parsed_data=value)
        if is_valid and not field.errors and field.parsed_data is not None:
            value = field.parsed_data
        elif not is_valid and self.mode:
            if not isinstance(error, set):
                error = {error}
            for e in error:
                assert error != ''
                field.errors.add(e)
        return value

    def add_error(self, msg):
        self.errors.add(msg)

    def render_fields(self):
        r = []
        for field in self.fields.values():
            r.append(field.as_html())

        if self.is_full_form:
            r.append(format_html(AVOID_EMPTY_FORM, self.path()))

        # We need to preserve all other GET parameters, so we can e.g. filter in two forms on the same page, and keep sorting after filtering
        own_field_paths = {f.path() for f in self.fields.values()}
        for k, v in self.request().GET.items():
            if k == self.own_target_marker():
                continue
            # TODO: why is there a special case for '-' here?
            if k not in own_field_paths and k != '-':
                r.append(format_html('<input type="hidden" name="{}" value="{}" />', k, v))

        return format_html('{}\n' * len(r), *r)

    @dispatch(
        render__call_target=render_template_name,
        context=EMPTY,
    )
    def as_html(self, *, context=None, render=None):
        # TODO: what if self.template is a Template?
        setdefaults_path(
            render,
            context=context,
            template_name=self.template,
        )

        request = self.request()
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
            field.value_list = field.initial_list

        if field.attr is not None:
            field.write_to_instance(field, instance, field.value_list if field.is_list else field.value)

    def get_errors(self):
        r = {}
        if self.errors:
            r['global'] = self.errors
        field_errors = {x.name: x.errors for x in self.fields.values() if x.errors}
        if field_errors:
            r['fields'] = field_errors
        return Errors(parent=self, **r)

    @classmethod
    @class_shortcut(
        call_target__attribute='from_model',
        extra__model_verbose_name=None,
        on_save=lambda **kwargs: None,  # pragma: no mutate
        redirect=lambda redirect_to, **_: HttpResponseRedirect(redirect_to),
        redirect_to=None,
        parts=EMPTY,
        extra__title=None,
        default_child=True,
        post_handler=create_or_edit_object__post_handler,
    )
    def as_create_or_edit_page(cls, *, call_target=None, extra=None, model=None, instance=None, on_save=None, redirect=None, redirect_to=None, parts=None, name, **kwargs):
        assert 'request' not in kwargs, "I'm afraid you can't do that Dave"
        if model is None and instance is not None:
            model = type(instance)

        if extra.model_verbose_name is None:
            assert model, 'If there is no model, you must specify extra__model_verbose_name, so we can create the title; or specify title.'
            # noinspection PyProtectedMember
            extra.model_verbose_name = model._meta.verbose_name.replace('_', ' ')

        if extra.title is None:
            extra.title = '%s %s' % ('Create' if extra.is_create else 'Save', extra.model_verbose_name)
        extra.on_save = on_save
        extra.redirect = redirect
        extra.redirect_to = redirect_to

        setdefaults_path(
            kwargs,
            actions__submit=dict(
                # TODO: should be call target attribute
                call_target=Action.submit,
                attrs__value=extra.title,
                attrs__name=name,
            ),
        )

        from iommi.page import Page
        from iommi.page import html
        return Page(
            parts={
                # TODO: do we really need to pop from parts ourselves here?
                'title': html.h1(extra.title, **parts.pop('title', {})),
                name: call_target(extra=extra, model=model, instance=instance, **kwargs),
                **parts
            }
        )

    @classmethod
    @class_shortcut(
        call_target__attribute='as_create_or_edit_page',
        name='create',
        extra__is_create=True,
    )
    def as_create_page(cls, *, name, call_target=None, **kwargs):
        return call_target(name=name or 'create', **kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute='as_create_or_edit_page',
        name='edit',
        extra__is_create=False,
    )
    def as_edit_page(cls, *, name, call_target=None, instance, **kwargs):
        return call_target(instance=instance, name=name or 'edit', **kwargs)


def create_or_edit_object_redirect(is_create, redirect_to, request, redirect, form):
    if redirect_to is None:
        if is_create:
            redirect_to = "../"
        else:
            redirect_to = "../../"  # We guess here that the path ends with '<pk>/edit/' so this should end up at a good place
    return redirect(request=request, redirect_to=redirect_to, form=form)
