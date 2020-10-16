import functools
from typing import (
    Any,
    Dict,
)

from tri_declarative import (
    getattr_path,
    Namespace,
)

from iommi.base import items


def reinvokable(f):
    @functools.wraps(f)
    def reinvokable_wrapper(self, *args, **kwargs):
        # We only need to save the params on the first level
        if not hasattr(self, '_iommi_saved_params'):
            self._iommi_saved_params = kwargs
        return f(self, *args, **kwargs)
    return reinvokable_wrapper


def is_reinvokable(obj):
    return hasattr(obj, '_iommi_saved_params')


def reinvoke(obj: Any, additional_kwargs: Dict[str, Any]) -> Any:
    assert is_reinvokable(obj), f'reinvoke() called on object with missing @reinvokable constructor decorator: {obj!r}'
    additional_kwargs_namespace = Namespace(additional_kwargs)
    kwargs = {}
    for name, saved_param in items(obj._iommi_saved_params):
        try:
            new_param = getattr_path(additional_kwargs_namespace, name)
        except AttributeError:
            kwargs[name] = saved_param
        else:
            if is_reinvokable(saved_param):
                assert isinstance(new_param, dict)
                kwargs[name] = reinvoke(saved_param, new_param)
            else:
                if isinstance(saved_param, Namespace):
                    kwargs[name] = Namespace(saved_param, new_param)
                else:
                    kwargs[name] = new_param

    additional_kwargs_namespace.pop('call_target', None)

    kwargs = Namespace(additional_kwargs_namespace, kwargs)  # Also include those keys not already in the original

    result = type(obj)(**kwargs)

    result._name = obj._name
    __tri_declarative_shortcut_stack = getattr(obj, '__tri_declarative_shortcut_stack', None)
    if __tri_declarative_shortcut_stack is not None:
        setattr(result, '__tri_declarative_shortcut_stack', __tri_declarative_shortcut_stack)

    return result


def set_and_remember_for_reinvoke(obj, **kwargs):
    assert is_reinvokable(obj)
    for k, v in items(kwargs):
        setattr(obj, k, v)
        # noinspection PyProtectedMember
        obj._iommi_saved_params[k] = v
