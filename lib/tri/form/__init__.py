from __future__ import unicode_literals, absolute_import

from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from distutils.version import StrictVersion
from itertools import chain

import django

import re
from django.core.exceptions import ValidationError
from django.db.models.fields import FieldDoesNotExist
from django.core.validators import validate_email, URLValidator
from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, CommaSeparatedIntegerField, DateField, DateTimeField, DecimalField, EmailField, URLField, TimeField, ForeignKey, OneToOneField, ManyToManyField, FileField, ManyToOneRel, ManyToManyRel
from django.template import RequestContext
from django.template.context import Context
from django.template.loader import render_to_string
from django.utils.encoding import python_2_unicode_compatible
from django.utils.safestring import mark_safe
from tri.named_struct import NamedStruct, NamedStructField
from tri.struct import Struct, Frozen
from tri.declarative import evaluate_recursive, should_show, creation_ordered, declarative, getattr_path, sort_after, with_meta, setdefaults_path, dispatch, setattr_path, assert_kwargs_empty, EMPTY

from tri.form.render import render_attrs

try:
    from django.template.loader import get_template_from_string
except ImportError:  # pragma: no cover
    # Django 1.8+
    # noinspection PyUnresolvedReferences
    from django.template import engines

    def get_template_from_string(template_code, origin=None, name=None):
        del origin, name  # the origin and name parameters seems not to be implemented in django 1.8
        return engines['django'].from_string(template_code)


__version__ = '3.3.0'


def capitalize(s):
    return s[0].upper() + s[1:] if s else s


# This input is added to all forms. It is used to circumvent the fact that unchecked checkboxes are not sent as
# parameters in the request. More specifically, the problem occurs when the checkbox is checked by default,
# as it would not be possible to distinguish between the initial request and a subsequent request where the checkbox
# is unchecked. By adding this input, it is possible to make this distinction as subsequent requests will contain
# (at least) this key-value.
AVOID_EMPTY_FORM = '<input type="hidden" name="-" value="-" />'

FULL_FORM_FROM_REQUEST = 'full_form_from_request'
INITIALS_FROM_GET = 'initials_from_get'


def bool_parse(string_value):
    s = string_value.lower()
    if s in ('1', 'true', 't', 'yes', 'y', 'on'):
        return True
    elif s in ('0', 'false', 'f', 'no', 'n', 'off'):
        return False
    else:
        raise ValueError('%s is not a valid boolean value' % string_value)


def foreign_key_factory(model_field, **kwargs):
    setdefaults_path(
        kwargs,
        choices=model_field.foreign_related_fields[0].model.objects.all(),
    )
    kwargs['model'] = model_field.foreign_related_fields[0].model
    return Field.choice_queryset(**kwargs)


def many_to_many_factory(model_field, **kwargs):
    setdefaults_path(
        kwargs,
        choices=model_field.rel.to.objects.all(),
        read_from_instance=lambda field, instance: getattr_path(instance, field.attr).all(),
        extra__django_related_field=True,
    )
    kwargs['model'] = model_field.rel.to
    return Field.multi_choice_queryset(**kwargs)


# The order here is significant because of inheritance structure. More specific must be below less specific.
_field_factory_by_django_field_type = OrderedDict([
    (CharField, lambda model_field, **kwargs: Field(**kwargs)),
    (URLField, lambda model_field, **kwargs: Field.url(**kwargs)),
    (TimeField, lambda model_field, **kwargs: Field.time(**kwargs)),
    (EmailField, lambda model_field, **kwargs: Field.email(**kwargs)),
    (DecimalField, lambda model_field, **kwargs: Field.decimal(**kwargs)),
    (DateField, lambda model_field, **kwargs: Field.date(**kwargs)),
    (DateTimeField, lambda model_field, **kwargs: Field.datetime(**kwargs)),
    (CommaSeparatedIntegerField, lambda model_field, **kwargs: Field.comma_separated(parent_field=Field.integer(**kwargs))),
    (BooleanField, lambda model_field, **kwargs: Field.boolean(**kwargs)),
    (TextField, lambda model_field, **kwargs: Field.text(**kwargs)),
    (FloatField, lambda model_field, **kwargs: Field.float(**kwargs)),
    (IntegerField, lambda model_field, **kwargs: Field.integer(**kwargs)),
    (AutoField, lambda model_field, **kwargs: Field.integer(**setdefaults_path(kwargs, show=False))),
    (ManyToOneRel, None),
    (ManyToManyRel, None),
    (FileField, lambda model_field, **kwargs: Field.file(**kwargs)),
    (ForeignKey, foreign_key_factory),
    (ManyToManyField, many_to_many_factory)
])


