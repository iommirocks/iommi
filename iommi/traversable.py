import copy
import functools
from typing import (
    Any,
    Dict,
    List,
    Union,
)

from tri_declarative import (
    dispatch,
    getattr_path,
    Namespace,
    Refinable,
    refinable,
    RefinableObject,
)
from tri_struct import Struct

from iommi.attrs import evaluate_attrs
from iommi.base import (
    items,
    MISSING,
)
from iommi.evaluate import (
    evaluate_members,
    evaluate_strict,
    evaluate_strict_container,
)
from iommi.style import apply_style


class EvaluatedRefinable(Refinable):
    pass


def is_evaluated_refinable(x):
    return isinstance(x, EvaluatedRefinable) or getattr(x, '__iommi__evaluated', False)


class PathNotFoundException(Exception):
    pass


def reinvokable(f):
    @functools.wraps(f)
    def reinvokable_wrapper(self, *args, **kwargs):
        # We only need to save the params on the first level
        if not hasattr(self, '_iommi_saved_params'):
            self._iommi_saved_params = kwargs
        return f(self, *args, **kwargs)
    return reinvokable_wrapper


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
    context = None

    iommi_style: str = EvaluatedRefinable()

    _declared_members: Dict[str, 'Traversable']
    _bound_members: Dict[str, 'Traversable']

    @dispatch
    def __init__(self, _name=None, **kwargs):
        self._declared_members = Struct()
        self._bound_members = Struct()
        self._evaluate_parameters = None
        self._name = _name

        super(Traversable, self).__init__(**kwargs)

    def __repr__(self):
        n = f' {self._name}' if self._name is not None else ''
        b = ' (bound)' if self._is_bound else ''
        try:
            p = f" path:'{self.iommi_path}'" if self.iommi_parent() is not None else ""
        except PathNotFoundException:
            p = ' path:<no path>'
        c = ''
        if self._is_bound and hasattr(self, '_bound_members'):
            members = self._bound_members
            if members:
                c = f" members:{list(members.keys())!r}"

        return f'<{type(self).__module__}.{type(self).__name__}{n}{b}{p}{c}>'

    def iommi_name(self) -> str:
        return self._name

    def iommi_parent(self) -> "Traversable":
        return self._parent

    def iommi_root(self) -> 'Traversable':
        node = self
        while node.iommi_parent() is not None:
            node = node.iommi_parent()
        return node

    def iommi_bound_members(self) -> Dict[str, 'Traversable']:
        return self._bound_members if self._bound_members is not None else Struct()

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

    def reinvoke(self, additional_kwargs: Dict[str, Any]) -> "Traversable":
        assert hasattr(self, '_iommi_saved_params'), f'reinvoke() called on class with missing @reinvokable decorator: {self.__class__.__name__}'
        additional_kwargs_namespace = Namespace(additional_kwargs)
        kwargs = {}
        for name, saved_param in items(self._iommi_saved_params):
            try:
                new_param = getattr_path(additional_kwargs_namespace, name)
            except AttributeError:
                kwargs[name] = saved_param
            else:
                if hasattr(saved_param, 'reinvoke'):
                    assert isinstance(new_param, dict)
                    kwargs[name] = saved_param.reinvoke(new_param)
                else:
                    if isinstance(saved_param, Namespace):
                        kwargs[name] = Namespace(saved_param, new_param)
                    else:
                        kwargs[name] = new_param

        additional_kwargs_namespace.pop('call_target', None)

        kwargs = Namespace(additional_kwargs_namespace, kwargs)  # Also include those keys not already in the original

        result = type(self)(**kwargs)

        result._name = self._name
        __tri_declarative_shortcut_stack = getattr(self, '__tri_declarative_shortcut_stack', None)
        if __tri_declarative_shortcut_stack is not None:
            setattr(result, '__tri_declarative_shortcut_stack', __tri_declarative_shortcut_stack)

        return result

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
                **(parent.iommi_evaluate_parameters() if parent is not None else {}),
                **result.own_evaluate_parameters(),
            })
            if not bool(include):
                return None
        else:
            include = MISSING

        if include is not MISSING:
            result.include = True

        apply_style(result)

        # Styling has another chance of setting include to False
        if include is not MISSING and result.include is False:
            return None
        result.include = True  # include can be the falsy MISSING. Set it to False

        # We need to recalculate evaluate_parameters here to not get the
        # unbound stuff that was in the first round of this dict
        result._evaluate_parameters = {
            **(result.iommi_parent().iommi_evaluate_parameters() if result.iommi_parent() is not None else {}),
            **result.own_evaluate_parameters(),
        }
        if parent is None:
            result.iommi_evaluate_parameters()['request'] = request
        result.on_bind()

        # on_bind has a chance to hide itself
        if result.include is False:
            return None

        if hasattr(result, 'attrs'):
            result.attrs = evaluate_attrs(result, **result.iommi_evaluate_parameters())

        evaluated_attributes = [k for k, v in items(result.get_declared('refinable_members')) if is_evaluated_refinable(v)]
        evaluate_members(result, evaluated_attributes, **result.iommi_evaluate_parameters())

        if hasattr(result, 'extra_evaluated'):
            result.extra_evaluated = evaluate_strict_container(result.extra_evaluated or {}, **result.iommi_evaluate_parameters())

        return result

    def on_bind(self) -> None:
        pass

    def own_evaluate_parameters(self):
        return {}

    def iommi_evaluate_parameters(self):
        return self._evaluate_parameters

    def get_request(self):
        if self._parent is None:
            return self._request
        else:
            return self.iommi_root().get_request()

    def get_context(self):
        if self._parent is None:
            return self.context or {}
        else:
            return self.iommi_parent().get_context()


def declared_members(node: Traversable) -> Any:
    # noinspection PyProtectedMember
    return node._declared_members


def set_declared_member(node: Traversable, name: str, value: Union[Any, Dict[str, Traversable]]):
    root = node.iommi_root()
    if (
        hasattr(root, '_long_path_by_path')
        or hasattr(root, '_path_by_long_path')
    ):
        print("### A disturbance in the force... The namespace has been recalculated!")
        root._long_path_by_path = root._path_by_long_path = None
    # noinspection PyProtectedMember
    node._declared_members[name] = value


def get_long_path_by_path(node):
    root = node.iommi_root()
    long_path_by_path = getattr(root, '_long_path_by_path', None)
    if long_path_by_path is None:
        long_path_by_path = build_long_path_by_path(root)
        root._long_path_by_path = long_path_by_path
    return long_path_by_path


def get_path_by_long_path(node):
    root = node.iommi_root()
    path_by_long_path = getattr(root, '_path_by_long_path', None)
    if path_by_long_path is None:
        long_path_by_path = get_long_path_by_path(root)
        path_by_long_path = {v: k for k, v in items(long_path_by_path)}
        root._path_by_long_path = path_by_long_path
    return path_by_long_path


def build_long_path(node: Traversable) -> str:
    def _traverse(t: Traversable) -> List[str]:
        assert t.iommi_name() is not None
        if t.iommi_parent() is None:
            return []
        return _traverse(t.iommi_parent()) + [t.iommi_name()]

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

        for name, member in items(members):
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


def evaluated_refinable(f):
    f = refinable(f)
    f.__iommi__evaluated = True
    return f
