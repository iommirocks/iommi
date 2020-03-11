from collections import defaultdict
from typing import (
    List,
    Type,
)

from django.conf import settings
from tri_declarative import (
    get_shortcuts_by_name,
    Namespace,
    RefinableObject,
)

DEFAULT_STYLE = 'bootstrap'


def apply_style(obj):
    style = get_style_obj_for_object(style=get_style_for(obj), obj=obj)
    apply_style_recursively(style_data=style, obj=obj)


def get_style_for(obj):
    if obj.iommi_style is not None:
        return obj.iommi_style
    if obj._parent is not None:
        return get_style_for(obj._parent)

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
        return Namespace({k: recursive_namespace(v) for k, v in d.items()})
    else:
        return d


class Style:
    def __init__(self, *bases, **kwargs):
        self.name = None
        self.config = Namespace(*[x.config for x in bases], recursive_namespace(kwargs))

    def component(self, obj):
        result = Namespace()
        for class_name in class_names_for(type(obj)):
            if class_name in self.config:
                config = Namespace(self.config.get(class_name, {}))
                shortcuts_config = Namespace(config.pop('shortcuts', {}))
                result.update(config)

                for shortcut_name in reversed(getattr(obj, '__tri_declarative_shortcut_stack', [])):
                    result = Namespace(result, shortcuts_config.get(shortcut_name, {}))
        return result


base = Style(
    Form=dict(
        template='iommi/form/form.html',
        actions_template='iommi/form/actions.html',
    ),
    Field=dict(
        shortcuts=dict(
            boolean=dict(
                input__attrs__type='checkbox',
                template='iommi/form/row_checkbox.html',
            ),
            choice=dict(
                input__template='iommi/form/choice.html',
                input__attrs__value=None,
                input__attrs__type=None,
            ),
            choice_queryset=dict(
                input__template='iommi/form/choice_select2.html',
            ),
            radio=dict(
                input__template='iommi/form/radio.html',
            ),
            heading=dict(
                template='iommi/form/heading.html',
            ),
        ),
        input__attrs__type='text',
        input__tag='input',
        label__tag='label',
        non_editable_input__tag='span',
        template='iommi/form/row.html',
        errors__template='iommi/form/errors.html',
    ),
    Column=dict(
        shortcuts=dict(
            select=dict(
                header__attrs__title='Select all',
            ),
        )
    ),
    Paginator=dict(
        template='iommi/table/paginator.html',
    ),
    Query=dict(
        template='iommi/query/form.html',
    ),
    Actions=dict(
        tag='div',
        attrs__class__links=True,
    ),
    MenuItem=dict(
        a__tag='a',
        active_class='active',
    ),
    DebugMenu=dict(
        tag='nav',
        items_container__tag='ul',
        items_container__attrs__style={
            'list-style': 'none',
        },
        attrs__style={
            'position': 'fixed',
            'bottom': '-1px',
            'right': '-1px',
            'background': 'white',
            'border': '1px solid black',
            'z-index': '100',
        },
        attrs__class={
            'flex-column': False,
        },
    ),
)

font_awesome_4 = Style(
    Column__shortcuts=dict(
        icon__extra=dict(
            icon_attrs__class={'fa': True, 'fa-lg': True},
            icon_prefix='fa-',
        ),
        edit__extra__icon='pencil-square-o',
        delete__extra__icon='trash-o',
        download__extra__icon='download',
    ),
)

test = Style(
    base,
    font_awesome_4,
    Field=dict(
        shortcuts=dict(
        ),
    ),
    Table=dict(
        attrs__class__table=True,
    ),
    Column=dict(
        shortcuts__number__cell__attrs__class__rj=True,
    ),
    Paginator=dict(
        template='iommi/table/bootstrap/paginator.html',
    ),
    Menu=dict(
        tag='nav',
        items_container__tag='ul'
    ),
    MenuItem=dict(
        tag='li',
        a__attrs__class={'link': True},
    ),
)

_styles = {}


def register_style(name, conf):
    assert name not in _styles
    assert conf.name is None
    conf.name = name
    _styles[name] = conf


def get_style(name):
    return _styles[name]


_no_attribute_sentinel = object()


def apply_style_recursively(*, style_data, obj):
    if isinstance(obj, dict):
        result = Namespace(style_data, obj)
        obj.clear()
        obj.update(**result)
    else:
        for k, v in style_data.items():
            if isinstance(v, dict):
                apply_style_recursively(style_data=v, obj=getattr(obj, k))
            else:
                attrib = getattr(obj, k, _no_attribute_sentinel)
                if attrib is _no_attribute_sentinel:
                    raise InvalidStyleConfigurationException(f'Object {obj!r} has no attribute {k} which the style tried to set.')
                if attrib is None:
                    setattr(obj, k, v)


def get_style_obj_for_object(style, obj):
    return get_style(style).component(obj)


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
    for cls_name, classes in classes_by_name.items():
        for cls in classes:
            shortcuts_available_by_class_name[cls_name].update(get_shortcuts_by_name(cls).keys())

    invalid_class_names = []
    non_existent_shortcut_names = []
    for style_name, style in styles.items():
        for cls_name, config in style.config.items():
            # First validate the top level classes
            if cls_name not in classes_by_name:
                invalid_class_names.append((style_name, cls_name))
                continue

            # Then validate the shortcuts
            for shortcut_name in config.get('shortcuts', {}).keys():
                if shortcut_name not in shortcuts_available_by_class_name[cls_name]:
                    non_existent_shortcut_names.append((style_name, cls_name, shortcut_name))

    if invalid_class_names or non_existent_shortcut_names:
        invalid_class_names_str = '\n'.join(
            f'    Style: {style_name} - class: {cls_name}'
            for style_name, cls_name in invalid_class_names
        )
        if invalid_class_names_str:
            invalid_class_names_str = 'Invalid class names:\n' + invalid_class_names_str
        invalid_shortcut_names_str = '    \n'.join(
            f'    Style: {style_name} - class: {cls_name} - shortcut: {shortcut_name}'
            for style_name, cls_name, shortcut_name in non_existent_shortcut_names
        )
        if invalid_shortcut_names_str:
            invalid_shortcut_names_str = 'Invalid shortcut names:\n' + invalid_shortcut_names_str
        raise InvalidStyleConfigurationException('\n\n'.join([invalid_class_names_str, invalid_shortcut_names_str]))
