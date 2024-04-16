class Struct(dict):
    """
    Struct is a dict that can be accessed like an object. It also has a predictable repr so it can be used in tests for example.

    .. code-block:: python

        >>> bs = Struct(a=1, b=2, c=3)
        >>> bs
        Struct(a=1, b=2, c=3)
        >>> bs.a
        1

    * Struct(**kwargs) -> new Struct initialized with the name=value pairs in the keyword aasdrgument list. For example: Struct(one=1, two=2)
    * Struct() -> new empty Struct
    * Struct(mapping) -> new Struct initialized from a mapping object's (key, value) pairs
    * Struct(iterable) -> new Struct initialized as if via:
        .. code-block:: python

            s = Struct()
            for k, v in iterable:
                s[k] = v

    """

    __slots__ = ()

    def __repr__(self):
        pieces = (
            "{}={}".format(key, (repr(val) if val is not self else "{}(...)".format(type(self).__name__)))
            for (key, val) in sorted(self.items())
        )
        return "{}({})".format(type(self).__name__, ", ".join(pieces))

    __str__ = __repr__

    def __getattribute__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            pass
        try:
            return object.__getattribute__(self, item)
        except AttributeError as e:
            try:
                missing_ = object.__getattribute__(self, '__missing__')
            except AttributeError:
                pass
            else:
                return missing_.__get__(self)(item)
            raise e

    __setattr__ = dict.__setitem__

    def __delattr__(self, item):
        try:
            del self[item]
        except KeyError:
            object.__delattr__(self, item)

    def copy(self):
        return type(self)(self)


class Frozen:
    """
    Mixin to create an immutable class.
    """

    __slots__ = ()

    def __hash__(self):
        hash_key = '_hash'
        try:
            _hash = dict.__getattribute__(self, hash_key)
        except AttributeError:
            _hash = hash(tuple((k, self[k]) for k in sorted(self.keys())))
            dict.__setattr__(self, hash_key, _hash)
        return _hash

    def __setitem__(self, *_, **__):
        raise TypeError(f"'{type(self).__name__}' object attributes are read-only")

    def __setattr__(self, key, value):
        raise TypeError(f"'{type(self).__name__}' object attributes are read-only")

    def setdefault(self, *_, **__):
        raise TypeError(f"'{type(self).__name__}' object attributes are read-only")

    def update(self, *_, **__):
        raise TypeError(f"'{type(self).__name__}' object attributes are read-only")

    def clear(self, *_, **__):
        raise TypeError(f"'{type(self).__name__}' object attributes are read-only")

    def __delitem__(self, *_, **__):
        raise TypeError(f"'{type(self).__name__}' object attributes are read-only")

    def __delattr__(self, *_, **__):
        raise TypeError(f"'{type(self).__name__}' object attributes are read-only")

    def __reduce__(self):
        return type(self), (), dict(self)

    def __setstate__(self, state):
        dict.update(self, state)

    def __copy__(self):
        return self


class FrozenStruct(Frozen, Struct):
    __slots__ = ('_hash',)


def merged(*dicts, **kwargs):
    """
    Merge dictionaries. Later keys overwrite.

    .. code-block:: python

        merged(dict(a=1), dict(b=2), c=3, d=1)

    """
    if not dicts:
        return Struct()
    result = dict()
    for d in dicts:
        result.update(d)
    result.update(kwargs)
    struct_type = type(dicts[0])
    return struct_type(**result)
