import copy
from typing import (
    Any,
    Dict,
    List,
    Union,
)

from tri_declarative import (
    dispatch,
    evaluate,
    evaluate_strict,
    Namespace,
    Refinable,
    RefinableObject,
)
from tri_struct import Struct

from iommi.attrs import evaluate_attrs
from iommi.base import MISSING
from iommi.style import apply_style


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

    _declared_members: Dict[str, 'Traversable']
    _bound_members: Dict[str, 'Traversable']

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
        except PathNotFoundException:
            p = ' path:<no path>'
        c = ''
        if self._is_bound and hasattr(self, '_bound_members'):
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

        result = copy.copy(self)
        result._declared = self

        del self  # to prevent mistakes when changing the code below

        result._parent = parent
        result._is_bound = True

        if hasattr(result, 'include'):
            include = evaluate_strict(result.include, **{
                **(parent._evaluate_parameters if parent is not None else {}),
                **result.own_evaluate_parameters(),
            })
            if include is False:
                return None
        else:
            include = MISSING

        if include is not MISSING:
            result.include = True

        apply_style(result)

        from iommi.member import Members
        if parent is not None:
            _unapplied_config = parent._unapplied_config.get(result._name, {})
            for k, v in _unapplied_config.items():
                if k == 'call_target':
                    continue
                if k in declared_members(result):
                    result._unapplied_config[k] = v
                    continue
                # The Members class applies config itself, so this is for the rest of them
                if not isinstance(result, Members):
                    if hasattr(result, k):
                        setattr(result, k, v)
                        continue
                    raise ValueError(f'Unable to set {k} on {result._name}')

        # Unapplied config and styling has another chance of setting include to False
        if include is not MISSING and result.include is False:
            return None
        result.include = True  # include can be the falsy MISSING. Set it to False

        # We neeed to recalculate evaluate_parameters here to not get the
        # unbound stuff that was in the first round of this dict
        result._evaluate_parameters = {
            **(get_parent(result)._evaluate_parameters if result._parent is not None else {}),
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


def declared_members(node: Traversable) -> Any:
    # noinspection PyProtectedMember
    return node._declared_members


def set_declared_member(node: Traversable, name: str, value: Union[Any, Dict[str, Traversable]]):
    # noinspection PyProtectedMember
    node._declared_members[name] = value


def get_parent(node: Traversable) -> Traversable:
    # noinspection PyProtectedMember
    return node._parent


def get_name(node: Traversable) -> str:
    # noinspection PyProtectedMember
    return node._name


def bound_members(node: Traversable) -> Dict[str, Traversable]:
    # noinspection PyProtectedMember
    return node._bound_members if node._bound_members else {}


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
    while get_parent(node) is not None:
        node = get_parent(node)
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
    def _traverse(t: Traversable) -> List[str]:
        assert get_name(t) is not None
        if get_parent(t) is None:
            return []
        return _traverse(get_parent(t)) + [get_name(t)]

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
            members = declared_members(node)
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
