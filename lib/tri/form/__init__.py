from __future__ import unicode_literals, absolute_import
from decimal import Decimal
import re
from datetime import datetime
from collections import OrderedDict
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, URLValidator
from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, CommaSeparatedIntegerField, DateField, DateTimeField, DecimalField, EmailField, URLField, TimeField, ForeignKey, QuerySet
from django.template.loader import render_to_string
from django.template.context import Context
from django.utils.safestring import mark_safe
from tri.struct import Struct, FrozenStruct
from tri.declarative import evaluate, should_show, should_not_evaluate, should_evaluate, creation_ordered, declarative

try:
    from django.template.loader import get_template_from_string
except ImportError:
    # Django 1.8+
    from django.template import engines
    def get_template_from_string(template_code, origin=None, name=None):
        del origin, name  # the origin and name parameters seems not to be implemented in django 1.8
        return engines['django'].from_string(template_code)


__version__ = '1.0.1'


def foreign_key_factory(model_field, kwargs):
    kwargs.setdefault('choices', model_field.related_field.model.objects.all())
    return Field.choice_queryset(model=model_field.related_field.model, **kwargs)

# The order here is significant because of inheritance structure. More specific must be below less specific.
_field_factory_by_django_field_type = OrderedDict([
    (CharField, lambda model_field, kwargs: Field(**kwargs)),
    (URLField, lambda model_field, kwargs: Field.url(**kwargs)),
    (TimeField, lambda model_field, kwargs: Field.time(**kwargs)),
    (EmailField, lambda model_field, kwargs: Field.email(**kwargs)),
    (DecimalField, lambda model_field, kwargs: Field.decimal(**kwargs)),
    (DateField, lambda model_field, kwargs: Field.date(**kwargs)),
    (DateTimeField, lambda model_field, kwargs: Field.datetime(**kwargs)),
    (CommaSeparatedIntegerField, lambda model_field, kwargs: Field.comma_separated(parent_field=Field.integer(**kwargs))),
    (BooleanField, lambda model_field, kwargs: Field.boolean(**kwargs)),
    (TextField, lambda model_field, kwargs: Field.text(**kwargs)),
    (FloatField, lambda model_field, kwargs: Field.float(**kwargs)),
    (IntegerField, lambda model_field, kwargs: Field.integer(**kwargs)),
    (ForeignKey, foreign_key_factory),
])


def register_field_factory(field_class, factory):
    _field_factory_by_django_field_type[field_class] = factory


def extract_subkeys(kwargs, prefix, defaults=None):
    """
    Extract

    >>> foo = {
    ...     'foo__foo': 1,
    ...     'foo__bar': 2,
    ...     'baz': 3,
    ... }
    >>> assert extract_subkeys(foo, defaults={'quux': 4}) == {
    ...     'foo': 1,
    ...     'bar': 2,
    ...     'quux': 4,
    ... }
    """

    prefix += '__'
    result = {k[len(prefix):]: v for k, v in kwargs.items() if k.startswith(prefix)}
    if defaults is not None:
        return setdefaults(result, defaults)
    else:
        return result


def setdefaults(d, d2):
    for k, v in d2.items():
        d.setdefault(k, v)
    return d


def getattr_path(obj, path):
    """
    Get an attribute path, as defined by a string separated by '__'.
    getattr_path(foo, 'a__b__c') is roughly equivalent to foo.a.b.c but
    will short circuit to return None if something on the path is None.
    """
    path = path.split('__')
    for name in path:
        obj = getattr(obj, name)
        if obj is None:
            return None
    return obj


def setattr_path(obj, path, value):
    """
    Set an attribute path, as defined by a string separated by '__'.
    setattr_path(foo, 'a__b__c', value) is equivalent to "foo.a.b.c = value".
    """
    path = path.split('__')
    o = obj
    for name in path[:-1]:
        o = getattr(obj, name)
    setattr(o, path[-1], value)
    return obj


