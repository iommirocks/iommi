from copy import copy
from typing import (
    Dict,
    Type,
)

from iommi.base import (
    items,
    keys,
)
from iommi.declarative.dispatch import dispatch
from iommi.declarative.namespace import (
    Namespace,
    setdefaults_path,
)
from iommi.refinable import (
    Prio,
    RefinableMembers,
)
from iommi.sort_after import sort_after
from iommi.struct import Struct
from iommi.traversable import (
    Traversable,
)

FORBIDDEN_NAMES = {x for x in dir(Traversable)} - {'context'}


class Members(Traversable):
    """
    Internal iommi class that holds members of another class, for example the columns of a `Table` instance.
    """

    @dispatch
    def __init__(self, *, _declared_members, unknown_types_fall_through, cls, **kwargs):
        super(Members, self).__init__(**kwargs)
        self._declared_members = _declared_members
        self._unknown_types_fall_through = unknown_types_fall_through
        self._cls = cls

    def on_bind(self):
        self._bound_members = MemberBinder(self, self._declared_members, self._unknown_types_fall_through)


def refine_done_members(
    container,
    *,
    name: str,
    members_from_namespace: Dict[str, Traversable] = None,
    members_from_declared: Dict[str, Traversable] = None,
    members_from_auto: Dict[str, Traversable] = None,
    cls: Type,
    members_cls: Type = Members,
    extra_member_defaults=None,
    unknown_types_fall_through=False,
):
    """
    This function is used to collect and merge data from the constructor
    argument, the declared members, and other config into one data structure.
    `bind_members` is then used at bind time to recursively bind the nested
    parts.

    Example:

    .. code-block:: python

        class ArtistTable(Table):
            instrument = Column()  # <- declared member

        MyTable(
            columns__name=Column(),  # <- constructor argument
            columns__instrument__after='name',  # <- inserted config for a declared member
        )

    In this example the resulting table will have two columns `instrument` and
    `name`, with `instrument` after name even though it was declared before.
    """
    forbidden_names = FORBIDDEN_NAMES & (
        set(keys(members_from_declared or {})) | set(keys(members_from_namespace or {}))
    )
    if forbidden_names:
        raise ForbiddenNamesException(
            f'The names {", ".join(sorted(forbidden_names))} are reserved by iommi, please pick other names'
        )

    assert isinstance(container.get_declared('refinable')[name], RefinableMembers)

    member_by_name = Struct()
    _unapplied_config = {}
    extra_member_defaults = extra_member_defaults or {}

    if members_from_auto is not None:
        member_by_name.update(members_from_auto)

    if members_from_declared is not None:
        for key, x in items(members_from_declared):
            assert (
                '__' not in key
            ), "Don't specify nested attrs using the field name. You lose the ability to include more config from other places. Pick another name and give the path as attr instead"
            x._name = key
            member_by_name[key] = x

    if members_from_namespace is not None:
        for key, item in items(members_from_namespace):
            if isinstance(item, Traversable):
                # noinspection PyProtectedMember
                assert not item._is_bound
                item._name = key
                member_by_name[key] = item
            elif isinstance(item, dict):
                if key in member_by_name:
                    _unapplied_config[key] = item
                else:
                    item = setdefaults_path(
                        Namespace(),
                        item,
                        extra_member_defaults.pop(key, {}),
                        call_target__cls=cls,
                        _name=key,
                    )
                    member_by_name[key] = item()
            else:
                assert (
                    unknown_types_fall_through or item is None
                ), f'I got {type(item)} when creating a {cls.__name__}.{key}, but I was expecting Traversable or dict'
                member_by_name[key] = item

    for k, v in items(Namespace(_unapplied_config)):
        member_by_name[k] = member_by_name[k].refine(Prio.member, **v)
        # noinspection PyProtectedMember
        assert member_by_name[k]._name is not None

    if extra_member_defaults:
        for k, v in items(Namespace(extra_member_defaults)):
            if k in member_by_name:
                v = Namespace(v)
                v.pop('call_target', None)
                member_by_name[k] = member_by_name[k].refine(Prio.member_defaults, **v)
            else:
                member_by_name[k] = Namespace(
                    v,
                    call_target__cls=cls,
                    _name=k,
                )()
            # noinspection PyProtectedMember
            assert member_by_name[k]._name is not None

    to_delete = {k for k, v in items(member_by_name) if v is None}

    for k in to_delete:
        del member_by_name[k]

    for key, item in items(member_by_name):
        if isinstance(item, Traversable) and not item.is_refine_done:
            member_by_name[key] = item.refine_done(parent=container)

    member_by_name = sort_after(member_by_name)
    container.iommi_namespace[name] = member_by_name

    m = members_cls(
        _name=name,
        _declared_members=member_by_name,
        cls=cls,
        unknown_types_fall_through=unknown_types_fall_through,
    )
    m = m.refine_done(parent=container)

    setattr(container, 'iommi_member_renderer_' + name, m)


