from collections import defaultdict
from contextlib import contextmanager
from typing import (
    Any,
    Dict,
    List,
    Type,
)

from tri_declarative import (
    dispatch,
    EMPTY,
    flatten,
    get_shortcuts_by_name,
    getattr_path,
    Namespace,
    RefinableObject,
    setdefaults_path,
)

from iommi.base import (
    items,
    keys,
)
from iommi.reinvokable import (
    is_reinvokable,
    retain_special_cases,
)
from ._web_compat import settings

DEFAULT_STYLE = 'bootstrap'


def get_iommi_style_name(obj: Any) -> str:
    while obj is not None:
        if obj.iommi_style is not None:
            return obj.iommi_style
        obj = obj.iommi_parent()
    return getattr(settings, 'IOMMI_DEFAULT_STYLE', DEFAULT_STYLE)


def get_style_object(obj: Any) -> 'Style':
    # Step 1: build the stack
    stack = []
    o = obj
    while o is not None:
        if o.iommi_style is not None:
            stack.append(o.iommi_style)
            if isinstance(o.iommi_style, Style):
                break
        o = o.iommi_parent()

    # Step 2: resolve names in the stack
    stack.append(get_style(getattr(settings, 'IOMMI_DEFAULT_STYLE', DEFAULT_STYLE)))
    stack.reverse()

    if len(stack) == 1:
        return stack[0]

    def resolve(x, previous_style):
        if isinstance(x, Style):
            return x

        assert isinstance(x, str)

        if previous_style is None:
            return get_style(x)

        result = previous_style.resolve(x)
        if result is None:
            return get_style(x)

        assert isinstance(result, Style)
        return result

    resolved_stack = []
    for i, x in enumerate(stack):
        resolved_stack.append(resolve(x, resolved_stack[i - 1] if i else None))

    return resolved_stack[-1]


def apply_style(style_object: 'Style', obj: Any, is_root) -> Any:
    style_data = get_style_data_for_object(style_object, obj=obj, is_root=is_root)
    return apply_style_data(style_data, obj)


def apply_style_data(style_data: Namespace, obj: Any) -> Any:
    if not style_data:
        return obj
    if not is_reinvokable(obj):
        print(f'Missing out of {style_data} for {type(obj)}')
        return obj
    return reinvoke_new_defaults(obj, style_data)


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
        self, *bases, base_template=None, content_block=None, assets=None, root=None, internal=False, sub_styles=None, **kwargs
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

        if assets:
            from iommi.debug import iommi_debug_on

            if iommi_debug_on():
                print(
                    "Warning: The preferred way to add top level assets config to a Style is via the root argument. "
                    "I.e. assets__* becomes root__assets__*"
                )
            setdefaults_path(root, assets=assets)

        self.root = {k: v for k, v in items(Namespace(*(base.root for base in bases), root)) if v is not None}
        self.config = Namespace(*[x.config for x in bases], recursive_namespace(kwargs))
        self.sub_styles = {
            k: Style(self, **v)
            for k, v in items(sub_styles)
        }

    def component(self, obj, is_root=False):
        """
        Calculate the namespace of additional argument that should be applied
        to the given object. If is_root is set to True, assets might also be
        added to the namespace.
        """
        result = Namespace()

        # TODO: is this wrong? Should it take classes first, then loop through shortcuts?
        for class_name in class_names_for(type(obj)):
            if class_name in self.config:
                config = Namespace(self.config.get(class_name, {}))
                shortcuts_config = Namespace(config.pop('shortcuts', {}))
                result.update(config)

                for shortcut_name in reversed(getattr(obj, '__tri_declarative_shortcut_stack', [])):
                    result = Namespace(result, shortcuts_config.get(shortcut_name, {}))

        if is_root:
            result = Namespace(result, self.root)

        return result

    def __repr__(self):
        return f'<Style: {self.name}>'

    def resolve(self, sub_style_name):
        result = self.sub_styles.get(sub_style_name)
        if result:
            return result

        for base in self.bases:
            result = base.resolve(sub_style_name)
            if result:
                return result

        return None


_styles = {}


def register_style(name, conf):
    assert name not in _styles, f'{name} is already registered'
    assert conf.name is None
    conf.name = name
    _styles[name] = conf

    @contextmanager
    def _unregister():
        try:
            yield
        finally:
            unregister_style(name)
    return _unregister()


def unregister_style(name):
    assert name in _styles
    del _styles[name]


def get_style(name):
    if isinstance(name, Style):
        return name
    try:
        return _styles[name]
    except KeyError:
        style_names = "\n    ".join(_styles.keys())
        raise Exception(
            f'''No registered style {name}. Register a style with register_style().

Available styles:
    {style_names}'''
        ) from None


def reinvoke_new_defaults(obj: Any, additional_kwargs: Dict[str, Any]) -> Any:
    assert is_reinvokable(obj), (
        f'reinvoke_new_defaults() called on object with ' f'missing @reinvokable constructor decorator: {obj!r}'
    )
    additional_kwargs_namespace = Namespace(additional_kwargs)

    kwargs = Namespace(additional_kwargs_namespace)
    for name, saved_param in items(obj._iommi_saved_params):
        try:
            new_param = getattr_path(additional_kwargs_namespace, name)
        except AttributeError:
            kwargs[name] = saved_param
        else:
            if is_reinvokable(saved_param):
                assert isinstance(new_param, dict)
                kwargs[name] = reinvoke_new_defaults(saved_param, new_param)
            else:
                if isinstance(saved_param, Namespace):
                    kwargs[name] = Namespace(new_param, saved_param)
                else:
                    kwargs[name] = saved_param

    try:
        call_target = kwargs.pop('call_target', None)
        if call_target is not None:
            kwargs['call_target'] = Namespace(call_target, cls=type(obj))
        else:
            kwargs['call_target'] = type(obj)

        result = kwargs()
    except TypeError as e:
        raise InvalidStyleConfigurationException(
            f'Object {obj!r} could not be updated with style configuration {flatten(additional_kwargs_namespace)}'
        ) from e

    retain_special_cases(obj, result)
    return result


def get_style_data_for_object(style_object, obj, is_root):
    return style_object.component(obj, is_root)


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
