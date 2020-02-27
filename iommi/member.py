from copy import copy
from typing import (
    Any,
    Dict,
    Type,
)

from tri_declarative import (
    dispatch,
    Namespace,
    setdefaults_path,
)
from tri_struct import Struct

from iommi.traversable import (
    Traversable,
    set_declared_member,
    declared_members,
)
from iommi.sort_after import sort_after

FORBIDDEN_NAMES = {x for x in dir(Traversable)}


class ForbiddenNamesException(Exception):
    pass


def collect_members(parent, *, name: str, items_dict: Dict = None, items: Dict[str, Any] = None, cls: Type, unknown_types_fall_through=False):
    forbidden_names = FORBIDDEN_NAMES & (set((items_dict or {}).keys()) | set((items or {}).keys()))
    if forbidden_names:
        raise ForbiddenNamesException(f'The names {", ".join(sorted(forbidden_names))} are reserved by iommi, please pick other names')

    assert name != 'items'
    unbound_items = Struct()
    _unapplied_config = {}

    if items_dict is not None:
        for key, x in items_dict.items():
            x._name = key
            unbound_items[key] = x

    if items is not None:
        for key, item in items.items():
            if isinstance(item, Traversable):
                assert not item._is_bound
                item._name = key
                unbound_items[key] = item
            elif isinstance(item, dict):
                if key in unbound_items:
                    _unapplied_config[key] = item
                else:
                    item = setdefaults_path(
                        Namespace(),
                        item,
                        call_target__cls=cls,
                        _name=key,
                    )
                    unbound_items[key] = item()
            else:
                assert unknown_types_fall_through, f'I got {type(item)}, but I was expecting Traversable or dict'
                unbound_items[key] = item

    if _unapplied_config:
        parent._unapplied_config[name] = _unapplied_config

    set_declared_member(parent, name, unbound_items)


class Members(Traversable):
    """
    Internal iommi class that holds members of another class, for example the columns of a `Table` instance.
    """

    @dispatch
    def __init__(self, *, _declared_members, unknown_types_fall_through, **kwargs):
        super(Members, self).__init__(**kwargs)
        self._declared_members = _declared_members
        self._bound_members = Struct()
        self._unknown_types_fall_through = unknown_types_fall_through

    def on_bind(self) -> None:
        for key, member in self._declared_members.items():
            if self._unknown_types_fall_through and not hasattr(member, 'bind'):
                self._bound_members[key] = copy(member)
                continue

            bound_member = member.bind(parent=self)
            if bound_member is not None:
                self._bound_members[key] = bound_member

        sort_after(self._bound_members)


def bind_members(parent: Traversable, *, name: str, cls=Members, unknown_types_fall_through=False) -> None:
    m = cls(
        _name=name,
        _declared_members=declared_members(parent)[name],
        unknown_types_fall_through=unknown_types_fall_through,
    )
    # It's useful to be able to access these during bind
    setattr(parent, name, m._bound_members)
    setattr(parent._bound_members, name, m)
    m = m.bind(parent=parent)
    # ...and now we have the real object
    setattr(parent, name, m._bound_members)
    setattr(parent._bound_members, name, m)
