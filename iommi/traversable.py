import copy
from collections import defaultdict
from typing import (
    List,
    Dict,
)

from tri_declarative import (
    get_callable_description,
    LAST,
    Namespace,
    evaluate_strict,
    Refinable,
    RefinableObject,
    dispatch,
    evaluate,
)
from tri_struct import Struct

from iommi.attrs import (
    evaluate_attrs,
)
from iommi.style import apply_style


def no_copy_on_bind(cls):
    cls._no_copy_on_bind = True
    return cls


class EvaluatedRefinable(Refinable):
    pass


def is_evaluated_refinable(x):
    return isinstance(x, EvaluatedRefinable) or getattr(x, '__iommi__evaluated', False)


class PathNotFoundException(Exception):
    pass


class Traversable(RefinableObject):
    """
    Abstract API for objects that have a place in the iommi path structure.
    You should not need to care about this class as it is an implementation
    detail.
    """

    _name = None
    _parent = None
    _is_bound = False
    _request = None

    iommi_style: str = EvaluatedRefinable()

    @dispatch
    def __init__(self, _name=None, **kwargs):
        self._declared_members = Struct()
        self._unapplied_config = Struct()
        self._bound_members = Struct()
        self._evaluate_parameters = None
        self._name = _name

        super(Traversable, self).__init__(**kwargs)

    def __repr__(self):
        n = f' {self._name}' if self._name is not None else ''
        b = ' (bound)' if self._is_bound else ''
        try:
            p = f" path:'{self.iommi_path}'" if self._parent is not None else ""
        except AssertionError:
            p = ' path:<no path>'
        c = ''
        if self._is_bound:
            members = self._bound_members
            if members:
                c = f" members:{list(members.keys())!r}"

        return f'<{type(self).__module__}.{type(self).__name__}{n}{b}{p}{c}>'

    @property
    def iommi_path(self) -> str:
        long_path = build_long_path(self)
        path_by_long_path = get_path_by_long_path(self)
        path = path_by_long_path.get(long_path)
        if path is None:
            candidates = '\n'.join(path_by_long_path.keys())
            raise PathNotFoundException(f"Path not found(!) (Searched for {long_path} among the following:\n{candidates}")
        return path

    @property
    def iommi_dunder_path(self) -> str:
        assert self._is_bound
        return build_long_path(self).replace('/', '__')

    def bind(self, *, parent=None, request=None):
        assert parent is None or parent._is_bound
        assert not self._is_bound

        if parent is None:
            self._request = request
            if self._name is None:
                self._name = 'root'

        if hasattr(self, '_no_copy_on_bind'):
            result = self
        else:
            result = copy.copy(self)
            result._declared = self

        del self  # to prevent mistakes when changing the code below

        result._parent = parent
        result._is_bound = True

        apply_style(result)

        if parent is not None:
            _unapplied_config = parent._unapplied_config.get(result._name, {})
            for k, v in _unapplied_config.items():
                if k in result._declared_members:
                    result._unapplied_config[k] = v
                    continue
                # The Members class applies config itself, so this is for the rest of them
                from iommi.base import Members
                if not isinstance(result, Members) and hasattr(result, k):
                    setattr(result, k, v)
                    continue
                print(f'Unable to set {k} on {result._name}')

        result._evaluate_parameters = {
            **(result._parent._evaluate_parameters if result._parent is not None else {}),
            **result.own_evaluate_parameters(),
        }
        result.on_bind()

        if hasattr(result, 'attrs'):
            result.attrs = evaluate_attrs(result, **result._evaluate_parameters)

        evaluated_attributes = [k for k, v in result.get_declared('refinable_members').items() if is_evaluated_refinable(v)]
        evaluate_members(result, evaluated_attributes, **result._evaluate_parameters)

        if hasattr(result, 'extra_evaluated'):
            result.extra_evaluated = evaluate_strict_container(result.extra_evaluated or {}, **result._evaluate_parameters)

        return result

    def on_bind(self) -> None:
        pass

    def own_evaluate_parameters(self):
        return {}

    def get_request(self):
        if self._parent is None:
            return self._request
        else:
            return self._parent.get_request()


def evaluate_members(obj, keys, **kwargs):
    for key in keys:
        evaluate_member(obj, key, **kwargs)


def evaluate_member(obj, key, strict=True, **kwargs):
    value = getattr(obj, key)
    new_value = evaluate(value, __strict=strict, **kwargs)
    if new_value is not value:
        setattr(obj, key, new_value)


def evaluate_strict_container(c, **kwargs):
    return Namespace(
        {
            k: evaluate_strict(v, **kwargs)
            for k, v in c.items()
        }
    )


def get_root(node: Traversable) -> Traversable:
    while node._parent is not None:
        node = node._parent
    return node


