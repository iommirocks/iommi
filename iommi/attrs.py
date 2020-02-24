from django.utils.safestring import mark_safe
from tri_declarative import (
    evaluate_strict,
    Namespace,
)


def evaluate_attrs(obj, **kwargs):
    attrs = obj.attrs or {}
    return Attrs(
        obj,
        **{
            'class': {
                k: evaluate_strict(v, **kwargs)
                for k, v in attrs.get('class', {}).items()
            }
        },
        style={
            k: evaluate_strict(v, **kwargs)
            for k, v in attrs.get('style', {}).items()
        },
        **{
            k: evaluate_strict(v, **kwargs)
            for k, v in attrs.items()
            if k not in ('class', 'style')
        },
    )


def render_attrs(attrs):
    """
    Render HTML attributes, or return '' if no attributes needs to be rendered.
    """
    if attrs is not None:
        if not attrs:
            return ''

        def parts():
            for key, value in sorted(attrs.items()):
                if value is None:
                    continue
                if value is True:
                    yield f'{key}'
                    continue
                if isinstance(value, dict):
                    if key == 'class':
                        if not value:
                            continue
                        value = render_class(value)
                        if not value:
                            continue
                    elif key == 'style':
                        if not value:
                            continue
                        value = render_style(value)
                        if not value:
                            continue
                    else:
                        raise TypeError(f'Only the class and style attributes can be dicts, you sent {value}')
                elif isinstance(value, (list, tuple)):
                    raise TypeError(f"Attributes can't be of type {type(value).__name__}, you sent {value}")
                elif callable(value):
                    raise TypeError(f"Attributes can't be callable, you sent {value} for key {key}")
                v = f'{value}'.replace('"', '&quot;')
                yield f'{key}="{v}"'
        return mark_safe(' %s' % ' '.join(parts()))
    return ''


class Attrs(Namespace):
    def __init__(self, parent, **attrs):
        from iommi.debug import iommi_debug_on

        if iommi_debug_on() and getattr(parent, '_name', None) is not None:
            attrs['data-iommi-path'] = parent.iommi_dunder_path

        if 'style' in attrs and not attrs['style']:
            del attrs['style']

        if 'class' in attrs and not attrs['class']:
            del attrs['class']

        super(Attrs, self).__init__(attrs)

    def __str__(self):
        return self.__html__()

    # noinspection PyUnusedLocal
    def __html__(self, *, context=None):
        return render_attrs(self)


def render_class(class_dict):
    return ' '.join(sorted(name for name, flag in class_dict.items() if flag))


def render_style(class_dict):
    return '; '.join(sorted(f'{k}: {v}' for k, v in class_dict.items() if v))