def _django_field_defaults(model_field):
    r = {}
    if hasattr(model_field, 'verbose_name'):
        r['label'] = capitalize(model_field.verbose_name)

    if hasattr(model_field, 'null') and not isinstance(model_field, BooleanField):
        r['required'] = not model_field.null and not model_field.blank

    if hasattr(model_field, 'blank'):
        r['parse_empty_string_as_none'] = not model_field.blank

    return r


def register_field_factory(field_class, factory):
    _field_factory_by_django_field_type[field_class] = factory


def default_parse(form, field, string_value):
    del form, field
    return string_value


def default_read_from_instance(field, instance):
    return getattr_path(instance, field.attr)


def default_write_to_instance(field, instance, value):
    setattr_path(instance, field.attr, value)


MISSING = object()


@dispatch
def create_members_from_model(default_factory, model, db_field, include=None, exclude=None, extra=None):
    def should_include(name):
        if exclude is not None and name in exclude:
            return False
        if include is not None:
            return name in include
        return True

    members = []
    # noinspection PyProtectedMember
    for field in get_fields(model):
        if should_include(field.name):
            subkeys = db_field.pop(field.name, {})
            subkeys.setdefault('class', default_factory)
            foo = subkeys.pop('class')(name=field.name, model=model, model_field=field, **subkeys)
            if foo is None:
                continue
            if isinstance(foo, list):
                members.extend(foo)
            else:
                members.append(foo)
    return members + (extra if extra is not None else [])


def member_from_model(model, factory_lookup, defaults_factory, field_name=None, model_field=None, **kwargs):
    if model_field is None:
        # noinspection PyProtectedMember
        model_field = model._meta.get_field(field_name)

    setdefaults_path(
        kwargs,
        defaults_factory(model_field),
        name=field_name,
    )

    factory = factory_lookup.get(type(model_field), MISSING)

    if factory is MISSING:
        for django_field_type, func in reversed(factory_lookup.items()):
            if isinstance(model_field, django_field_type):
                factory = func
                break

    if factory is MISSING:  # pragma: no cover
        raise AssertionError('No factory for %s. Register a factory with tri.form.register_field_factory, you can also register one that returns None to not handle this field type' % type(model_field))

    return factory(model_field=model_field, model=model, **kwargs) if factory else None


@dispatch(
    field=EMPTY,
)
def expand_member(model, factory_lookup, defaults_factory, name, field, field_name=None, model_field=None):
    if model_field is None:  # pragma: no cover
        # noinspection PyProtectedMember
        model_field = model._meta.get_field(field_name)
    assert isinstance(model_field, OneToOneField)

    result = [member_from_model(model=model_field.related_field.model,
                                factory_lookup=factory_lookup,
                                defaults_factory=defaults_factory,
                                field_name=sub_model_field.name,
                                name=name + '__' + sub_model_field.name,
                                **field.pop(sub_model_field.name, {}))
              for sub_model_field in get_fields(model=model_field.related_field.model)]
    assert_kwargs_empty(field)
    return [x for x in result if x is not None]