def get_long_path_by_path(node):
    root = get_root(node)
    long_path_by_path = getattr(root, '_long_path_by_path', None)
    if long_path_by_path is None:
        long_path_by_path = build_long_path_by_path(root)
        root._long_path_by_path = long_path_by_path
    return long_path_by_path


def get_path_by_long_path(node):
    root = get_root(node)
    path_by_long_path = getattr(root, '_path_by_long_path', None)
    if path_by_long_path is None:
        long_path_by_path = get_long_path_by_path(root)
        path_by_long_path = {v: k for k, v in long_path_by_path.items()}
        root._path_by_long_path = path_by_long_path
    return path_by_long_path


def build_long_path(node: Traversable) -> str:
    def _traverse(node: Traversable) -> List[str]:
        # noinspection PyProtectedMember
        assert node._name is not None
        if node._parent is None:
            return []
        return _traverse(node._parent) + [node._name]

    return '/'.join(_traverse(node))


def include_in_short_path(node):
    return getattr(node, '_name', None) is not None


def build_long_path_by_path(root) -> Dict[str, str]:
    result = dict()

    def _traverse(node, long_path_segments, short_path_candidate_segments):
        if include_in_short_path(node):
            def find_unique_suffix(parts):
                for i in range(len(parts), -1, -1):
                    candidate = '/'.join(parts[i:])
                    if candidate not in result:
                        return candidate

            long_path = '/'.join(long_path_segments)
            short_path = find_unique_suffix(short_path_candidate_segments)
            if short_path is not None:
                result[short_path] = long_path
            else:
                less_short_path = find_unique_suffix(long_path_segments)
                if less_short_path is not None:
                    result[less_short_path] = long_path
                else:
                    so_far = '\n'.join(f'{k}   ->   {v}' for k, v in result.items())
                    assert False, f"Ran out of names... Any suitable short name for {'/'.join(long_path_segments)} already taken.\n\nResult so far:\n{so_far}"

        if hasattr(node, '_declared_members'):
            members = node._declared_members
        elif isinstance(node, dict):
            members = node
        else:
            return

        for name, member in members.items():
            if member:
                _traverse(
                    member,
                    long_path_segments=long_path_segments + [name],
                    short_path_candidate_segments=short_path_candidate_segments + (
                        [name]
                        if include_in_short_path(member)
                        else []
                    )
                )

    _traverse(root, [], [])

    return result


def should_include(item):
    if callable(item.include):
        assert False, "`include` was a callable. You probably forgot to evaluate it. The callable was: {}".format(get_callable_description(item.include))

    return item.include


def sort_after(d):
    unmoved = []
    to_be_moved_by_index = []
    to_be_moved_by_name = defaultdict(list)
    to_be_moved_last = []
    for x in d.items():
        after = getattr(x[1], 'after', None)
        if after is None:
            unmoved.append(x)
        elif after is LAST:
            to_be_moved_last.append(x)
        elif isinstance(after, int):
            to_be_moved_by_index.append(x)
        else:
            to_be_moved_by_name[x[1].after].append(x)

    if len(unmoved) == len(d):
        return d

    to_be_moved_by_index = sorted(to_be_moved_by_index, key=lambda x: x[1].after)  # pragma: no mutate (infinite loop when x.after changed to None, but if changed to a number manually it exposed a missing test)

    def place(x):
        yield x
        for y in to_be_moved_by_name.pop(x[0], []):
            yield from place(y)

    def traverse():
        count = 0
        while unmoved or to_be_moved_by_index:
            while to_be_moved_by_index:
                next_to_be_moved_by_index = to_be_moved_by_index[0]

                next_by_position_index = next_to_be_moved_by_index[1].after
                if count < next_by_position_index:  # pragma: no mutate (infinite loop when mutating < to <=)
                    break  # pragma: no mutate (infinite loop when mutated to continue)

                for x in place(next_to_be_moved_by_index):
                    yield x
                    count += 1  # pragma: no mutate

                to_be_moved_by_index.pop(0)

            if unmoved:
                next_unmoved_and_its_children = place(unmoved.pop(0))
                for x in next_unmoved_and_its_children:
                    yield x
                    count += 1  # pragma: no mutate

        for x in to_be_moved_last:
            yield from place(x)

    result = list(traverse())

    if to_be_moved_by_name:
        available_names = "\n    ".join(sorted(list(d.keys())))
        raise KeyError(f'Tried to order after {", ".join(sorted(to_be_moved_by_name.keys()))} '
                       f'but {"that key does" if len(to_be_moved_by_name) == 1 else "those keys do"} '
                       f'not exist.\nAvailable names:\n    {available_names}')

    d.clear()
    d.update(dict(result))
    return d


