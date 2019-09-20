from __future__ import (
    absolute_import,
    unicode_literals,
)

import copy
import json
import re
import six
import warnings
from collections import OrderedDict
from datetime import datetime
from decimal import (
    Decimal,
    InvalidOperation,
)
from itertools import (
    chain,
    groupby,
)
from tri_declarative import (
    assert_kwargs_empty,
    class_shortcut,
    creation_ordered,
    declarative,
    dispatch,
    EMPTY,
    evaluate_recursive,
    flatten,
    getattr_path,
    Namespace,
    Refinable,
    refinable,
    RefinableObject,
    setattr_path,
    setdefaults_path,
    shortcut,
    Shortcut,
    should_show,
    sort_after,
    with_meta,
    evaluate)
from tri_struct import Struct

from tri_form.compat import (
    field_defaults_factory,
    format_html,
    get_template_from_string,
    render_template,
    render_to_string,
    setup_db_compat,
    slugify,
    URLValidator,
    validate_email,
    ValidationError,
)
from tri_form.render import render_attrs
from .compat import HttpResponse

# Prevent django templates from calling That Which Must Not Be Called
Namespace.do_not_call_in_templates = True

__version__ = '7.1.0'  # pragma: no mutate


def capitalize(s):
    return s[0].upper() + s[1:] if s else s


# This input is added to all forms. It is used to circumvent the fact that unchecked checkboxes are not sent as
# parameters in the request. More specifically, the problem occurs when the checkbox is checked by default,
# as it would not be possible to distinguish between the initial request and a subsequent request where the checkbox
# is unchecked. By adding this input, it is possible to make this distinction as subsequent requests will contain
# (at least) this key-value.
AVOID_EMPTY_FORM = '<input type="hidden" name="-" value="-" />'

FULL_FORM_FROM_REQUEST = 'full_form_from_request'  # pragma: no mutate The string is just to make debugging nice
INITIALS_FROM_GET = 'initials_from_get'  # pragma: no mutate The string is just to make debugging nice

DISPATCH_PATH_SEPARATOR = '/'


def dispatch_prefix_and_remaining_from_key(key):
    prefix, _, remaining_key = key.partition(DISPATCH_PATH_SEPARATOR)
    return prefix, remaining_key


def handle_dispatch(request, obj):
    for key, value in request.GET.items():
        if key.startswith(DISPATCH_PATH_SEPARATOR):
            remaining_key = key[len(DISPATCH_PATH_SEPARATOR):]
            expected_prefix = obj.endpoint_dispatch_prefix
            if expected_prefix is not None:
                prefix, remaining_key = dispatch_prefix_and_remaining_from_key(remaining_key)
                if prefix != expected_prefix:
                    return True, None
                if remaining_key == '':
                    remaining_key = None
            data = obj.endpoint_dispatch(key=remaining_key, value=value)
            if data is not None:
                return True, HttpResponse(json.dumps(data), content_type='application/json')
    return False, None


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


_field_factory_by_field_type = OrderedDict()


def register_field_factory(field_class, factory):
    _field_factory_by_field_type[field_class] = factory


MISSING = object()


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
            subkeys = Namespace(**member_params_by_member_name.pop(field.name, {}))
            subkeys.setdefault('call_target', default_factory)
            foo = subkeys(name=field.name, model=model, model_field=field)
            if foo is None:
                continue
            if isinstance(foo, list):
                members.extend(foo)
            else:
                members.append(foo)
    assert_kwargs_empty(member_params_by_member_name)
    return members + (extra if extra is not None else []) + [default_factory(model=model, field_name=x) for x in extra_includes]


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
        for django_field_type, foo in reversed(factory_lookup.items()):
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
    field=EMPTY,
)
def expand_member(cls, model, factory_lookup, defaults_factory, name, field, field_name=None, model_field=None):
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
            **field.pop(sub_model_field.name, {})
        )
        for sub_model_field in get_fields(model=model_field.remote_field.model)
    ]
    assert_kwargs_empty(field)
    return [x for x in result if x is not None]