def default_help_text(field, **_):
    if field.model is None or field.attr is None:
        return ''
    try:
        return field.model._meta.get_field_by_name(field.attr.rsplit('__', 1)[-1])[0].help_text or ''
    except FieldDoesNotExist:  # pragma: no cover
        return ''


class FieldBase(NamedStruct):
    name = NamedStructField()

    show = NamedStructField(default=True)

    attr = NamedStructField(default=MISSING)
    id = NamedStructField(default=MISSING)
    label = NamedStructField(default=MISSING)

    after = NamedStructField()

    is_valid = NamedStructField(default=lambda form, field, parsed_data: (True, ''))
    """ @type: (Form, Field, object) -> boolean """
    parse = NamedStructField(default=default_parse)
    """ @type: (Form, Field, unicode) -> object """
    parse_empty_string_as_none = NamedStructField(default=True)
    initial = NamedStructField()
    initial_list = NamedStructField()
    template = NamedStructField(default='tri_form/{style}_form_row.html')
    template_string = NamedStructField()
    attrs = NamedStructField(default_factory=dict)
    input_template = NamedStructField(default='tri_form/input.html')
    label_template = NamedStructField(default='tri_form/label.html')
    errors_template = NamedStructField(default='tri_form/errors.html')
    required = NamedStructField(default=True)
    container_css_classes = NamedStructField(default_factory=set)
    label_container_css_classes = NamedStructField(default_factory=lambda: {'description_container'})
    input_container_css_classes = NamedStructField(default_factory=set)
    post_validation = NamedStructField(default=lambda form, field: None)
    """ @type: (Form, Field) -> None """
    render_value = NamedStructField(default=lambda form, field, value: "%s" % value)
    """ @type: (Form, Field, object) -> unicode """
    is_list = NamedStructField(default=False)
    is_boolean = NamedStructField(default=False)
    model = NamedStructField()

    # grab help_text from model if applicable
    # noinspection PyProtectedMember
    help_text = NamedStructField(default=default_help_text)

    editable = NamedStructField(default=True)
    strip_input = NamedStructField(default=True)
    input_type = NamedStructField(default='text')

    extra = NamedStructField(default_factory=Struct)
    choice_to_option = NamedStructField()
    empty_label = NamedStructField()
    empty_choice_tuple = NamedStructField()
    choices = NamedStructField()

    read_from_instance = NamedStructField(default=default_read_from_instance)
    """ @type: (Field, object) -> None """
    write_to_instance = NamedStructField(default=default_write_to_instance)
    """ @type: (Field, object, object) -> None """

    endpoint_dispatch = NamedStructField(default=lambda **_: None)
    """ @type: (Form, Field, str) -> None """
    endpoint_path = NamedStructField(default=None)


class BoundField(FieldBase):

    form = NamedStructField()
    errors = NamedStructField()

    # raw_data/raw_data contains the strings grabbed directly from the request data
    raw_data = NamedStructField()
    raw_data_list = NamedStructField()

    # parsed_data/parsed_data contains data that has been interpreted, but not checked for validity or access control
    parsed_data = NamedStructField()
    parsed_data_list = NamedStructField()

    # value/value_data_list is the final step that contains parsed and valid data
    value = NamedStructField()
    value_list = NamedStructField()

    choice_tuples = NamedStructField()

    """
    An internal class that is used to handle the mutable data used during parsing and validation of a Field.

    The life cycle of the data is:
        1. raw_data/raw_data_list: will be set if the corresponding key is present in the HTTP request
        2. parsed_data/parsed_data_list: set if parsing is successful, which only happens if the previous step succeeded
        3. value/value_list: set if validation is successful, which only happens if the previous step succeeded

    The variables *_list should be used if the input is a list.
    """

    def __init__(self, field, form):
        super(BoundField, self).__init__(**field)
        if self.attr is MISSING:
            self.attr = self.name
        if self.id is MISSING:
            self.id = 'id_%s' % self.name if self.name else ''
        if self.label is MISSING:
            # noinspection PyTypeChecker
            self.label = capitalize(self.name).replace('_', ' ') if self.name else ''

        self.form = form
        self.errors = set()

    def evaluate(self):
        """
        Evaluates callable/lambda members. After this function is called all members will be values.
        """
        members_to_evaluate = {k: v for k, v in self.items() if k != 'post_validation'}
        for k, v in members_to_evaluate.items():
            self[k] = evaluate_recursive(v, form=self.form, field=self)
        if not self.editable:
            # noinspection PyAttributeOutsideInit
            self.input_template = 'tri_form/non_editable.html'

    def rendered_value(self):
        value = self.raw_data if self.errors else self.value
        return self.render_value(form=self.form, field=self, value=value if value else '')

    def render_attrs(self):
        """
        Render HTML attributes, or return '' if no attributes needs to be rendered.
        """
        return render_attrs(self.attrs)

    def render_container_css_classes(self):
        container_css_classes = set(self.container_css_classes)
        if self.required and self.editable:
            container_css_classes.add('required')
        if self.form.style == 'compact':
            container_css_classes.add('key-value')
        return render_css_classes(container_css_classes)

    def render_label_container_css_classes(self):
        return render_css_classes(self.label_container_css_classes)

    def render_input_container_css_classes(self):
        return render_css_classes(self.input_container_css_classes)


