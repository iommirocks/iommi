from collections import defaultdict
from typing import (
    List,
    Type,
)

from ._web_compat import settings
from tri_declarative import (
    get_shortcuts_by_name,
    Namespace,
    RefinableObject,
)

from iommi.base import (
    items,
    keys,
)

DEFAULT_STYLE = 'bootstrap'


def apply_style(obj):
    style_data = get_style_data_for_object(style_name=get_style_name_for(obj), obj=obj)
    return apply_style_recursively(style_data=style_data, obj=obj)


def get_style_name_for(obj):
    if obj is not None:
        if obj.iommi_style is not None:
            return obj.iommi_style
        if obj._parent is not None:
            return get_style_name_for(obj._parent)

    return getattr(settings, 'IOMMI_DEFAULT_STYLE', DEFAULT_STYLE)


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
    def __init__(self, *bases, base_template=None, content_block=None, **kwargs):
        self.name = None

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

        self.config = Namespace(*[x.config for x in bases], recursive_namespace(kwargs))

    def component(self, obj):
        result = Namespace()

        # TODO: is this wrong? Should it take classes first, then loop through shortcuts?
        for class_name in class_names_for(type(obj)):
            if class_name in self.config:
                config = Namespace(self.config.get(class_name, {}))
                shortcuts_config = Namespace(config.pop('shortcuts', {}))
                result.update(config)

                for shortcut_name in reversed(getattr(obj, '__tri_declarative_shortcut_stack', [])):
                    result = Namespace(result, shortcuts_config.get(shortcut_name, {}))
        return result


_styles = {}


def register_style(name, conf):
    assert name not in _styles
    assert conf.name is None
    conf.name = name
    _styles[name] = conf


def get_style(name):
    try:
        return _styles[name]
    except KeyError:
        style_names = "\n    ".join(_styles.keys())
        raise Exception(f'''No registered style {name}. Register a style with register_style(). 

Available styles:
    {style_names}''') from None


_no_attribute_sentinel = object()


def apply_style_recursively(*, style_data, obj):
    from iommi.member import NotBoundYet, MemberBinder, Members
    if isinstance(obj, NotBoundYet):
        return style_data

    rest_style = Namespace()
    if isinstance(obj, dict):
        result = Namespace(style_data, obj)
        obj.clear()
        obj.update(**result)
    else:
        for k, v in items(style_data):
            if isinstance(v, dict):
                if isinstance(obj, Members):
                    try:
                        child = obj._bound_members[k]
                    except KeyError:
                        child = getattr(obj, k)
                else:
                    child = getattr(obj, k)

                if isinstance(child, MemberBinder):
                    child = obj._bound_members[k]
                if child is not None:
                    rest = apply_style_recursively(style_data=v, obj=child)
                    if rest:
                        rest_style[k] = rest
            else:
                attrib = getattr(obj, k, _no_attribute_sentinel)
                if attrib is _no_attribute_sentinel:
                    raise InvalidStyleConfigurationException(f'Object {obj!r} has no attribute {k} which the style tried to set.')
                if attrib is None:
                    setattr(obj, k, v)
    return rest_style


def get_style_data_for_object(style_name, obj):
    return get_style(style_name).component(obj)


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
        DebugMenu,
    )
    from iommi.error import Errors
    from iommi.action import Actions
    from iommi.admin import Admin
    from iommi.fragment import Container
    if default_classes is None:
        default_classes = [
            Action,
            Actions,
            Column,
            DebugMenu,
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
            f'    Style: {style_name} - class: {cls_name}'
            for style_name, cls_name in invalid_class_names
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
