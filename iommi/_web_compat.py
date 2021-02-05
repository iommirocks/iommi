from django.template.utils import InvalidTemplateEngineError

template_types = tuple()

try:
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email, URLValidator
    from django.http import HttpResponse
    from django.http import QueryDict  # noqa: F401
    from django.template import RequestContext
    from django.template.loader import render_to_string
    from django.template.loader import get_template  # noqa: F401
    from django.template.exceptions import TemplateDoesNotExist  # noqa: F401
    from django.utils.html import format_html
    from django.utils.text import slugify
    from django.http import HttpResponseRedirect
    from django.shortcuts import render
    from django.utils.encoding import smart_str
    from django.template.context_processors import csrf as csrf_
    from django.utils.safestring import mark_safe
    from django.http import HttpRequest
    from django.http.response import HttpResponseBase

    DjangoTemplate = None
    JinjaTemplate = None

    from django.conf import settings

    if not settings.TEMPLATES or any('DjangoTemplates' in x['BACKEND'] for x in settings.TEMPLATES):
        from django.template import Template as DjangoTemplate

        template_types = template_types + (DjangoTemplate,)
    else:
        assert any('Jinja2' in x['BACKEND'] for x in settings.TEMPLATES)
        import jinja2  # noqa: F401
        from jinja2 import Template as JinjaTemplate

        template_types = template_types + (JinjaTemplate,)

    class Template:
        def __init__(self, template_string):
            self.s = template_string

        def render(self, context):
            if DjangoTemplate is not None:
                return DjangoTemplate(self.s).render(context=context)
            else:
                assert JinjaTemplate is not None
                return JinjaTemplate(self.s).render(**context.flatten())

    template_types = template_types + (Template,)

    def csrf(request):
        return {} if request is None else csrf_(request)

    try:
        from django.template.loader import get_template_from_string
    except ImportError:  # pragma: no cover
        # Django 1.8+
        # noinspection PyUnresolvedReferences
        from django.template import engines

        def get_template_from_string(template_code, origin=None, name=None):
            del origin, name  # the origin and name parameters seems not to be implemented in django 1.8
            try:
                engine = engines['django']
            except InvalidTemplateEngineError:
                engine = engines.all()[0]

            return engine.from_string(template_code)

    def render_template(request, template, context):
        """
        @type request: django.http.HttpRequest
        @type template: str|django.template.Template|django.template.backends.django.Template
        @type context: dict
        """
        from iommi._web_compat import template_types

        if template is None:
            return ''
        elif isinstance(template, str):
            return mark_safe(render_to_string(template_name=template, context=context, request=request))
        elif isinstance(template, template_types):
            return mark_safe(template.render(context=RequestContext(request, context)))
        else:
            return mark_safe(template.render(context, request))


except ImportError:  # pragma: no cover This flask support is a work in progress/future plan
    from jinja2 import Markup
    from flask import render_template as render
    from ._web_compat_flask import HttpRequest  # noqa: F401

    csrf = None

    class HttpResponse:
        def __init__(self, content, content_type=None):
            from flask import Response

            self.r = Response(content, content_type=content_type)

        @property
        def content(self):
            return self.r.get_rows()

        @property
        def _headers(self):
            return {k.lower(): [v] for k, v in self.r.headers._list}

    HttpResponseBase = HttpResponse

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

    def smart_str(s):
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
            from jinja2 import Template

            self.template = Template(template_string, **kwargs)

        def render(self, context, request=None):
            return self.template.render(**context)

    def slugify(s):
        return s.lower().replace(' ', '-')

    def mark_safe(s):
        return Markup(s)
