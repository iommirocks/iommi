from iommi.struct import (
    Frozen,
    Struct,
)


def _get_type_of_namespace(dict_value):
    if isinstance(dict_value, Namespace):
        return type(dict_value)
    else:
        return Namespace


class Namespace(Struct):
    """
    Namespace represents a structure of nested dicts. It behaves like a regular
    dictionary, with the added feature that values at nested levels can be set via
    `setitem_path` by providing a "path" of the form "<name1>__<name2>__<name3>",
    where the double underscores separate attribute names at increasing levels of
    depth.

    Attributes at nested levels can be retrieved either using "dotted" access
    such as `foo_namespace.a.b.c`, or via the helper function `getattr_path` by
    passing a double-underscored path like the example above.

    In addition, a Namespace can act like a function if it contains a toplevel
    item `{"call_target": f, ...}` where `f` is a callable. When the Namespace
    is called, `f` is called with the contents of the Namespace as keyword
    arguments (excluding f itself).
    """

    # noinspection PyMissingConstructor
    def __init__(self, *dicts, **kwargs):
        for mappings in dicts:
            for path, value in dict.items(mappings):
                self.setitem_path(path, value)
        for path, value in dict.items(kwargs):
            self.setitem_path(path, value)

    def setitem_path(self, path, value):
        key, delimiter, rest_path = path.partition('__')
        existing = Struct.get(self, key)

        if value is EMPTY:
            value = Namespace()

        if delimiter:
            if isinstance(existing, dict):
                type_of_namespace = _get_type_of_namespace(existing)
                self[key] = type_of_namespace(existing, {rest_path: value})
            elif callable(existing):
                self[key] = Namespace(dict(call_target=existing), {rest_path: value})
            else:
                # Unable to promote to Namespace, just overwrite
                self[key] = Namespace({rest_path: value})
        else:
            if existing is None:
                # This is a common case and checking for None is fast
                self[key] = value
            elif getattr(existing, 'shortcut', False):
                # Avoid merging Shortcuts
                self[key] = value
            elif isinstance(existing, dict):
                type_of_namespace = _get_type_of_namespace(existing)
                if isinstance(value, dict):
                    self[key] = type_of_namespace(existing, value)
                elif callable(value):
                    self[key] = type_of_namespace(existing, call_target=value)
                else:
                    # Unable to promote to Namespace, just overwrite
                    self[key] = value
            elif callable(existing):
                if isinstance(value, dict):
                    type_of_namespace = _get_type_of_namespace(value)
                    self[key] = type_of_namespace(dict(call_target=existing), value)
                else:
                    self[key] = value
            else:
                self[key] = value

    def __repr__(self):
        # Note: `repr` is called on any values in the namespace
        flattened_key_value_pairs = ", ".join(
            '%s=%r' % (k, v) for k, v in sorted(flatten_items(self), key=lambda x: x[0])
        )
        return "%s(%s)" % (type(self).__name__, flattened_key_value_pairs)

    def __str__(self):
        # Note: `str` is called on any values in the namespace
        flattened_key_value_pairs = ", ".join(
            '%s=%s' % (k, v) for k, v in sorted(flatten_items(self), key=lambda x: x[0])
        )
        return "%s(%s)" % (type(self).__name__, flattened_key_value_pairs)

    def __call__(self, *args, **kwargs):
        params = Namespace(self, kwargs)

        try:
            call_target = params.pop('call_target')
        except KeyError as e:
            raise TypeError(
                'Namespace was used as a function, but no call_target was specified. The namespace is: %s' % self
            ) from e

        if isinstance(call_target, Namespace):
            if 'call_target' in call_target:
                # Override of the default
                call_target.pop('attribute', None)
                call_target.pop('cls', None)
            else:
                # The default
                attribute = call_target.get('attribute', None)
                if attribute is not None:
                    call_target = getattr(call_target.cls, attribute)
                else:
                    call_target = call_target.cls

        return call_target(*args, **params)


class FrozenNamespace(Frozen, Namespace):
    pass


EMPTY = FrozenNamespace()


def flatten(namespace):
    return dict(flatten_items(namespace))


def flatten_items(namespace):
    def mappings(n, visited, prefix=''):
        for key, value in dict.items(n):
            path = prefix + key
            if isinstance(value, Namespace):
                if id(value) not in visited:
                    if value:
                        for mapping in mappings(value, visited=[id(value)] + visited, prefix=path + '__'):
                            yield mapping
                    else:
                        yield path, Namespace()
            else:
                yield path, value

    return mappings(namespace, visited=[])


# The first argument has a funky name to avoid name clashes with stuff in kwargs
def setdefaults_path(__target__, *defaults, **kwargs):
    args = [kwargs] + list(reversed(defaults)) + [__target__]
    dict.update(__target__, Namespace(*args))
    return __target__


_MISSING = object()


def getattr_path(obj, path, default=_MISSING):
    """
    Get an attribute path, as defined by a string separated by '__'.
    getattr_path(foo, 'a__b__c') is roughly equivalent to foo.a.b.c but
    will short circuit to return None if something on the path is None.
    If no default value is provided AttributeError is raised if an attribute
    is missing somewhere along the path. If a default value is provided that
    value is returned.
    """
    if path == '':
        return obj
    current = obj
    parts = path.split('__')
    for name in parts:
        if default is _MISSING:
            try:
                current = getattr(current, name)
            except AttributeError as e:
                raise AttributeError(f"'{type(obj).__name__}' object has no attribute path '{path}', since {e}") from e

        else:
            current = getattr(current, name, _MISSING)
            if current is _MISSING:
                return default
        if current is None:
            return None
    return current


def setattr_path(obj, path, value):
    """
    Set an attribute path, as defined by a string separated by '__'.
    setattr_path(foo, 'a__b__c', value) is equivalent to "foo.a.b.c = value".
    """
    path = path.split('__')
    o = obj
    for name in path[:-1]:
        o = getattr(o, name)
    setattr(o, path[-1], value)
    return obj
