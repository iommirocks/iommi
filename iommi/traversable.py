import copy
from typing import (
    Any,
    Dict,
    List,
)

from iommi.attrs import evaluate_attrs
from iommi.base import (
    items,
    NOT_BOUND_MESSAGE,
)
from iommi.declarative.namespace import Namespace
from iommi.evaluate import (
    evaluate_members,
    evaluate_strict,
    evaluate_strict_container,
    get_callable_description,
    get_signature,
    matches,
    signature_from_kwargs,
)
from iommi.refinable import (
    evaluated_refinable,
    EvaluatedRefinable,
    is_evaluated_refinable,
    Prio,
    Refinable,
    RefinableMembers,
    RefinableObject,
)
from iommi.struct import Struct
from iommi.style import Style

# Backward compatible definition
EvaluatedRefinable = EvaluatedRefinable  # pragma: no mutate this is just marking the symbols as used
evaluated_refinable = evaluated_refinable  # pragma: no mutate this is just marking the symbols as used


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
    context = None

    iommi_style: str = Refinable()
    assets = RefinableMembers()
    endpoints = RefinableMembers()

    _bound_members: Dict[str, 'Traversable']

    def __init__(self, _name=None, **kwargs):
        self._bound_members = None
        self._evaluate_parameters = None
        self._name = _name

        super().__init__(**kwargs)

    def __repr__(self):
        n = f'{self._name}' if self._name is not None else ''
        b = '(bound)' if self._is_bound else ''
        try:
            p = f"path:'{self.iommi_path}'" if self.iommi_parent() is not None else ''
        except PathNotFoundException:
            p = 'path:<no path>'
        c = ''
        if self._is_bound:
            if self._bound_members:
                c = f'members:{list(self._bound_members.keys())!r}'

        description = (' ' + ' '.join(x for x in ('', n, b, p, c) if x)).rstrip()
        return f'<{type(self).__module__}.{type(self).__name__}{description}>'

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
        assert self._is_bound, "Not bound yet"
        return self._bound_members

    @property
    def iommi_path(self) -> str:
        if hasattr(self, '_iommi_path_override'):
            return self._iommi_path_override

        if hasattr(self, '_iommi_path_cache'):
            return self._iommi_path_cache

        long_path = build_long_path(self)
        path_by_long_path = get_path_by_long_path(self)
        path = path_by_long_path.get(long_path)
        if path is None:
            candidates = '\n'.join(path_by_long_path.keys())
            raise PathNotFoundException(
                f"Path not found(!) (Searched for '{long_path}' among the following:\n{candidates}"
            )
        return path

    @property
    def iommi_dunder_path(self) -> str:
        assert self._is_bound, NOT_BOUND_MESSAGE
        return build_long_path(self).replace('/', '__')

    def apply_style(self, iommi_style: Style, is_root=True):
        assert iommi_style.__class__.__name__ == "Style", iommi_style.__class__.__name__

        refinements = iommi_style.resolve(obj=self, is_root=is_root)

        result = self
        del self

        if refinements:
            for refinement in refinements:
                result = result.refine(Prio.style, **Namespace(refinement))
        else:
            result = result.refine(Prio.style)

        result.iommi_style = iommi_style
        return result

    def bind(self, *, parent=None, request=None):
        assert parent is None or parent._is_bound
        assert not self._is_bound

        result = copy.copy(self)

        is_root = parent is None

        if not result.is_refine_done:
            result = result.refine_done(parent=parent)

        # todo drop _declared
        result._declared = self
        del self  # to prevent mistakes when changing the code below

        if is_root:
            result._request = request
            if result._name is None:
                result._name = 'root'
            result._iommi_collected_assets = {}

        result._parent = parent
        result._bound_members = Struct()
        result._is_bound = True

        evaluate_parameters = {
            **(parent.iommi_evaluate_parameters() if parent is not None else {}),
            **result.own_evaluate_parameters(),
            'traversable': result,
        }
        if parent is None:
            evaluate_parameters['request'] = request
            if hasattr(request, 'iommi_view_params'):
                evaluate_parameters['params'] = request.iommi_view_params
        result._evaluate_parameters = evaluate_parameters

        if hasattr(result, 'include'):
            include = evaluate_strict(result.include, **evaluate_parameters)
            if not bool(include):
                return None

        result.include = True

        result.on_bind()

        # on_bind has a chance to hide itself
        if result.include is False:
            return None

        if hasattr(result, 'attrs'):
            result.attrs = evaluate_attrs(result, **result.iommi_evaluate_parameters())

        evaluated_attributes = [k for k, v in items(result.get_declared('refinable')) if is_evaluated_refinable(v)]
        evaluate_members(result, evaluated_attributes, **evaluate_parameters)

        if hasattr(result, 'extra_evaluated'):
            result.extra_evaluated = evaluate_strict_container(result.extra_evaluated or {}, **evaluate_parameters)

        return result

    def on_bind(self) -> None:
        pass

    def own_evaluate_parameters(self):
        return {}

    def iommi_evaluate_parameters(self):
        return self._evaluate_parameters

    def invoke_callback(self, callback, **kwargs):
        try:
            return callback(**kwargs, **self.iommi_evaluate_parameters())
        except TypeError as e:
            if not matches(
                signature_from_kwargs(dict(**kwargs, **self.iommi_evaluate_parameters())),
                get_signature(callback),
                __match_empty=True,
            ):
                raise TypeError(
                    f'TypeError when invoking callback {get_callable_description(callback)}.\n'
                    f'(Keyword arguments: {", ".join(sorted([*kwargs, *self.iommi_evaluate_parameters()]))})'
                ) from e
            raise

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
    assert node.is_refine_done, "Trying to find declared_member on RefinableObject without doing refine_done() first"
    result = Namespace()
    for k, v in items(node.get_declared('refinable')):
        if isinstance(v, RefinableMembers):
            result[k] = node.iommi_namespace.get(k, Namespace())
        else:
            child = getattr(node, k)
            if isinstance(child, RefinableObject):
                assert (
                    child.is_refine_done
                ), f"refine_done() not invoked on something ({k}) in the declared namespace of {node._name}"
                result[k] = child
    if hasattr(node, '_declared_members'):
        result.update(node._declared_members)

    return result


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
            if short_path is None:
                less_short_path = find_unique_suffix(long_path_segments)
                assert less_short_path is not None, (
                    f"Ran out of names...\n"
                    f"Any suitable short name for {'/'.join(long_path_segments)} already taken.\n\n"
                    f"Result so far:\n" + '\n'.join(f'{k}   ->   {v}' for k, v in result.items())
                )
                short_path = less_short_path
            result[short_path] = long_path

            node._iommi_path_cache = short_path

        if isinstance(node, RefinableObject):
            members = declared_members(node)
        elif isinstance(node, dict):
            members = node
            assert '_declared_members' not in members
        else:
            return

        for name, member in sorted(items(members), key=lambda item: item[0] == 'endpoints'):
            assert name != '_declared_members'
            if member:
                _traverse(
                    member,
                    long_path_segments=long_path_segments + [name],
                    short_path_candidate_segments=short_path_candidate_segments
                    + ([name] if include_in_short_path(member) else []),
                )

    _traverse(root, [], [])

    return result