def render_css_classes(classes):
    """
    Render CSS classes, or return '' if no attributes needs to be rendered.
    """
    return '' if not classes else mark_safe(' class="%s"' % ' '.join(sorted(classes)))


@creation_ordered
class Field(Frozen, FieldBase):
    """
    Class that describes a field, i.e. what input controls to render, the label, etc.
    """
    @dispatch(
        extra=EMPTY,
        attrs__class=EMPTY,
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
        :param id: the HTML id attribute. Default: 'id_%s' % name
        :param label: the text in the HTML label tag. Default: capitalize(name).replace('_', ' ')
        :param template: django template filename for the entire row. Normally you shouldn't need to override on this level, see input_template, label_template and error_template below. Default: 'tri_form/{style}_form_row.html'
        :param template_string: You can inline a template string here if it's more convenient than creating a file. Default: None
        :param input_template: django template filename for the template for just the input control. Default: 'tri_form/input.html'
        :param label_template: django template filename for the template for just the label tab. Default: 'tri_form/label.html'
        :param errors_template: django template filename for the template for just the errors output. Default: 'tri_form/errors.html'
        :param required: if the field is a required field. Default: True
        :param container_css_classes: extra CSS classes to set on the container (i.e. row if rendering as a table). Default: set()
        :param label_container_css_classes: default: {'description_container'}
        :param input_container_css_classes: default: set()
        :param help_text: The help text will be grabbed from the django model if specified and available. Default: lambda form, field: '' if form.model is None else form.model._meta.get_field_by_name(field.name)[0].help_text or ''

        :param editable: default: True
        :param strip_input: runs the input data through standard python .strip() before passing it to the parse function (can NOT be callable). Default: True
        :param input_type: the type attribute on the standard input HTML tag. Default: 'text'
        :param render_value: render the parsed and validated value into a string. Default just converts to unicode: lambda form, field, value: unicode(value)
        :param is_list: interpret request data as a list (can NOT be a callable). Default False
        :param read_from_instance: callback to retrieve value from edited instance. Invoked with parameters field and instance.
        :param write_to_instance: callback to write value to instance. Invoked with parameters field, instance and value.
        """

        super(Field, self).__init__(**kwargs)

    @staticmethod
    def hidden(**kwargs):
        setdefaults_path(
            kwargs,
            input_type='hidden',
        )
        return Field(**kwargs)

    @staticmethod
    def text(**kwargs):
        setdefaults_path(
            kwargs,
            input_type='text',
        )
        return Field(**kwargs)

    @staticmethod
    def textarea(**kwargs):
        setdefaults_path(
            kwargs,
            input_template='tri_form/text.html',
        )
        return Field(**kwargs)

    @staticmethod
    def integer(**kwargs):
        setdefaults_path(
            kwargs,
            parse=lambda string_value, **_: int(string_value),
        )
        return Field(**kwargs)

    @staticmethod
    def float(**kwargs):
        def parse_float(string_value, **_):
            try:
                return float(string_value)
            except ValueError:
                # Acrobatics so we get equal formatting in python 2/3
                raise ValueError("could not convert string to float: %s" % string_value)

        setdefaults_path(
            kwargs,
            parse=parse_float,
        )
        return Field(**kwargs)

    @staticmethod
    def password(**kwargs):
        setdefaults_path(
            kwargs,
            input_type='password',
        )
        return Field(**kwargs)

    @staticmethod
    def boolean(**kwargs):
        """
        Boolean field. Tries hard to parse a boolean value from its input.
        """
        setdefaults_path(
            kwargs,
            parse=lambda string_value, **_: bool_parse(string_value),
            required=False,
            template='tri_form/{style}_form_row_checkbox.html',
            input_template='tri_form/checkbox.html',
            is_boolean=True,
        )
        return Field(**kwargs)

    @staticmethod
    def choice(**kwargs):
        """
        Shortcut for single choice field. If required is false it will automatically add an option first with the value '' and the title '---'. To override that text pass in the parameter empty_label.
        :param empty_label: default '---'
        :param choices: list of objects
        :param choice_to_option: callable with three arguments: form, field, choice. Convert from a choice object to a tuple of (choice, value, label, selected), the last three for the <option> element
        """
        assert 'choices' in kwargs

        setdefaults_path(
            kwargs,
            required=True,
            is_list=False,
            empty_label='---',
        )

        if not kwargs['required'] and not kwargs['is_list']:
            original_parse = kwargs.get('parse', default_parse)

            def parse(form, field, string_value):
                return original_parse(form=form, field=field, string_value=string_value)

            kwargs.update(
                parse=parse
            )

        def choice_is_valid(form, field, parsed_data):
            del form
            return parsed_data in field.choices, '%s not in available choices' % parsed_data

        def post_validation(form, field):
            choice_tuples = (field.choice_to_option(form=form, field=field, choice=choice) for choice in field.choices)
            if not field.required and not field.is_list:
                choice_tuples = chain([field.empty_choice_tuple], choice_tuples)
            field.choice_tuples = choice_tuples

        setdefaults_path(
            kwargs,
            empty_choice_tuple=(None, '', kwargs['empty_label'], True),
            choice_to_option=lambda form, field, choice: (choice, "%s" % choice, "%s" % choice, choice == field.value),
            input_template='tri_form/choice.html',
            is_valid=choice_is_valid,
            post_validation=post_validation,
        )

        return Field(**kwargs)

    @staticmethod
    def choice_queryset(**kwargs):

        def choice_queryset_is_valid(form, field, parsed_data):
            del form
            return field.choices.filter(pk=parsed_data.pk).exists(), '%s not in available choices' % (field.raw_data or ', '.join(field.raw_data_list))

        def choice_queryset_endpoint_dispatch(field, value, **_):
            limit = 10
            result = field.choices.filter(**{field.extra.endpoint_attr + '__icontains': value}).values_list(*['pk', field.extra.endpoint_attr])
            return [
                dict(
                    id=row[0],
                    text=row[1],
                )
                for row in result[:limit]
            ]

        kwargs = setdefaults_path(
            Struct(),
            kwargs,
            parse=lambda form, field, string_value: field.model.objects.get(pk=string_value) if string_value else None,
            choice_to_option=lambda form, field, choice: (choice, choice.pk, "%s" % choice, choice == field.value),
            endpoint_path=lambda form, field: '__' + form.endpoint_dispatch_prefix + '__field__' + field.name,
            endpoint_dispatch=choice_queryset_endpoint_dispatch,
            extra__endpoint_attr='name',
            is_valid=choice_queryset_is_valid,
        )
        return Field.choice(**kwargs)

    @staticmethod
    def multi_choice(**kwargs):
        setdefaults_path(
            kwargs,
            attrs__multiple=True,
            choice_to_option=lambda form, field, choice: (choice, "%s" % choice, "%s" % choice, field.value_list and choice in field.value_list),
            is_list=True,
        )
        return Field.choice(**kwargs)

    @staticmethod
    def multi_choice_queryset(**kwargs):
        setdefaults_path(
            kwargs,
            attrs__multiple=True,
            choice_to_option=lambda form, field, choice: (choice, choice.pk, "%s" % choice, field.value_list and choice in field.value_list),
            is_list=True,
        )
        return Field.choice_queryset(**kwargs)

    @staticmethod
    def radio(**kwargs):
        setdefaults_path(
            kwargs,
            input_template='tri_form/radio.html',
        )
        return Field.choice(**kwargs)

    @staticmethod
    def datetime(**kwargs):
        iso_format = '%Y-%m-%d %H:%M:%S'

        def datetime_parse(string_value, **_):
            try:
                return datetime.strptime(string_value, iso_format)
            except ValueError as e:
                raise ValidationError(str(e))

        setdefaults_path(
            kwargs,
            parse=datetime_parse,
            render_value=lambda value, **_: value.strftime(iso_format) if value else '',
        )
        return Field(**kwargs)

    @staticmethod
    def date(**kwargs):
        iso_format = '%Y-%m-%d'

        def date_parse(string_value, **_):
            try:
                return datetime.strptime(string_value, iso_format).date()
            except ValueError as e:
                raise ValidationError(str(e))

        setdefaults_path(
            kwargs,
            parse=date_parse,
            render_value=lambda value, **_: value.strftime(iso_format) if value else '',
        )
        return Field(**kwargs)

    @staticmethod
    def time(**kwargs):
        iso_format = '%H:%M:%S'

        def time_parse(string_value, **_):
            try:
                return datetime.strptime(string_value, iso_format).time()
            except ValueError as e:
                raise ValidationError(str(e))

        setdefaults_path(
            kwargs,
            parse=time_parse,
            render_value=lambda value, **_: value.strftime(iso_format),
        )
        return Field(**kwargs)

    @staticmethod
    def decimal(**kwargs):
        setdefaults_path(
            kwargs,
            parse=lambda string_value, **_: Decimal(string_value),
        )
        return Field(**kwargs)

    @staticmethod
    def url(**kwargs):
        setdefaults_path(
            kwargs,
            input_type='email',
            parse=lambda string_value, **_: URLValidator(string_value) or string_value,
        )
        return Field(**kwargs)

    @staticmethod
    def file(**kwargs):
        def file_write_to_instance(field, instance, value):
            if value:
                default_write_to_instance(field=field, instance=instance, value=value)

        setdefaults_path(
            kwargs,
            input_type='file',
            template_string='{% extends "tri_form/table_form_row.html" %}{% block extra_content %}{{ field.value }}{% endblock %}',
            write_to_instance=file_write_to_instance,
        )
        return Field(**kwargs)

    @staticmethod
    def heading(label, show=True, template='tri_form/heading.html', **kwargs):
        """
        Shortcut to create a fake input that performs no parsing but is useful to separate sections of a form.
        """
        setdefaults_path(
            kwargs,
            label=label,
            show=show,
            template=template,
            editable=False,
            attr=None,
            name='@@heading@@',
        )
        return Field(**kwargs)

    @staticmethod
    def info(value, **kwargs):
        """
        Shortcut to create an info entry.
        """
        setdefaults_path(
            kwargs,
            initial=value,
            editable=False,
            attr=None,
        )
        return Field(**kwargs)

    @staticmethod
    def email(**kwargs):
        setdefaults_path(
            kwargs,
            input_type='email',
            parse=lambda string_value, **_: validate_email(string_value) or string_value,
        )
        return Field(**kwargs)

    @staticmethod
    def phone_number(**kwargs):
        setdefaults_path(
            kwargs,
            is_valid=lambda form, field, parsed_data: (re.match(r'^\+\d{1,3}(( |-)?\(\d+\))?(( |-)?\d+)+$', parsed_data, re.IGNORECASE), 'Please use format +<country code> (XX) XX XX. Example of US number: +1 (212) 123 4567 or +1 212 123 4567'),
        )
        return Field(**kwargs)

    @staticmethod
    def from_model(model, field_name=None, model_field=None, **kwargs):
        return member_from_model(
            model=model,
            factory_lookup=_field_factory_by_django_field_type,
            defaults_factory=_django_field_defaults,
            field_name=field_name,
            model_field=model_field,
            **kwargs)

    @staticmethod
    def from_model_expand(model, field_name=None, model_field=None, **kwargs):
        return expand_member(
            model=model,
            factory_lookup=_field_factory_by_django_field_type,
            defaults_factory=_django_field_defaults,
            field_name=field_name,
            model_field=model_field,
            **kwargs)

    @staticmethod
    def comma_separated(parent_field):
        """
        Shortcut to create a comma separated list of something. You can use this to create a comma separated text input that gives nice validation errors easily. Example:

        .. code:: python

            Field.comma_separated(Field.email)

        :type parent_field: Field
        """
        kwargs = dict(parent_field)

        def parse_comma_separated(form, field, string_value):
            errors = []
            result = []
            for x in string_value.split(','):
                x = x.strip()
                try:
                    result.append(parent_field.parse(form=form, field=field, string_value=x.strip()))
                except ValueError as e:
                    errors.append('Invalid value "%s": %s' % (x, e))
                except ValidationError as e:
                    for message in e.messages:
                        errors.append('Invalid value "%s": %s' % (x, message))
            if errors:
                raise ValidationError(errors)
            return ', '.join(result)

        def is_valid_comma_separated(form, field, parsed_data):
            errors = set()
            for x in parsed_data.split(','):
                x = x.strip()
                is_valid, error = parent_field.is_valid(form=form, field=field, parsed_data=x)
                if not is_valid:
                    errors.add('Invalid value "%s": %s' % (x, error))
            return errors == set(), errors

        kwargs.update(dict(
            parse=parse_comma_separated,
            is_valid=is_valid_comma_separated
        ))
        return Field(**kwargs)


if StrictVersion(django.get_version()) >= StrictVersion('1.8.0'):
    def get_fields(model):
        # noinspection PyProtectedMember
        for field in model._meta.get_fields():
            yield field
else:
    # This is actually covered by tests, but only in a specific version of django :P
    def get_fields(model):  # pragma: no cover
        # noinspection PyProtectedMember
        for field, _ in chain(model._meta.get_fields_with_model(), model._meta.get_m2m_with_model()):
            yield field


@python_2_unicode_compatible
@declarative(Field, 'fields_dict')
@with_meta
class Form(object):
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
    def __init__(self, request=None, data=None, instance=None, fields=None, model=None, post_validation=None, fields_dict=None, endpoint_dispatch_prefix='form'):
        """
        :type fields: list of Field
        :type data: dict[basestring, basestring]
        :type model: django.db.models.Model
        """
        self.endpoint_dispatch_prefix = endpoint_dispatch_prefix
        self.request = request
        if data is None and request:
            data = request.POST if request.method == 'POST' else request.GET

        if data is None:
            data = {}

        def unbound_fields():
            if fields is not None:
                for field in fields:
                    yield field
            for name, field in fields_dict.items():
                dict.__setitem__(field, 'name', name)
                yield field
        self.fields = sort_after([BoundField(f, self) for f in unbound_fields()])
        """ :type: list of BoundField"""

        if instance is not None:
            for field in self.fields:
                if field.attr:
                    initial = field.read_from_instance(field, instance)
                    if field.is_list:
                        field.initial_list = initial
                    else:
                        field.initial = initial

            self.instance = instance
        else:
            self.instance = None

        self.mode = FULL_FORM_FROM_REQUEST if '-' in data else INITIALS_FROM_GET
        if self.mode == INITIALS_FROM_GET and request:
            assert request.method == 'GET', 'Seems to be a POST but parameter "-" is not present'

        if data:
            for field in self.fields:
                if field.is_list:
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
                    field.raw_data = data.get(field.name)
                    if field.raw_data and field.strip_input:
                        field.raw_data = field.raw_data.strip()

        self.post_validation = post_validation if post_validation is not None else lambda form: None
        self.fields_by_name = None
        """ :type: dict[str, BoundField] """
        self.style = None
        self.model = model
        """ :type model: django.db.models.Model """
        self._valid = None
        self.errors = set()
        self.evaluate()
        self.is_valid()
        """ :type: list of str """

    @staticmethod
    def fields_from_model(**kwargs):
        return create_members_from_model(default_factory=Field.from_model, **kwargs)

    @staticmethod
    @dispatch(
        field=EMPTY,
    )
    def from_model(data, model, field, instance=None, include=None, exclude=None, extra_fields=None, post_validation=None, **kwargs):
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
        fields = Form.fields_from_model(model=model, include=include, exclude=exclude, extra=extra_fields, db_field=field)
        return Form(data=data, model=model, instance=instance, fields=fields, post_validation=post_validation, **kwargs)

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

    def evaluate(self):
        for field in self.fields:
            field.evaluate()
        self.fields = [field for field in self.fields if should_show(field)]
        self.fields_by_name = Struct({field.name: field for field in self.fields})

    def validate(self):
        self.parse()

        for field in self.fields:
            if self.mode is INITIALS_FROM_GET and field.raw_data is None and field.raw_data_list is None:
                if field.is_list:
                    field.value_list = field.initial_list
                else:
                    field.value = field.initial
                continue

            if not field.editable:
                continue

            value = None
            value_list = None
            if field.is_list:
                if field.parsed_data_list is not None:
                    value_list = [self.validate_field_parsed_data(field, x) for x in field.parsed_data_list]
            else:
                if field.parsed_data is not None:
                    value = self.validate_field_parsed_data(field, field.parsed_data)

            if not field.errors:
                if self.mode is FULL_FORM_FROM_REQUEST and field.required and not value and not value_list:
                    field.errors.add('This field is required')
                else:
                    field.value = value
                    field.value_list = value_list

        for field in self.fields:
            field.post_validation(form=self, field=field)
        self.post_validation(form=self)
        return self

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

    def compact(self):
        return self.render(template_name=None)

    def table(self):
        return self.render(style='table', template_name=None)

    def render(self, style='compact', template_name="tri_form/form.html"):
        """
        :type style: str| unicode
        :type template_name: str | unicode | None
        """
        self.style = style
        r = []
        for field in self.fields:
            context = {
                'form': self,
                'field': field,
            }
            if field.template_string is not None:
                r.append(get_template_from_string(field.template_string, origin='tri.form', name='Form.render').render(Context(context)))
            else:
                r.append(render_to_string(field.template.format(style=style), context))
        r.append(AVOID_EMPTY_FORM)

        if template_name is None:
            return mark_safe('\n'.join(r))
        else:
            return render_to_string(
                context_instance=RequestContext(self.request, dict(form=self)),
                template_name=template_name,
            )

    def apply(self, instance):
        """
        Write the new values specified in the form into the instance specified.
        """
        assert self.is_valid()
        for field in self.fields:
            self.apply_field(instance=instance, field=field)

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
        if key.startswith('field__'):
            key = key[len('field__'):]
            field = self.fields_by_name.get(key, None)
            if field is not None:
                return field.endpoint_dispatch(form=self, field=field, value=value)
