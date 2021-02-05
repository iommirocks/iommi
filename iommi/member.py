from copy import (
    copy,
)
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

from iommi.base import (
    items,
    keys,
)
from iommi.reinvokable import reinvoke
from iommi.sort_after import sort_after
from iommi.traversable import (
    declared_members,
    set_declared_member,
    Traversable,
)

FORBIDDEN_NAMES = {x for x in dir(Traversable)} - {'context'}

# Need to use this in collect_members that has a local variable called items
items_of = items


def collect_members(
    container,
    *,
    name: str,
    items_dict: Dict = None,
    items: Dict[str, Any] = None,
    cls: Type,
    unknown_types_fall_through=False,
):
    """
    This function is used to collect and merge data from the constructor
    argument, the declared members, and other config into one data structure.
    `bind_members` is then used at bind time to recursively bind the nested
    parts.

    Example:

    .. code:: python

        class ArtistTable(Table):
            instrument = Column()  # <- declared member

        MyTable(
            columns__name=Column(),  # <- constructor argument
            columns__instrument__after='name',  # <- inserted config for a declared member
        )

    In this example the resulting table will have two columns `instrument` and
    `name`, with `instrument` after name even though it was declared before.
    """
    forbidden_names = FORBIDDEN_NAMES & (set(keys(items_dict or {})) | set(keys(items or {})))
    if forbidden_names:
        raise ForbiddenNamesException(
            f'The names {", ".join(sorted(forbidden_names))} are reserved by iommi, please pick other names'
        )

    assert name != 'items'
    unbound_items = Struct()
    _unapplied_config = {}

    if items_dict is not None:
        for key, x in items_of(items_dict):
            x._name = key
            unbound_items[key] = x

    if items is not None:
        for key, item in items_of(items):
            if isinstance(item, Traversable):
                # noinspection PyProtectedMember
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
                assert (
                    unknown_types_fall_through or item is None
                ), f'I got {type(item)} when creating a {cls.__name__}.{key}, but I was expecting Traversable or dict'
                unbound_items[key] = item

    for k, v in items_of(Namespace(_unapplied_config)):
        unbound_items[k] = reinvoke(unbound_items[k], v)
        # noinspection PyProtectedMember
        assert unbound_items[k]._name is not None

    to_delete = {k for k, v in items_of(unbound_items) if v is None}

    for k in to_delete:
        del unbound_items[k]

    sort_after(unbound_items)

    set_declared_member(container, name, unbound_items)
    setattr(container, name, NotBoundYet(container, name))


class Members(Traversable):
    """
    Internal iommi class that holds members of another class, for example the columns of a `Table` instance.
    """

    @dispatch
    def __init__(self, *, _declared_members, unknown_types_fall_through, **kwargs):
        super(Members, self).__init__(**kwargs)
        self._declared_members = _declared_members
        self._unknown_types_fall_through = unknown_types_fall_through

    def on_bind(self):
        self._bound_members = MemberBinder(self, self._declared_members, self._unknown_types_fall_through)


# noinspection PyProtectedMember
def bind_members(parent: Traversable, *, name: str, cls=Members, unknown_types_fall_through=False, lazy=True) -> None:
    """
    This is the companion function to `collect_members`. It is used at bind
    time to recursively (and by default lazily(!)) bind the parts of a container.
    """
    m = cls(
        _name=name,
        _declared_members=declared_members(parent)[name],
        unknown_types_fall_through=unknown_types_fall_through,
    )
    assert parent._is_bound
    m = m.bind(parent=parent)
    setattr(parent._bound_members, name, m)
    setattr(parent, name, m._bound_members)
    if not lazy:
        _force_bind_all(m._bound_members)


class ForbiddenNamesException(Exception):
    pass


class NotBoundYetException(Exception):
    pass


class NotBoundYet:
    """
    This class is used to make debugging easier. Before the members are bound,
    this class is used as a sentinel so you get some feedback on where you
    should be looking instead. Without this class I was constantly confused why
    stuff was empty and spent lots of time trying to figure that out.
    """

    def __init__(self, parent, name):
        self.parent = parent
        self.name = name

    def __repr__(self):
        return f"{self.name} of {type(self.parent).__name__} is not bound, look in _declared_members[{self.name}] for the declared copy of this, or bind first"

    def __str__(self):
        raise NotBoundYetException(repr(self))

    def __iter__(self):
        raise NotBoundYetException(repr(self))

    def values(self):
        raise NotBoundYetException(repr(self))

    def keys(self):
        raise NotBoundYetException(repr(self))

    def items(self):
        raise NotBoundYetException(repr(self))


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
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        self[name] = value

    def __getitem__(self, name):
        _force_bind(self, name)
        return dict.__getitem__(self, name)

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
