from pathlib import Path
from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag(takes_context=True)
def iommi_language_code(context):
    request = context.get('request')
    if request:
        return getattr(request, 'LANGUAGE_CODE', settings.LANGUAGE_CODE)
    return settings.LANGUAGE_CODE


@register.filter
def basename(value):
    return Path(value).name


@register.filter
def file_type(value):
    return Path(value).suffix.lstrip('.')


@register.filter
def is_image_thumb_allowed(value):
    return file_type(value) in ('jpg', 'jpeg', 'gif', 'png', 'bmp', 'jif', 'jfif', 'jfi', 'webp', 'avif', 'svg')