class BoundField(Struct):
    """
    An internal class that is used to handle the mutable data used during parsing and validation of a Field.
    
    The life cycle of the data is:
        1. raw_data/raw_data_list: will be set if the corresponding key is present in the HTTP request
        2. parsed_data/parsed_data_list: set if parsing is successful, which only happens if the previous step succeeded
        3. value/value_list: set if validation is successful, which only happens if the previous step succeeded

    The variables *_list should be used if the input is a list.
    """
    
    def __init__(self, field, form):
        super(BoundField, self).__init__(field)
        self.form = form

        self.errors = set()

        # raw_data/raw_data contains the strings grabbed directly from the request data
        self.raw_data = None
        self.raw_data_list = None
        # parsed_data/parsed_data contains data that has been interpreted, but not checked for validity or access control
        self.parsed_data = None
        self.parsed_data_list = None
        # value/value_data_list is the final step that contains parsed and valid data
        self.value = None
        self.value_list = None

    def evaluate(self):
        """
        Evaluates callable/lambda members. After this function is called all members will be values. 
        """
        members_to_evaluate = {k: v for k, v in self.items() if k not in ('parse', 'is_valid', 'form', 'internal', 'post_validation', 'render_value')}
        for k, v in members_to_evaluate.items():
            self[k] = evaluate(v, form=self.form, field=self)
        if not self.editable:
            # noinspection PyAttributeOutsideInit
            self.input_template = 'tri_form/non_editable.html'

    def rendered_value(self):
        return self.render_value(form=self.form, field=self, value=self.value)

    def render_attrs(self):
        """
        Render HTML attributes, or return '' if no attributes needs to be rendered.
        """
        attrs = self.get('attrs')
        if attrs is not None:
            return mark_safe(' %s ' % ' '.join(['%s="%s"' % (key, value) for key, value in attrs.items()]))
        return ''

    def render_css_classes(self, key):
        """
        Render CSS classes, or return '' if no attributes needs to be rendered.
        """
        classes = self.get(key)
        return '' if not classes else mark_safe(' class="%s"' % ' '.join(sorted(classes)))

    def render_container_css_classes(self):
        c = self.get('container_css_classes', set())
        if self.get('required', False):
            c.add('required')
        if self.form.style == 'compact':
            c.add('key-value')
        self['container_css_classes'] = c
        return self.render_css_classes('container_css_classes')

    def render_label_container_css_classes(self):
        return self.render_css_classes('label_container_css_classes')

    def render_input_container_css_classes(self):
        return self.render_css_classes('input_container_css_classes')


def DEFAULT_PARSE(form, field, string_value):
    del form, field
    return string_value


