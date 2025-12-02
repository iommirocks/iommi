from pathlib import Path
from django import template

register = template.Library()


@register.filter
def basename(value):
    return Path(value).name


@register.filter
def file_type(value):
    return Path(value).suffix.lstrip('.')


@register.filter
def is_image_thumb_allowed(value):
    return file_type(value) in ('jpg', 'jpeg', 'gif', 'png', 'bmp', 'jif', 'jfif', 'jfi', 'webp', 'avif', 'svg')
