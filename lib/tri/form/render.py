from tri.form.compat import mark_safe


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
                if key == 'class' and isinstance(value, dict):
                    if not value:
                        continue
                    value = render_class(value)
                if key == 'style' and isinstance(value, dict):
                    if not value:
                        continue
                    value = render_style(value)
                yield '%s="%s"' % (key, ('%s' % value).replace('"', '&quot;'))
        return mark_safe(' %s' % ' '.join(parts()))
    return ''


def render_class(class_dict):
    return ' '.join(sorted(name for name, flag in class_dict.items() if flag))


def render_style(class_dict):
    return '; '.join(sorted(('%s: %s' % (k, v)) for k, v in class_dict.items()))