# noinspection PyProtectedMember
def bind_members(container: Traversable, *, name: str, lazy=True) -> None:
    """
    This is the companion function to `collect_members`. It is used at bind
    time to recursively (and by default lazily(!)) bind the parts of a container.
    """
    assert container._is_bound
    m = getattr(container, 'iommi_member_renderer_' + name)
    m = m.bind(parent=container)
    setattr(container._bound_members, name, m)
    setattr(container, name, m._bound_members)
    if not lazy:
        _force_bind_all(m._bound_members)


def bind_member(container, *, name: str) -> None:
    bound_member = getattr(container, name).bind(parent=container)
    setattr(container, name, bound_member)
    if bound_member is not None:
        setattr(container._bound_members, name, bound_member)


class ForbiddenNamesException(Exception):
    pass


# noinspection PyCallByClass
class MemberBinder(dict):
    def __init__(self, parent: Members, _declared_members: Dict[str, Traversable], _unknown_types_fall_through: bool):
        if _unknown_types_fall_through:
            bindable_names = []
            for name, member in items(_declared_members):
                if not hasattr(member, 'bind'):
                    self[name] = copy(member)
                    continue
                bindable_names.append(name)
        else:
            bindable_names = list(keys(_declared_members))

        object.__setattr__(self, '_parent', parent)
        object.__setattr__(self, '_bindable_names', bindable_names)
        object.__setattr__(self, '_declared_members', _declared_members)
        super().__init__()

    def __getattribute__(self, name):
        _bindable_names = object.__getattribute__(self, '_bindable_names')
        if name in _bindable_names:
            return self[name]
        try:
            return object.__getattribute__(self, name)
        except AttributeError as e:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no member '{name}'.\n"
                f"Available members:\n    " + '\n    '.join(sorted(_bindable_names)) + '\n'
            ) from e

    def __setattr__(self, name, value):
        self[name] = value

    def __getitem__(self, name):
        _force_bind(self, name)
        return dict.__getitem__(self, name)

    def __delitem__(self, name):
        dict.__delitem__(self, name)
        _bindable_names = object.__getattribute__(self, '_bindable_names')
        _bindable_names.remove(name)

    def get(self, name, *args):
        _force_bind(self, name)
        return dict.get(self, name, *args)

    def values(self):
        _force_bind_all(self)
        return super().values()

    def items(self):
        _force_bind_all(self)
        return super().items()

    def keys(self):
        _force_bind_all(self)
        return super().keys()

    def __len__(self):
        _force_bind_all(self)
        return super().__len__()

    def __repr__(self):
        bound_members = list(dict.keys(self))
        members = [
            name + (' (bound)' if name in bound_members else '')
            for name in object.__getattribute__(self, '_declared_members')
        ]
        return f'<{self.__class__.__name__}: {", ".join(members)}>'


# noinspection PyCallByClass
def _force_bind(member_binder: MemberBinder, name: str):
    if name not in member_binder:
        _parent = object.__getattribute__(member_binder, '_parent')
        _bindable_names = object.__getattribute__(member_binder, '_bindable_names')
        _declared_members = object.__getattribute__(member_binder, '_declared_members')

        if name in _bindable_names:
            bound_member = _declared_members[name].bind(parent=_parent)
            if bound_member is not None:
                bound_members = dict.copy(member_binder)
                dict.clear(member_binder)  # re-insert values in dict to retain ordering
                dict.update(
                    member_binder,
                    (
                        (k, bound_member if k == name else bound_members[k])
                        for k in dict.keys(_declared_members)
                        if k == name or k in bound_members
                    ),
                )


# noinspection PyCallByClass
def _force_bind_all(member_binder: MemberBinder):
    _bindable_names = object.__getattribute__(member_binder, '_bindable_names')
    for name in _bindable_names:
        if name not in member_binder:
            _force_bind(member_binder, name)
