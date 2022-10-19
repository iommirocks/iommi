import warnings
from collections import defaultdict
from contextlib import contextmanager
from typing import (
    Any,
    List,
    Type,
    Union,
)

from django.conf import settings

from iommi.base import (
    items,
    keys,
)
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    EMPTY,
    Namespace,
)
from iommi.refinable import RefinableObject
from iommi.shortcut import get_shortcuts_by_name

DEFAULT_STYLE = 'bootstrap'


def get_style_object(obj: Any) -> 'Style':
    return get_global_style(obj.iommi_style)


def _style_name_for_class(cls):
    return cls.__name__.rpartition('.')[-1]  # this converts iommi.form.Form to just Form


def class_names_for(cls):
    from iommi import Part
    from iommi.traversable import Traversable

    for base_class in reversed(cls.mro()):
        if base_class in (object, Part, RefinableObject, Traversable):
            continue
        yield _style_name_for_class(base_class)


def recursive_namespace(d):
    if isinstance(d, dict):
        return Namespace({k: recursive_namespace(v) for k, v in items(d)})
    else:
        return d


class Style:
    @dispatch(
        root=EMPTY,
        sub_styles=EMPTY,
    )
    def __init__(
        self, *bases, base_template=None, content_block=None, root=None, internal=False, sub_styles=None, **kwargs
    ):
        self.name = None
        self.internal = internal
        self.bases = bases

        self.base_template = base_template
        if not self.base_template:
            for base in reversed(bases):
                if base.base_template:
                    self.base_template = base.base_template
                    break

        self.content_block = content_block
        if not self.content_block:
            for base in reversed(bases):
                if base.content_block:
                    self.content_block = base.content_block
                    break

        self.root = {k: v for k, v in items(Namespace(*(base.root for base in bases), root)) if v is not None}
        self.config = Namespace(*[x.config for x in bases], recursive_namespace(kwargs))

        for k, v in items(self.config):
            if k[0].islower():
                warnings.warn(f"Style definition got the keyword {k} which starts with a lowercase letter. Classes should start with an uppercase letter. Either you made a mistake in passing something that won't match any config, or you should rename your class to start with a capital letter.")

        sub_style_names = list(sub_styles)
        for base in bases:
            for n in base.sub_styles:
                if n not in sub_style_names:
                    sub_style_names.append(n)

        self.sub_styles = {}
        for k in sub_style_names:
            v = sub_styles.get(k, {})
            if isinstance(v, Style):
                self.sub_styles[k] = v
            else:
                sub_style_bases = [self]
                for base in bases:
                    sub_style_base = base.sub_styles.get(k)
                    if sub_style_base:
                        sub_style_bases.append(sub_style_base)
                self.sub_styles[k] = Style(*sub_style_bases, **v)

        for name, sub_style in items(self.sub_styles):
            sub_style.name = name

    def resolve(self, obj, is_root=False):
        """
        Calculate the namespaces of additional argument that should be applied
        to the given object. If is_root is set to True, assets might also be
        added to the namespace.
        """
        result = []

        for class_name in class_names_for(type(obj)):
            if class_name in self.config:
                config = dict(self.config.get(class_name))
                shortcuts_config = config.pop('shortcuts', {})
                if config:
                    result.append(config)

                for shortcut_name in reversed(getattr(obj, 'iommi_shortcut_stack', [])):
                    config = shortcuts_config.get(shortcut_name)
                    if config:
                        result.append(config)

        if is_root and self.root:
            result.append(self.root)

        return result

    def __repr__(self):
        return f'<Style: {self.name}>'


_styles = {}


def register_style(name, style):
    assert name not in _styles, f'{name} is already registered'
    assert style.name is None
    style.name = name
    _styles[name] = style

    @contextmanager
    def _unregister():
        try:
            yield style
        finally:
            unregister_style(name)

    return _unregister()


def unregister_style(name):
    assert name in _styles
    del _styles[name]


def get_global_style(name):
    if isinstance(name, Style):
        return name
    try:
        return _styles[name]
    except KeyError:
        style_names = "\n    ".join(_styles.keys())

        if not style_names:
            'No styles registered! Did you forget to add iommi to INSTALLED_APPS?'

        raise Exception(
            f'''No registered iommi style {name}. Register a style with register_style().

Available styles:
    {style_names}'''
        ) from None


