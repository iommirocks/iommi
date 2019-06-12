from tri_declarative import Shortcut

try:
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email, URLValidator
    from django.http import HttpResponse
    from django.template import RequestContext
    from django.template.loader import render_to_string
    from django.utils.html import format_html
    from django.utils.text import slugify
    from django.http import HttpResponseRedirect
    from django.template import Template
    from django.shortcuts import render
    from django.utils.encoding import smart_text
    from django.template.context_processors import csrf
    from django.utils.safestring import mark_safe

    try:
        from django.template.loader import get_template_from_string
    except ImportError:  # pragma: no cover
        # Django 1.8+
        # noinspection PyUnresolvedReferences
        from django.template import engines

        def get_template_from_string(template_code, origin=None, name=None):
            del origin, name  # the origin and name parameters seems not to be implemented in django 1.8
            return engines['django'].from_string(template_code)

    def setup_db_compat():
        from tri_form import register_field_factory
        from django.db.models import IntegerField, FloatField, TextField, BooleanField, AutoField, CharField, \
            DateField, DateTimeField, DecimalField, EmailField, URLField, TimeField, \
            ForeignKey, ManyToManyField, FileField, ManyToOneRel, ManyToManyRel

        # The order here is significant because of inheritance structure. More specific must be below less specific.
        register_field_factory(CharField, Shortcut())
        register_field_factory(URLField, Shortcut(call_target__attribute='url'))
        register_field_factory(TimeField, Shortcut(call_target__attribute='time'))
        register_field_factory(EmailField, Shortcut(call_target__attribute='email'))
        register_field_factory(DecimalField, Shortcut(call_target__attribute='decimal'))
        register_field_factory(DateField, Shortcut(call_target__attribute='date'))
        register_field_factory(DateTimeField, Shortcut(call_target__attribute='datetime'))
        register_field_factory(
            BooleanField,
            lambda model_field, **kwargs: (
                Shortcut(call_target__attribute='boolean')
                if not model_field.null
                else Shortcut(call_target__attribute='boolean_tristate')
            )
        )
        register_field_factory(TextField, Shortcut(call_target__attribute='textarea'))
        register_field_factory(FloatField, Shortcut(call_target__attribute='float'))
        register_field_factory(IntegerField, Shortcut(call_target__attribute='integer'))
        register_field_factory(AutoField, Shortcut(call_target__attribute='integer', show=False))
        register_field_factory(ManyToOneRel, None)
        register_field_factory(ManyToManyRel, None)
        register_field_factory(FileField, Shortcut(call_target__attribute='file'))
        register_field_factory(ForeignKey, Shortcut(call_target__attribute='foreign_key'))
        register_field_factory(ManyToManyField, Shortcut(call_target__attribute='many_to_many'))

    def field_defaults_factory(model_field):
        from tri_form import capitalize
        from django.db.models import BooleanField
        r = {}
        if hasattr(model_field, 'verbose_name'):
            r['display_name'] = capitalize(model_field.verbose_name)

        if hasattr(model_field, 'null') and not isinstance(model_field, BooleanField):
            r['required'] = not model_field.null and not model_field.blank

        if hasattr(model_field, 'null'):
            r['parse_empty_string_as_none'] = model_field.null

        return r

    def render_template(request, template, context):
        """
        @type request: django.http.HttpRequest
        @type template: str|django.template.Template|django.template.backends.django.Template
        @type context: dict
        """
        import six
        from tri_form.compat import Template
        if template is None:
            return ''
        elif isinstance(template, six.string_types):
            # positional arguments here to get compatibility with django 1.8+
            return render_to_string(template, context, request=request)
        elif isinstance(template, Template):
            return template.render(RequestContext(request, context))
        else:
            return template.render(context, request)

except ImportError:
    from jinja2 import Markup
    from jinja2 import Template as _Template
    from flask import render_template as render
    from flask import Response as _Response
    from flask import Request as _Request

    csrf = None

    class HttpResponse:
        def __init__(self, content, content_type=None):
            self.r = _Response(content, content_type=content_type)

        @property
        def content(self):
            return self.r.get_data()

        @property
        def _headers(self):
            return {k.lower(): [v] for k, v in self.r.headers._list}

    class HttpRequest:

        def __init__(self, environ):
            self.r = _Request(environ)

        @property
        def POST(self):
            return self.r.form

        @property
        def GET(self):
            return self.r.args

        @property
        def method(self):
            return self.r.method

    def format_html(format_string, *args, **kwargs):
        return Markup(format_string).format(*args, **kwargs)

    class ValidationError(Exception):
        def __init__(self, messages):
            if isinstance(messages, list):
                self.messages = messages
            else:
                self.messages = [messages]

    def HttpResponseRedirect(url, code=302):
        from flask import redirect
        return redirect(url, code=code)

    def smart_text(s):
        return str(s)

    def render_template(request, template, context):
        if template is None:
            return ''

        if isinstance(template, str):
            return Markup(render(template, **(context or {})))
        else:
            return Markup(template.render(context=context, request=request))

    def validate_email(s):
        if '@' not in s:
            raise ValidationError(messages=['Enter a valid email address.'])

        return s

    class URLValidator:
        def __call__(self, string_value):
            if '://' not in string_value:
                raise ValidationError('Enter a valid URL.')

    def get_template_from_string(s, origin=None, name=None):
        return Template(s)

    def render_to_string(template_name, context, request=None):
        return format_html(render(template_name, request=request, **context))

    class Template:
        def __init__(self, template_string, **kwargs):
            self.template = _Template(template_string, **kwargs)

        def render(self, context, request=None):
            return self.template.render(**context)

    def slugify(s):
        return s.lower().replace(' ', '-')

    def setup_db_compat():
        pass

    def field_defaults_factory(model_field):
        raise NotImplementedError()

    def mark_safe(s):
        return Markup(s)
