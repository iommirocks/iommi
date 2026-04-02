from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template import RequestContext
from django.template.backends.django import Template as DjangoLoadedTemplate
from django.template.loader import render_to_string
from django.utils.html import format_html as django_format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe

DjangoTemplate = None
JinjaTemplate = None


_template_types = tuple()

_template_types_initialized = False


def _init_template_types():
    global DjangoTemplate, JinjaTemplate, _template_types, _template_types_initialized
    if _template_types_initialized:
        return
    _template_types_initialized = True

    try:
        if not settings.TEMPLATES or any('DjangoTemplates' in x['BACKEND'] for x in settings.TEMPLATES):
            from django.template import Template as DT

            DjangoTemplate = DT
            _template_types += (DjangoTemplate, DjangoLoadedTemplate)

        if any('Jinja2' in x['BACKEND'] for x in settings.TEMPLATES):
            import jinja2  # noqa: F401
            from jinja2 import Template as JT

            JinjaTemplate = JT
            _template_types += (JinjaTemplate,)
    except ImproperlyConfigured:
        pass

    _template_types = _template_types + (Template,)


def get_template_types():
    _init_template_types()
    return _template_types


def format_html(s, *args, **kwargs):
    if not args and not kwargs:
        return mark_safe(s)
    return django_format_html(s, *args, **kwargs)


class Template:
    def __init__(self, template_string):
        self.s = template_string

    def render(self, context):
        _init_template_types()
        if DjangoTemplate is not None:
            return DjangoTemplate(self.s).render(context=context)
        else:
            assert JinjaTemplate is not None
            return JinjaTemplate(self.s).render(**context.flatten())


def safe_redirect_url(url, request, fallback='/'):
    if url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}):
        return url
    return fallback


def log_used_template(request, item):
    if item is None:
        return

    if request is not None:
        if isinstance(item, (str, DjangoLoadedTemplate)):
            if not hasattr(request, 'iommi_used_templates'):
                request.iommi_used_templates = []
            request.iommi_used_templates.append(item)


def render_template(request, template, context):
    """
    @type request: django.http.HttpRequest
    @type template: str|django.template.Template|django.template.backends.django.Template
    @type context: dict
    """
    log_used_template(request, template)

    if template is None:
        return ''
    elif isinstance(template, str):
        return mark_safe(render_to_string(template_name=template, context=context, request=request))
    elif isinstance(template, DjangoLoadedTemplate):
        return mark_safe(template.render(context=context, request=request))
    elif isinstance(template, get_template_types()):
        return mark_safe(template.render(context=RequestContext(request, context)))
    else:
        return mark_safe(template.render(context, request))