@creation_ordered
class Field(FrozenStruct):
    """
    Class that describes a field, i.e. what input controls to render, the label, etc.
    """
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
        :param label: the text in the HTML label tag. Default: name.capitalize().replace('_', ' ')
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
        :parma is_list: interpret request data as a list (can NOT be a callable). Default False
        """
        kwargs.setdefault('internal', Struct())
        if 'name' in kwargs:
            name = kwargs['name']
            kwargs.setdefault('attr', name)
            kwargs.setdefault('id', 'id_%s' % name)
            kwargs.setdefault('label', name.capitalize().replace('_', ' '))
        kwargs.setdefault('is_valid', lambda form, field, parsed_data: (True, ''))
        kwargs.setdefault('parse', DEFAULT_PARSE)
        kwargs.setdefault('initial')
        kwargs.setdefault('initial_list')
        kwargs.setdefault('template', 'tri_form/{style}_form_row.html')
        kwargs.setdefault('template_string')
        kwargs.setdefault('input_template', 'tri_form/input.html')
        kwargs.setdefault('label_template', 'tri_form/label.html')
        kwargs.setdefault('errors_template', 'tri_form/errors.html')
        kwargs.setdefault('required', True)
        kwargs.setdefault('container_css_classes', set())
        kwargs.setdefault('label_container_css_classes', {'description_container'})
        kwargs.setdefault('input_container_css_classes', set())
        kwargs.setdefault('post_validation', lambda form, field: None)
        kwargs.setdefault('render_value', lambda form, field, value: unicode(value))
        kwargs.setdefault('is_list', False)

        # grab help_text from model if applicable
        # noinspection PyProtectedMember
        kwargs.setdefault('help_text', lambda form, field: '' if form.model is None else form.model._meta.get_field_by_name(field.name)[0].help_text or '')

        kwargs.setdefault('editable', True)
        kwargs.setdefault('strip_input', True)
        kwargs.setdefault('input_type', 'text')
        super(Field, self).__init__(**kwargs)

    @staticmethod
    def hidden(**kwargs):
        kwargs.setdefault('input_type', 'hidden')
        return Field(**kwargs)

    @staticmethod
    def text(**kwargs):
        kwargs.setdefault('input_template', 'tri_form/text.html')
        return Field(**kwargs)

    @staticmethod
    def integer(**kwargs):
        kwargs.setdefault('parse', lambda string_value, **_: int(string_value))
        return Field(**kwargs)

    @staticmethod
    def float(**kwargs):
        kwargs.setdefault('parse', lambda string_value, **_: float(string_value))
        return Field(**kwargs)

    @staticmethod
    def password(**kwargs):
        kwargs['input_type'] = 'password'
        return Field(**kwargs)

    @staticmethod
    def boolean(**kwargs):
        def bool_parse(string_value, **_):
            s = string_value.lower()
            if s in ('1', 'true', 't', 'yes', 'y', 'on'):
                return True
            elif s in ('0', 'false', 'f', 'no', 'n', 'off'):
                return False
            else:
                raise ValueError('%s is not a valid boolean value' % string_value)
        kwargs.setdefault('parse', bool_parse)
        kwargs.setdefault('required', False)
        kwargs.setdefault('template', 'tri_form/{style}_form_row_checkbox.html')
        kwargs.setdefault('input_template', 'tri_form/checkbox.html')
        return Field(**kwargs)

    @staticmethod
    def choice(**kwargs):
        """
        Shortcut for single choice field. If required is false it will automatically add an option first with the value '' and the title 'ALL'. To override that text pass in the parameter empty_label.
        :param empty_label: default 'ALL'
        :param choices: list of objects
        :param choice_to_option: callable with three arguments: form, field, choice. Convert from a choice object to a tuple of (choice, value, label, selected), the last three for the <option> element
        """
        assert 'choices' in kwargs

        if not kwargs.get('required', True):
            kwargs['original_choices'] = kwargs.pop('choices')
            kwargs['choices'] = lambda form, field: [None] + list(evaluate(should_evaluate(field.original_choices), form=form, field=field))
            kwargs['original_parse'] = should_not_evaluate(kwargs.pop('parse', DEFAULT_PARSE))
            kwargs['parse'] = lambda form, field, string_value: None if string_value == '' else field.original_parse(form=form, field=field, string_value=string_value)
        else:
            kwargs['original_choices'] = kwargs['choices']

        def choice_is_valid(form, field, parsed_data):
            del form
            if not field.required and parsed_data is None:
                return True, ''

            return parsed_data in field.choices, '%s not in available choices' % parsed_data

        kwargs.setdefault('empty_choice_tuple', (None, '', 'ALL'))
        kwargs.setdefault('choice_to_option', lambda form, field, choice: (choice, unicode(choice), unicode(choice), choice == field.value))
        kwargs['choice_to_option'] = should_not_evaluate(kwargs['choice_to_option'])
        kwargs.setdefault('input_template', 'tri_form/choice.html')
        kwargs.setdefault('is_valid', choice_is_valid)

        def choice_post_validation(form, field):
            field.choice_tuples = [field.choice_to_option(form=form, field=field, choice=choice) if choice is not None else field.empty_choice_tuple for choice in field.choices]
        kwargs.setdefault('post_validation', choice_post_validation)
        return Field(**kwargs)

    @staticmethod
    def choice_queryset(**kwargs):
        model = kwargs.pop('model')
        kwargs.setdefault('internal', Struct()).model = model
        kwargs.setdefault('parse', lambda form, field, string_value: field.internal.model.objects.get(pk=string_value) if string_value else None)
        kwargs.setdefault('choice_to_option', lambda form, field, choice: (choice, choice.pk, unicode(choice), choice == field.value))

        return Field.choice(**kwargs)

    @staticmethod
    def multi_choice(**kwargs):
        kwargs.setdefault('attrs', {'multiple': ''})
        kwargs.setdefault('choice_to_option', lambda form, field, choice: (choice, unicode(choice), unicode(choice), field.value_list and choice in field.value_list))
        kwargs.setdefault('is_list', True)
        return Field.choice(**kwargs)

    @staticmethod
    def multi_choice_queryset(**kwargs):
        kwargs.setdefault('attrs', {'multiple': ''})
        kwargs.setdefault('choice_to_option', should_not_evaluate(lambda form, field, choice: (choice, choice.pk, unicode(choice), field.value_list and choice in field.value_list)))
        kwargs.setdefault('is_list', True)
        return Field.choice_queryset(**kwargs)

    @staticmethod
    def radio(**kwargs):
        kwargs.setdefault('input_template', 'tri_form/radio.html')
        return Field.choice(**kwargs)

    @staticmethod
    def datetime(**kwargs):
        def parse_datetime(string_value, **_):
            try:
                return datetime.strptime(string_value, '%Y-%m-%d %H:%M:%S')
            except ValueError as e:
                raise ValidationError(e.message)
        kwargs.setdefault('parse', parse_datetime)
        return Field(**kwargs)

    @staticmethod
    def date(**kwargs):
        def parse_date(string_value, **_):
            try:
                return datetime.strptime(string_value, '%Y-%m-%d').date()
            except ValueError as e:
                raise ValidationError(e.message)
        kwargs.setdefault('parse', parse_date)
        return Field(**kwargs)

    @staticmethod
    def time(**kwargs):
        def parse_time(string_value, **_):
            try:
                return datetime.strptime(string_value, '%H:%M:%S').time()
            except ValueError as e:
                raise ValidationError(e.message)
        kwargs.setdefault('parse', parse_time)
        return Field(**kwargs)

    @staticmethod
    def decimal(**kwargs):
        kwargs.setdefault('parse', lambda string_value, **_: Decimal(string_value))
        return Field(**kwargs)

    @staticmethod
    def url(**kwargs):
        kwargs.setdefault('input_type', 'email')
        kwargs.setdefault('parse', lambda string_value, **_: URLValidator(string_value) or string_value)
        return Field(**kwargs)

    @staticmethod
    def heading(label, show=True, template='tri_form/heading.html'):
        """
        Shortcut to create a fake input that performs no parsing but is useful to separate sections of a form.
        """
        kwargs = dict(
            label=label,
            show=show,
            template=template,
            editable=False,
            name='@@heading@@',
        )
        return Field(**kwargs)

    @staticmethod
    def email(**kwargs):
        kwargs.setdefault('input_type', 'email')
        kwargs.setdefault('parse', lambda string_value, **_: validate_email(string_value) or string_value)
        return Field(**kwargs)

    @staticmethod
    def phone_number(**kwargs):
        kwargs.setdefault('is_valid', lambda form, field, parsed_data: (re.match(r'^\+\d{1,3}(( |-)?\(\d+\))?(( |-)?\d+)+$', parsed_data, re.IGNORECASE), 'Please use format +<country code> (XX) XX XX. Example of US number: +1 (212) 123 4567 or +1 212 123 4567'))
        return Field(**kwargs)

    @staticmethod
    def from_model(model, field_name=None, model_field=None, **kwargs):
        if model_field is None:
            # noinspection PyProtectedMember
            model_field = model._meta.get_field(field_name)

        factory = _field_factory_by_django_field_type.get(type(model_field))

        if factory is None:
            for django_field_type, func in reversed(_field_factory_by_django_field_type.items()):
                if isinstance(model_field, django_field_type):
                    factory = func
                    break
        assert factory is not None
        return factory(model_field=model_field, kwargs=kwargs)

    @staticmethod
    def comma_separated(parent_field):
        """
        Shortcut to create a comma separated list of something. You can use this to create a comma separated text input that gives nice validation errors easily. Example:

        .. code::python

            Field.comma_separated(Field.email)

        @type parent_field: Field
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
                    errors.append('Invalid value "%s": %s' % (x, e.message))
                except ValidationError as e:
                    for message in e.messages:
                        errors.append('Invalid value "%s": %s' % (x, message))
            if errors:
                raise ValidationError(errors)
            return ', '.join(result)

        def is_valid_comma_separated(form, field, parsed_data):
            if parsed_data is None:
                return True, None
            errors = set()
            for x in parsed_data.split(','):
                x = x.strip()
                is_valid, error = parent_field.is_valid(form=form, field=field, parsed_data=x)
                if not is_valid:
                    errors.add('Invalid value "%s": %s' % (x, error))
            return errors == set(), errors

        kwargs['parse'] = parse_comma_separated
        kwargs['is_valid'] = is_valid_comma_separated
        return Field(**kwargs)


