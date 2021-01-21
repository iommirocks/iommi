from iommi.base import items

def is_reinvokable(obj):
    return hasattr(obj, '_iommi_saved_params')


def retain_special_cases(obj, result):
    special_cases = [
        '_name',
        '__tri_declarative_shortcut_stack',
        '_instantiated_at_frame'
    ]
    for special_case in special_cases:
        value = getattr(obj, special_case, None)
        if value is not None:
            setattr(result, special_case, value)


def set_and_remember_for_reinvoke(obj, **kwargs):
    # assert is_reinvokable(obj)
    for k, v in items(kwargs):
        setattr(obj, k, v)
        # noinspection PyProtectedMember
        # obj._iommi_saved_params[k] = v
