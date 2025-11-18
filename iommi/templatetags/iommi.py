from pathlib import Path
from django import template

register = template.Library()

@register.filter
def basename(value):
    return Path(value).name

@register.filter
def file_type(value):
    return Path(value).suffix.lstrip('.')
