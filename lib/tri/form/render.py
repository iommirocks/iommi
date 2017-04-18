from django.utils.safestring import mark_safe


def render_attrs(attrs):
    """
    Render HTML attributes, or return '' if no attributes needs to be rendered.
    """
    if attrs is not None:
        def parts():
            for key, value in sorted(attrs.items()):
                if value is None:
                    continue
                if value is True:
                    yield '%s' % (key, )
                    continue
                if isinstance(value, dict):
                    if not value:
                        continue
                    value = render_class(value)
                yield '%s="%s"' % (key, ('%s' % value).replace('"', '&quot;'))
        return mark_safe(' %s' % ' '.join(parts()))
    return ''


def render_class(class_dict):
    return ' '.join(sorted(name for name, flag in class_dict.items() if flag))