def render_css_classes(classes):
    """
    Render CSS classes, or return '' if no attributes needs to be rendered.
    """
    warnings.warn('render_css_classes is deprecated, use tri.form.render.render_attrs instead', DeprecationWarning)
    return '' if not classes else format_html(' class="{}"', ' '.join(sorted(classes)))  # pragma: no mutate, we'll delete this function anyway


def default_endpoint__config(field, key, value, **_):
    # type: (Field, str, str) -> dict
    return dict(
        name=field.name,
    )


def default_endpoint__validate(field, key, value, **_):
    return dict(
        valid=not bool(field.errors),
        errors=list(field.errors),
    )


def float_parse(string_value, **_):
    try:
        return float(string_value)
    except ValueError:
        # Acrobatics so we get equal formatting in python 2/3
        raise ValueError("could not convert string to float: %s" % string_value)


def int_parse(string_value, **_):
    return int(string_value)


def choice_is_valid(form, field, parsed_data):
    del form
    return parsed_data in field.choices, '%s not in available choices' % parsed_data


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


def choice_queryset_is_valid(field, parsed_data, **_):
    return field.choices.filter(pk=parsed_data.pk).exists(), '%s not in available choices' % (field.raw_data or ', '.join(field.raw_data_list))


def choice_queryset_endpoint__select2(field, value, **_):
    limit = 10  # pragma: no mutate
    result = field.choices.filter(**{field.extra.endpoint_attr + '__icontains': value}).values_list(*['pk', field.extra.endpoint_attr])
    return [
        dict(
            id=row[0],
            text=row[1],
        )
        for row in result[:limit]
    ]


def choice_queryset_parse(field, string_value, **_):
    try:
        return field.model.objects.get(pk=string_value) if string_value else None
    except field.model.DoesNotExist as e:
        raise ValidationError(str(e))


def choice_queryset_choice_to_option(field, choice, **_):
    return choice, choice.pk, "%s" % choice, choice == field.value


def choice_queryset_endpoint_path(form, field):
    return DISPATCH_PATH_SEPARATOR + DISPATCH_PATH_SEPARATOR.join(part for part in [form.endpoint_dispatch_prefix, 'field', field.name] if part is not None)


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


def evaluate_and_group_links(links, **kwargs):
    grouped_links = {}
    if links is not None:
        links = [link.bind(**kwargs) for link in links]
        links = [link for link in links if link.show]

        grouped_links = groupby((link for link in links if link.group is not None), key=lambda l: l.group)
        grouped_links = [(g, slugify(g), list(lg)) for g, lg in grouped_links]  # list(lg) because django templates touches the generator and then I can't iterate it

        for _, _, group_links in grouped_links:
            for link in group_links:
                link.attrs.role = 'menuitem'

        links = [link for link in links if link.group is None]

    return links, grouped_links


@six.python_2_unicode_compatible
class Link(RefinableObject):
    tag = Refinable()
    attrs = Refinable()
    group = Refinable()
    show = Refinable()
    template = Refinable()
    extra = Refinable()
    title = Refinable()

    @dispatch(
        tag='a',
        attrs=EMPTY,
        show=True,
        extra=EMPTY,
    )
    def __init__(self, title, **kwargs):
        super(Link, self).__init__(title=title, **kwargs)

    def bind(self, **kwargs):
        kwargs = {k: evaluate_recursive(getattr(self, k), **kwargs)
                  for k in self.get_declared('refinable_members')}
        return type(self)(**kwargs)

    def render_attrs(self):
        return render_attrs(self.attrs)

    def render(self):
        if self.template:
            return render_to_string(self.template, dict(link=self))
        else:
            return format_html(u'<{tag}{attrs}>{title}</{tag}>', tag=self.tag, attrs=self.render_attrs(), title=self.title)

    @property
    def rendered(self):
        return self.render()

    def __str__(self):
        return self.render()

    def __html__(self):
        return self.render()

    def __repr__(self):
        return '<Link: %s>' % self.title


@shortcut
@dispatch(
    call_target=Link,
    icon_classes=[],
)
def link_shortcut_icon(icon, title, call_target, **kwargs):
    icon_classes = kwargs.pop('icon_classes')
    icon_classes_str = ' '.join(['fa-' + icon_class for icon_class in icon_classes]) if icon_classes else ''
    setdefaults_path(
        kwargs,
        title=format_html('<i class="fa fa-{}{}"></i> {}', icon, icon_classes_str, title),
    )
    return call_target(**kwargs)