class InvalidStyleConfigurationException(Exception):
    pass


def validate_styles(*, additional_classes: List[Type] = None, default_classes=None, styles=None):
    """
    This function validates all registered styles against all standard
    classes. If you have more classes you need to have checked against,
    pass these as the `classes` argument.

    The `default_classes` parameter can be used to say which classes are
    checked for valid data. By default this is all the `Part`-derived
    classes in iommmi. This parameter is primarily used by tests.

    The `styles` parameter can be used to specify which exact styles to
    validate. By default it will validate all registered styles. This
    parameter is primarily used by tests.
    """
    if default_classes is None:
        from iommi import (
            Action,
            Column,
            Field,
            Form,
            Menu,
            MenuItem,
            Query,
            Table,
            Filter,
        )
        from iommi.table import Paginator
        from iommi.menu import (
            MenuBase,
            get_debug_menu,
        )
        from iommi.error import Errors
        from iommi.action import Actions
        from iommi.admin import Admin
        from iommi.fragment import Container
        from iommi.fragment import Header
        from iommi.live_edit import LiveEditPage
        from iommi.form import FieldGroup

        default_classes = [
            Action,
            Actions,
            Column,
            get_debug_menu().__class__,
            Errors,
            Field,
            Form,
            Menu,
            MenuBase,
            MenuItem,
            Paginator,
            Query,
            Table,
            Filter,
            Admin,
            Container,
            Header,
            LiveEditPage,
            FieldGroup,
        ]
    if additional_classes is None:
        additional_classes = []

    classes = default_classes + additional_classes

    if styles is None:
        styles = _styles

    # We can have multiple classes called Field. In fact that's the recommended way to use iommi!
    classes_by_name = defaultdict(list)
    for cls in classes:
        for cls_name in class_names_for(cls):
            classes_by_name[cls_name].append(cls)

    # This will functionally merge separate trees of class inheritance. So it produces a list of all shortcuts on all classes called something.Field.
    shortcuts_available_by_class_name = defaultdict(set)
    for cls_name, classes in items(classes_by_name):
        for cls in classes:
            shortcuts_available_by_class_name[cls_name].update(get_shortcuts_by_name(cls).keys())

    invalid_class_names = []
    non_existent_shortcut_names = []
    for style_name, style in items(styles):
        for cls_name, config in items(style.config):
            # First validate the top level classes
            if cls_name not in classes_by_name:
                invalid_class_names.append((style_name, cls_name))
                continue

            # Then validate the shortcuts
            for shortcut_name in keys(config.get('shortcuts', {})):
                if shortcut_name not in shortcuts_available_by_class_name[cls_name]:
                    non_existent_shortcut_names.append((style_name, cls_name, shortcut_name))

    if invalid_class_names or non_existent_shortcut_names:
        invalid_class_names_str = '\n'.join(
            f'    Style: {style_name} - class: {cls_name}' for style_name, cls_name in invalid_class_names
        )
        if invalid_class_names_str:
            invalid_class_names_str = 'Invalid class names:\n' + invalid_class_names_str
        invalid_shortcut_names_str = '\n'.join(
            f'    Style: {style_name} - class: {cls_name} - shortcut: {shortcut_name}'
            for style_name, cls_name, shortcut_name in non_existent_shortcut_names
        )
        if invalid_shortcut_names_str:
            invalid_shortcut_names_str = 'Invalid shortcut names:\n' + invalid_shortcut_names_str
        raise InvalidStyleConfigurationException('\n\n'.join([invalid_class_names_str, invalid_shortcut_names_str]))


def resolve_style(iommi_style: Union[str, Style], enclosing_style: Style = None):
    if isinstance(iommi_style, Style):
        return iommi_style

    if not enclosing_style:
        default_style = get_global_style(getattr(settings, 'IOMMI_DEFAULT_STYLE', DEFAULT_STYLE))
        enclosing_style = default_style

    if iommi_style is None:
        return enclosing_style

    sub_style = enclosing_style.sub_styles.get(iommi_style)
    if sub_style is not None:
        return sub_style

    return get_global_style(iommi_style)
