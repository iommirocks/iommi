from iommi._web_compat import mark_safe

# TODO: this package name is silly


# TODO: inline this into Attrs
from tri_declarative import (
    Namespace,
    EMPTY,
    dispatch,
)


def render_attrs(attrs):
    """
    Render HTML attributes, or return '' if no attributes needs to be rendered.
    """
    if attrs is not None:
        if not attrs:
            return ' '

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


def render_class(class_dict):
    return ' '.join(sorted(name for name, flag in class_dict.items() if flag))


def render_style(class_dict):
    return '; '.join(sorted(f'{k}: {v}' for k, v in class_dict.items()))


class Attrs(Namespace):
    def __init__(self, attrs):
        super(Attrs, self).__init__(attrs)

    def __html__(self):
        return str(self)

    def __str__(self):
        return self.as_html()

    # noinspection PyUnusedLocal
    def as_html(self, *, context=None):
        return render_attrs(self)


class Errors(set):
    @dispatch(
        attrs=EMPTY,
    )
    def __init__(self, *, parent, attrs, errors=None, template=None):
        super(Errors, self).__init__(errors or [])
        self.parent = parent
        self.attrs = attrs
        self.template = template

    def __html__(self):
        return str(self)

    def __str__(self):
        return self.as_html()

    def __bool__(self):
        return len(self) != 0

    # noinspection PyUnusedLocal
    def as_html(self, *, context=None):
        if not self:
            return ''

        from iommi.page import Fragment
        return Fragment(
            child='',
            tag='ul',
            attrs=self.attrs,
            template=self.template,
            children=[Fragment(tag='li') for error in self],
        ).bind(parent=self.parent).as_html()