Link.icon = staticmethod(link_shortcut_icon)

Link.button = Shortcut(
    call_target=Link,
    tag='button',
    attrs__class__button=True,
)

Link.submit = Shortcut(
    call_target=Link.button,
    tag='input',
    attrs__type='submit',
    attrs__value='Submit',
    attrs__accesskey='s',
    title='',
)


@creation_ordered
class Field(RefinableObject):
    """
    Class that describes a field, i.e. what input controls to render, the label, etc.
    """

    name = Refinable()

    show = Refinable()

    attr = Refinable()
    id = Refinable()
    display_name = Refinable()

    after = Refinable()

    # raw_data/raw_data contains the strings grabbed directly from the request data
    raw_data = Refinable()
    raw_data_list = Refinable()

    parse_empty_string_as_none = Refinable()
    initial = Refinable()
    initial_list = Refinable()
    template = Refinable()
    template_string = Refinable()
    attrs = Refinable()
    input_template = Refinable()
    label_template = Refinable()
    errors_template = Refinable()
    required = Refinable()

    container = Refinable()
    label_container = Refinable()
    input_container = Refinable()

    is_list = Refinable()
    is_boolean = Refinable()
    model = Refinable()
    model_field = Refinable()

    editable = Refinable()
    strip_input = Refinable()
    input_type = Refinable()

    extra = Refinable()

    choices = Refinable()  # type: (Form, Field, str) -> None
    choice_to_option = Refinable()
    choice_tuples = Refinable()

    empty_label = Refinable()
    empty_choice_tuple = Refinable()

    endpoint = Refinable()
    endpoint_path = Refinable()

    @dispatch(
        attr=MISSING,
        id=MISSING,
        display_name=MISSING,
        show=True,
        extra=EMPTY,
        attrs__class=EMPTY,
        parse_empty_string_as_none=True,
        required=True,
        template='tri_form/{style}_form_row.html',
        input_template='tri_form/input.html',
        label_template='tri_form/label.html',
        errors_template='tri_form/errors.html',
        is_list=False,
        is_boolean=False,
        editable=True,
        strip_input=True,
        input_type='text',
        endpoint=EMPTY,
        endpoint__config=default_endpoint__config,
        endpoint__validate=default_endpoint__validate,
        container__attrs=EMPTY,
        label_container__attrs__class__description_container=True,
        input_container__attrs=EMPTY,
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
        :param label: the text in the HTML label tag. Default: capitalize(name).replace('_', ' ')
        :param template: django template filename for the entire row. Normally you shouldn't need to override on this level, see input_template, label_template and error_template below. Default: 'tri_form/{style}_form_row.html'
        :param template_string: You can inline a template string here if it's more convenient than creating a file. Default: None
        :param input_template: django template filename for the template for just the input control. Default: 'tri_form/input.html'
        :param label_template: django template filename for the template for just the label tab. Default: 'tri_form/label.html'
        :param errors_template: django template filename for the template for just the errors output. Default: 'tri_form/errors.html'
        :param required: if the field is a required field. Default: True
        :param container__attrs: extra html attributes to set on the container (i.e. row if rendering as a table). Default: set()
        :param help_text: The help text will be grabbed from the django model if specified and available. Default: lambda form, field: '' if form.model is None else form.model._meta.get_field_by_name(field.name)[0].help_text or ''

        :param editable: default: True
        :param strip_input: runs the input data through standard python .strip() before passing it to the parse function (can NOT be callable). Default: True
        :param input_type: the type attribute on the standard input HTML tag. Default: 'text'
        :param render_value: render the parsed and validated value into a string. Default just converts to unicode: lambda form, field, value: unicode(value)
        :param is_list: interpret request data as a list (can NOT be a callable). Default False
        :param read_from_instance: callback to retrieve value from edited instance. Invoked with parameters field and instance.
        :param write_to_instance: callback to write value to instance. Invoked with parameters field, instance and value.
        """

        if 'container_css_classes' in kwargs:
            warnings.warn('container_css_classes is deprecated, use container__attrs__class instead', DeprecationWarning)
            kwargs['container']['attrs']['class'] = {k: True for k in kwargs.pop('container_css_classes')}

        if 'label_container_css_classes' in kwargs:
            warnings.warn('label_container_css_classes is deprecated, use label_container__attrs__class instead', DeprecationWarning)
            kwargs['label_container']['attrs']['class'] = {k: True for k in kwargs.pop('label_container_css_classes')}

        if 'input_container_css_classes' in kwargs:
            warnings.warn('input_container_css_classes is deprecated, use input_container__attrs__class instead', DeprecationWarning)
            kwargs['input_container']['attrs']['class'] = {k: True for k in kwargs.pop('input_container_css_classes')}

        super(Field, self).__init__(**kwargs)

        if self.is_list:
            assert self.initial is None, 'The parameter initial is only valid if is_list is False, otherwise use initial_list'
        else:
            assert self.initial_list is None, 'The parameter initial_list is only valid if is_list is True, otherwise use initial'

        # Bound field data
        self.form = None
        self.field = None
        self.errors = None

        # parsed_data/parsed_data contains data that has been interpreted, but not checked for validity or access control
        self.parsed_data = None
        self.parsed_data_list = None

        # value/value_data_list is the final step that contains parsed and valid data
        self.value = None
        self.value_list = None

        self.choice_tuples = None

    @staticmethod
    @refinable
    def is_valid(form, field, parsed_data):
        # type: (Form, Field, object) -> (bool, str)
        return True, ''

    @staticmethod
    @refinable
    def parse(form, field, string_value, **_):
        # type: (Form, Field, str, **_) -> object
        del form, field
        return string_value

    @staticmethod
    @refinable
    def post_validation(form, field, **_):
        # type: (Form, Field, **_) -> None
        pass

    @staticmethod
    @refinable
    def render_value(form, field, value):
        # type: (Form, Field, object) -> str
        return "%s" % value if value is not None else ''

    @staticmethod
    @refinable
    def render_value_list(form, field, value_list):
        if value_list:
            return ', '.join(field.render_value(form=form, field=field, value=value) for value in value_list)
        else:
            return ''

    @property
    def choice_tuples_property(self):
        return self.choice_tuples()

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
    def read_from_instance(field, instance):
        # type: (Field, object) -> None
        return getattr_path(instance, field.attr)

    @staticmethod
    @refinable
    def write_to_instance(field, instance, value):
        # type: (Field, object, object) -> None
        setattr_path(instance, field.attr, value)

    @staticmethod
    @refinable
    def endpoint_dispatch(field, key, **kwargs):
        prefix, remaining_key = dispatch_prefix_and_remaining_from_key(key)

        endpoint = field.endpoint.get(prefix, None)
        if endpoint is not None:
            return endpoint(field=field, key=remaining_key, **kwargs)

    """
    An internal class that is used to handle the mutable data used during parsing and validation of a Field.

    The life cycle of the data is:
        1. raw_data/raw_data_list: will be set if the corresponding key is present in the HTTP request
        2. parsed_data/parsed_data_list: set if parsing is successful, which only happens if the previous step succeeded
        3. value/value_list: set if validation is successful, which only happens if the previous step succeeded

    The variables *_list should be used if the input is a list.
    """

    def _bind(self, form):
        bound_field = copy.copy(self)  # type: Field

        if bound_field.attr is MISSING:
            bound_field.attr = bound_field.name
        if bound_field.id is MISSING:
            bound_field.id = 'id_%s' % bound_field.name if bound_field.name else ''
        if bound_field.display_name is MISSING:
            bound_field.display_name = capitalize(bound_field.name).replace('_', ' ') if bound_field.name else ''

        bound_field.form = form
        bound_field.field = self
        bound_field.errors = set()

        if form.editable is False:
            bound_field.editable = False

        return bound_field

    def _evaluate_attribute(self, key):
        value = getattr(self, key)
        new_value = evaluate_recursive(value, form=self.form, field=self)
        if new_value is not value:
            setattr(self, key, new_value)

    def _evaluate_show(self):
        self._evaluate_attribute('show')

    def _evaluate(self):
        """
        Evaluates callable/lambda members. After this function is called all members will be values.
        """
        not_evaluated_attributes = {'post_validation', 'show'}
        evaluated_attributes = (x for x in self.get_declared('refinable_members').keys() if x not in not_evaluated_attributes)
        for key in evaluated_attributes:
            self._evaluate_attribute(key)

        if not self.editable:
            self.input_template = 'tri_form/non_editable.html'

    @property
    def rendered_value(self):
        if self.errors:
            return self.raw_data
        if self.is_list:
            return self.render_value_list(form=self.form, field=self, value_list=self.value_list)
        else:
            return self.render_value(form=self.form, field=self, value=self.value)

    def render_attrs(self):
        """
        Render HTML attributes, or return '' if no attributes needs to be rendered.
        """
        return render_attrs(self.attrs)

    @property
    def rendered_attrs(self):
        return self.render_attrs()

    def get_container_attrs(self):
        container_attrs = Namespace(flatten(self.container.attrs))
        if self.required and self.editable:
            container_attrs.setdefault('class', dict())['required'] = True
        if self.form.style == 'compact':
            container_attrs.setdefault('class', dict())['key-value'] = True
        return container_attrs

    @property
    def rendered_container_attrs(self):
        return render_attrs(self.get_container_attrs())

    def render_container_css_classes(self):
        warnings.warn('render_container_css_classes is deprecated, use rendered_container_attrs instead', DeprecationWarning)
        return render_css_classes(self.get_container_attrs().get('class', {}))

    def render_label_container_css_classes(self):
        warnings.warn('render_label_container_css_classes is deprecated, use rendered_container_attrs instead', DeprecationWarning)
        return render_css_classes(self.label_container_attrs.get('class', {}))

    @property
    def rendered_label_container_attrs(self):
        return render_attrs(self.label_container.attrs)

    def render_input_container_css_classes(self):
        warnings.warn('render_input_container_css_classes is deprecated, use rendered_input_attrs instead', DeprecationWarning)
        return render_css_classes(self.label_container_attrs.get('class', {}))

    @property
    def rendered_input_container_css_classes(self):
        return self.render_input_container_css_classes()

    @property
    def rendered_input_container_attrs(self):
        return render_attrs(self.input_container.attrs)

    def __repr__(self):
        return '<{}.{} {}>'.format(self.__class__.__module__, self.__class__.__name__, self.name)

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

    @classmethod
    def from_model_expand(cls, model, field_name=None, model_field=None, **kwargs):
        return expand_member(
            cls=cls,
            model=model,
            factory_lookup=_field_factory_by_field_type,
            defaults_factory=field_defaults_factory,
            field_name=field_name,
            model_field=model_field,
            **kwargs)

    def render(self, style='compact'):
        context = {
            'form': self.form,
            'field': self,
        }
        if self.template_string is not None:
            return get_template_from_string(self.template_string, origin='tri.form', name='Form.render').render(context, self.form.request)
        else:
            return render_template(self.form.request, self.template.format(style=style), context)

    @classmethod
    @class_shortcut(
        input_type='hidden',
        container__attrs__style__display='none',
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
        input_template='tri_form/text.html',
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
        template='tri_form/{style}_form_row_checkbox.html',
        input_template='tri_form/checkbox.html',
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
        input_template='tri_form/choice.html',
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
        parse=choice_queryset_parse,
        choice_to_option=choice_queryset_choice_to_option,
        endpoint_path=choice_queryset_endpoint_path,
        endpoint__=choice_queryset_endpoint__select2,  # Backwards compatible
        endpoint__select2=choice_queryset_endpoint__select2,
        extra__endpoint_attr='name',
        is_valid=choice_queryset_is_valid,
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
        call_target__attribute="choice",
        attrs__multiple=True,
        choice_to_option=multi_choice_choice_to_option,
        is_list=True,
    )
    def multi_choice(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute="choice_queryset",
        attrs__multiple=True,
        choice_to_option=multi_choice_queryset_choice_to_option,
        is_list=True,
    )
    def multi_choice_queryset(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    @classmethod
    @class_shortcut(
        call_target__attribute="choice",
        input_template='tri_form/radio.html',
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
        template_string='{% extends "tri_form/table_form_row.html" %}{% block extra_content %}{{ field.value }}{% endblock %}',
        input_template='tri_form/file.html',
        write_to_instance=file_write_to_instance,
    )
    def file(cls, call_target=None, **kwargs):
        return call_target(**kwargs)

    # Shortcut to create a fake input that performs no parsing but is useful to separate sections of a form.
    @classmethod
    @class_shortcut(
        show=True,
        template='tri_form/heading.html',
        editable=False,
        attr=None,
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


def default_endpoint__field(form, key, value):
    prefix, remaining_key = dispatch_prefix_and_remaining_from_key(key)
    field = form.fields_by_name.get(prefix, None)
    if field is not None:
        return field.endpoint_dispatch(form=form, field=field, key=remaining_key, value=value)


@six.python_2_unicode_compatible
@declarative(Field, 'fields_dict')
@with_meta
class Form(RefinableObject):
    """
    Describe a Form. Example:

    .. code:: python

        class MyForm(Form):
            a = Field()
            b = Field.email()

        form = MyForm(data={})

    You can also create an instance of a form with this syntax if it's more convenient:

    .. code:: python

        form = MyForm(data={}, fields=[Field(name='a'), Field.email(name='b')])

    See tri.declarative docs for more on this dual style of declaration.
"""
    is_full_form = Refinable()
    links = Refinable()
    links_template = Refinable()
    attrs = Refinable()
    name = Refinable()
    editable = Refinable()

    model = Refinable()
    """ :type: django.db.models.Model """
    endpoint_dispatch_prefix = Refinable()
    """ :type: str """
    endpoint = Refinable()
    """ :type: tri.declarative.Namespace """
    extra = Refinable()
    """ :type: tri.declarative.Namespace """
    base_template = Refinable()
    """ :type: str """
    member_class = Refinable()

    class Meta:
        base_template = 'tri_form/base.html'
        member_class = Field

    @dispatch(
        is_full_form=True,
        model=None,
        endpoint__field=default_endpoint__field,
        editable=True,
        extra=EMPTY,
        attrs__class__newforms=True,
        attrs__action='',
        attrs__method='post',
        links=[Link.submit()],
        links_template='tri_form/links.html',
    )
    def __init__(self, request=None, data=None, instance=None, fields=None, fields_dict=None, **kwargs):
        """
        :type fields: list of Field
        :type data: dict[basestring, any]
        :type model: django.db.models.Model
        """
        super(Form, self).__init__(**kwargs)

        self.request = request

        if data is None and request:
            data = request.POST if request.method == 'POST' else request.GET

        if callable(fields):
            fields = fields(model=self.model)

        if data is None:
            data = {}

        self.data = data

        def unbound_fields():
            if fields is not None:
                for field in fields:
                    yield field
            for name, field in fields_dict.items():
                setattr(field, 'name', name)
                yield field

        self.declared_fields = sort_after([f._bind(self) for f in unbound_fields()])
        """ :type: list of Field"""

        self.mode = FULL_FORM_FROM_REQUEST if '-' in data else INITIALS_FROM_GET
        if request and request.method == 'POST' and self.is_target():
            self.mode = FULL_FORM_FROM_REQUEST

        if self.mode == INITIALS_FROM_GET and request and self.is_target():
            assert request.method == 'GET', 'Seems to be a POST but parameter "-" is not present'

        self.fields_by_name = None
        """ :type: Struct[str, Field] """
        self.style = None
        self.errors = set()
        """ :type: set of str """
        self._valid = None
        self.instance = instance

        for field in self.declared_fields:
            field._evaluate_show()

        self.fields = [field for field in self.declared_fields if should_show(field)]
        self.fields_by_name = Struct({field.name: field for field in self.fields})

        if self.instance is not None:
            for field in self.fields:
                if field.attr:
                    initial = field.read_from_instance(field, self.instance)
                    if field.is_list:
                        field.initial_list = initial
                    else:
                        field.initial = initial

        if data:
            for field in self.fields:
                if field.is_list:
                    if field.raw_data_list is not None:
                        continue
                    try:
                        # django and similar
                        # noinspection PyUnresolvedReferences
                        raw_data_list = data.getlist(field.name)
                    except AttributeError:  # pragma: no cover
                        # werkzeug and similar
                        raw_data_list = data.get(field.name)

                    if raw_data_list and field.strip_input:
                        raw_data_list = [x.strip() for x in raw_data_list]

                    if raw_data_list is not None:
                        field.raw_data_list = raw_data_list
                else:
                    if field.raw_data is not None:
                        continue
                    field.raw_data = data.get(field.name)
                    if field.raw_data and field.strip_input:
                        field.raw_data = field.raw_data.strip()

        for field in self.fields:
            field._evaluate()

        self.is_valid()

    def render_attrs(self):
        """
        Render HTML attributes, or return '' if no attributes needs to be rendered.
        """
        return render_attrs(self.attrs)

    @property
    def rendered_attrs(self):
        return self.render_attrs()

    def render_links(self):
        links, grouped_links = evaluate_and_group_links(self.links, form=self)
        return render_template(self.request, self.links_template, dict(links=links, grouped_links=grouped_links, form=self))

    @property
    def rendered_links(self):
        return format_html(self.render_links())

    @classmethod
    @dispatch(
        field=EMPTY,
    )
    def fields_from_model(cls, field, **kwargs):
        return create_members_from_model(
            member_params_by_member_name=field,
            default_factory=cls.get_meta().member_class.from_model,
            **kwargs
        )

    @classmethod
    @dispatch(
        field=EMPTY,
    )
    def from_model(cls, data, model, field, instance=None, include=None, exclude=None, extra_fields=None, **kwargs):
        """
        Create an entire form based on the fields of a model. To override a field parameter send keyword arguments in the form
        of "the_name_of_the_field__param". For example:

        .. code:: python

            class Foo(Model):
                foo = IntegerField()

            Form.from_model(data=request.GET, model=Foo, field__foo__help_text='Overridden help text')

        :param include: fields to include. Defaults to all
        :param exclude: fields to exclude. Defaults to none (except that AutoField is always excluded!)

        """
        fields = cls.fields_from_model(model=model, include=include, exclude=exclude, extra=extra_fields, field=field)
        return cls(data=data, model=model, instance=instance, fields=fields, **kwargs)

    def is_target(self):
        if not self.name:
            return True
        return self.name in self.data

    def is_valid(self):
        if self._valid is None:
            self.validate()
            for field in self.fields:
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
        for field in self.fields:
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

        for field in self.fields:
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

        for field in self.fields:
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

    def __str__(self):
        return self.table()

    def __html__(self):
        return self.table()

    def compact(self):
        return self.render(template_name=None)

    def table(self):
        return self.render(style='table', template_name=None)

    @property
    def table_property(self):
        return self.table()

    def render(self, style='compact', template_name="tri_form/form.html"):
        """
        :type style: str| unicode
        :type template_name: str | unicode | None
        """
        self.style = style
        r = []
        for field in self.fields:
            r.append(field.render(style=style))

        if self.is_full_form:
            r.append(format_html(AVOID_EMPTY_FORM))

        if template_name is None:
            return format_html('{}\n' * len(r), *r)
        else:
            return render_to_string(
                template_name=template_name,
                context=dict(form=self),
                request=self.request
            )

    def apply(self, instance):
        """
        Write the new values specified in the form into the instance specified.
        """
        assert self.is_valid()
        for field in self.fields:
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
        field_errors = {x.name: x.errors for x in self.fields if x.errors}
        if field_errors:
            r['fields'] = field_errors
        return r

    def endpoint_dispatch(self, key, value):
        prefix, remaining_key = dispatch_prefix_and_remaining_from_key(key)
        handler = self.endpoint.get(prefix, None)
        if handler is not None:
            return handler(form=self, key=remaining_key, value=value)

    @classmethod
    def create_or_edit_object(cls, *args, **kwargs):
        from .views import create_or_edit_object
        setdefaults_path(
            kwargs,
            form__call_target=cls.from_model,
        )
        return create_or_edit_object(*args, **kwargs)


# Backward compatibility
default_read_from_instance = Field.read_from_instance
default_write_to_instance = Field.write_to_instance

setup_db_compat()