@declarative(Field, 'fields')
class Form(object):
    def __init__(self, data=None, instance=None, fields=None, model=None):
        """
        Describe a Form. Example:

        .. code::python

            class MyForm(Form):
                a = Field()
                b = Field.email()

            form = MyForm(data={})

        You can also create an instance of a form with this syntax if it's more convenient:

        .. code::python

            form = MyForm(data={}, fields=[Field(name='a'), Field.email(name='b')])

        See tri.declarative docs for more on this dual style of declaration.

        @type fields: list of Field
        @type data: dict[basestring, basestring]
        @type model: django.db.models.Model
        """
        if isinstance(fields, dict):  # Declarative case
            fields = [field + dict(name=name) for name, field in fields.items()]
        self.fields = [BoundField(field, self) for field in fields]

        if instance is not None:
            for field in self.fields:
                if field.attr:
                    field.initial = getattr_path(instance, field.attr)

        if data:
            for field in self.fields:
                if field.is_list:
                    try:
                        raw_data_list = data.getlist(field.name)
                    except AttributeError:  # pragma: no cover
                        raw_data_list = data.get(field.name)
                    if raw_data_list and field.strip_input:
                        raw_data_list = [x.strip() for x in raw_data_list]
                    if raw_data_list is not None:
                        field.raw_data_list = raw_data_list
                else:
                    field.raw_data = data.get(field.name)
                    if field.raw_data and field.strip_input:
                        field.raw_data = field.raw_data.strip()

        self.fields_by_name = {field.name: field for field in self.fields}
        self.style = None
        self.model = model
        self._valid = None
        self.should_parse = data is not None
        self.validate()

    @staticmethod
    def from_model(data, model, instance=None, include=None, exclude=None, **kwargs):
        """
        Create an entire form based on the fields of a model. To override a field parameter send keyword arguments in the form
        of "the_name_of_the_field__param". For example:

        .. code::python

            class Foo(Model):
                foo = IntegerField()

            Form.from_model(data=request.GET, model=Foo, foo__help_text='Overridden help text')

        :param include: fields to include. Defaults to all
        :param exclude: fields to exclude. Defaults to none (except that AutoField is always excluded!)

        """

        def should_include(name):
            if exclude is not None and name in exclude:
                return False
            if include is not None:
                return name in include
            return True

        # noinspection PyProtectedMember
        fields = [Field.from_model(name=field.name, model=model, model_field=field, **extract_subkeys(kwargs, field.name))
                  for field, _ in model._meta.get_fields_with_model()
                  if should_include(field.name) and not isinstance(field, AutoField)]
        return Form(data=data, model=model, instance=instance, fields=fields)

    def is_valid(self):
        if self._valid is None:
            self.validate()
            for field in self.fields:
                if field.errors:
                    self._valid = False
                    break
            else:
                self._valid = True
        return self._valid

    def parse_field_raw_value(self, field, raw_data):
        try:
            return field.parse(form=self, field=field, string_value=raw_data)
        except ValueError as e:
            assert e.message != ''
            field.errors.add(e.message)
        except ValidationError as e:
            for message in e.messages:
                msg = unicode(message)
                assert msg != ''
                field.errors.add(msg)

    def parse(self):
        if not self.should_parse:
            return

        for field in self.fields:
            if field.is_list:
                if field.raw_data_list is not None:
                    field.parsed_data_list = [self.parse_field_raw_value(field, x) for x in field.raw_data_list]
                else:
                    field.parsed_data_list = None
            else:
                if field.raw_data is not None:
                    field.parsed_data = self.parse_field_raw_value(field, field.raw_data)
                else:
                    field.parsed_data = None

    def evaluate(self):
        for field in self.fields:
            field.evaluate()

    def validate(self):
        self.evaluate()

        self.fields = [field for field in self.fields if should_show(field)]
        self.fields_by_name = {field.name: field for field in self.fields}

        self.parse()

        for field in self.fields:
            value = None
            value_list = None
            if field.parsed_data_list is not None or field.initial_list is not None:
                value_list = field.parsed_data_list if self.should_parse else field.initial_list
                value_list = [self.validate_field_parsed_data(field, x) for x in value_list]
            else:
                value = field.parsed_data if self.should_parse else field.initial
                value = self.validate_field_parsed_data(field, value)

            if self.should_parse and not field.errors:
                if field.required and not value and not value_list:
                    field.errors.add('This field is required')

            if not field.errors:
                field.value = value
                field.value_list = value_list

        for field in self.fields:
            field.post_validation(form=self, field=field)
        return self

    def validate_field_parsed_data(self, field, value):
        is_valid, error = field.is_valid(
            form=self,
            field=field,
            parsed_data=value)
        if is_valid and not field.errors and field.parsed_data is not None:
            value = field.parsed_data
        elif not is_valid and self.should_parse:
            if not isinstance(error, set):
                error = {error}
            for e in error:
                assert error != ''
                field.errors.add(e)
        return value

    def __unicode__(self):
        return self.table()

    def compact(self):
        return self.render(style='compact')

    def table(self):
        return self.render(style='table')

    def render(self, style):
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
        return mark_safe('\n'.join(r))

    def apply(self, instance):
        """
        Write the new values specified in the form into the instance specified.
        """
        assert self.is_valid()
        for field in self.fields:
            if field.attr is not None:
                if field.value is not None:
                    setattr_path(instance, field.attr, field.value)
                else:
                    setattr_path(instance, field.attr, field.value_list)
