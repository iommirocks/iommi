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

    kwargs = Namespace(additional_kwargs_namespace, kwargs)  # Also include those keys not already in the original

    call_target = kwargs.pop('call_target', None)
    if call_target is not None:
        kwargs['call_target'] = Namespace(
            call_target,
            cls=type(obj),
        )
    else:
        kwargs['call_target'] = type(obj)

    result = kwargs()

    retain_special_cases(obj, result)
    return result


def retain_special_cases(obj, result):
    special_cases = ['_name', '__tri_declarative_shortcut_stack', '_instantiated_at_frame']
    for special_case in special_cases:
        value = getattr(obj, special_case, None)
        if value is not None:
            setattr(result, special_case, value)


def set_and_remember_for_reinvoke(obj, **kwargs):
    assert is_reinvokable(obj)
    for k, v in items(kwargs):
        setattr(obj, k, v)
        # noinspection PyProtectedMember
        obj._iommi_saved_params[k] = v
