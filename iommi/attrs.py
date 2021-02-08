from tri_declarative import Namespace

from iommi._web_compat import mark_safe
from iommi.base import items
from iommi.evaluate import evaluate_strict


def evaluate_attrs(obj, **kwargs):
    attrs = obj.attrs or {}

    # Micro optimization
    from iommi.debug import iommi_debug_on

    if not attrs and not iommi_debug_on():
        return ''

    classes = evaluate_strict(attrs.get('class', {}), **kwargs)

    assert not isinstance(
        classes, str
    ), """CSS classes needs to be specified as dicts, not as strings. So you want something like:
    field__class__foo=True

or

    field__class={'foo-bar': true}"""

    styles = evaluate_strict(attrs.get('style', {}), **kwargs)

    assert not isinstance(
        styles, str
    ), """CSS styles needs to be specified as dicts, not as strings. So you want something like:
        field__style__display='none'

    or

        field__style={'background-color': 'blue'}"""

    return Attrs(
        obj,
        **{'class': {k: evaluate_strict(v, **kwargs) for k, v in items(classes)}},
        style={k: evaluate_strict(v, **kwargs) for k, v in items(styles)},
        **{k: evaluate_strict(v, **kwargs) for k, v in items(attrs) if k not in ('class', 'style')},
    )


def render_attrs(attrs):
    """
    Render HTML attributes, or return '' if no attributes needs to be rendered.
    """
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
                    raise TypeError(f'Only the class and style attributes can be dicts, you sent {value} for key {key}')
            elif isinstance(value, (list, tuple)):
                raise TypeError(f"Attributes can't be of type {type(value).__name__}, you sent {value} for key {key}")
            elif callable(value):
                from .docs import get_docs_callable_description

                raise TypeError(
                    f"Attributes can't be callable, you sent {get_docs_callable_description(value)} for key {key}"
                )
            v = f'{value}'.replace('"', '&quot;')
            yield f'{key}="{v}"'

    r = mark_safe(' %s' % ' '.join(parts()))
    return '' if r == ' ' else r


class Attrs(Namespace):
    """
    The `attrs` namespace on `Field`, `Form`, `Header`, `Cell` and more is used to customize HTML attributes.

    .. code:: python

        form = Form(
            auto__model=Album,
            fields__artist__attrs__foo='bar',
            fields__name__attrs__class__bar=True,
            fields__name__attrs__style__baz='qwe',
        )

    or more succinctly:

    .. code:: python

        form = Form(
            auto__model=Album,
            fields__artist__attrs__foo='bar',
            fields__name__attrs=dict(
                class__bar=True,
                style__baz='qwe',
            )
        )


    The thing to remember is that the basic namespace is a dict with key value
    pairs that gets projected out into the HTML, but there are two special cases
    for `style` and `class`. The example above will result in the following
    attributes on the field tag:

    .. code:: html

       <div foo="bar" class="bar" style="baz: qwe">

    The values in these dicts can be callables:

    .. code:: python

        form = Form(
            auto__model=Album,
            fields__name__attrs__class__bar=
                lambda request, **_: request.user.is_staff,
        )
    """

    def __init__(self, parent, **attrs):
        from iommi.debug import iommi_debug_on

        if iommi_debug_on() and getattr(parent, '_name', None) is not None:
            attrs['data-iommi-path'] = parent.iommi_dunder_path
            attrs['data-iommi-type'] = type(parent).__name__

        super(Attrs, self).__init__(attrs)

    def __str__(self):
        return self.__html__()

    # noinspection PyUnusedLocal
    def __html__(self):
        return render_attrs(self)


def render_class(class_dict):
    return ' '.join(sorted(name for name, flag in items(class_dict) if flag))


def render_style(class_dict):
    return '; '.join(sorted(f'{k}: {v}' for k, v in items(class_dict) if v))
