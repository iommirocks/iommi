from tri_form.compat import mark_safe


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
                    yield '%s' % (key, )
                    continue
                if isinstance(value, dict):
                    if key == 'class':
                        if not value:
                            continue
                        value = render_class(value)
                    elif key == 'style':
                        if not value:
                            continue
                        value = render_style(value)
                    else:
                        raise TypeError('Only the class and style attributes can be dicts, you sent %s' % value)
                elif isinstance(value, (list, tuple)):
                    raise TypeError("Attributes can't be of type %s, you sent %s" % (type(value).__name__, value))
                elif callable(value):
                    raise TypeError("Attributes can't be callable, you sent %s" % value)
                yield '%s="%s"' % (key, ('%s' % value).replace('"', '&quot;'))
        return mark_safe(' %s' % ' '.join(parts()))
    return ''


def render_class(class_dict):
    return ' '.join(sorted(name for name, flag in class_dict.items() if flag))


def render_style(class_dict):
    return '; '.join(sorted(('%s: %s' % (k, v)) for k, v in class_dict.items()))
