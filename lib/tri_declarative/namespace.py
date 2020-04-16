from tri_struct import Struct, Frozen


class Namespace(Struct):
    # noinspection PyMissingConstructor
    def __init__(self, *dicts, **kwargs):
        if dicts or kwargs:
            for mappings in list(dicts) + [kwargs]:
                for path, value in dict.items(mappings):
                    self.setitem_path(path, value)

    def setitem_path(self, path, value):
        from .shortcut import is_shortcut

        if value is EMPTY:
            value = Namespace()
        key, delimiter, rest_path = path.partition('__')

        def get_type_of_namespace(dict_value):
            if isinstance(dict_value, Namespace):
                return type(dict_value)
            else:
                return Namespace

        existing = Struct.get(self, key)
        if delimiter:
            if isinstance(existing, dict):
                type_of_namespace = get_type_of_namespace(existing)
                self[key] = type_of_namespace(existing, {rest_path: value})
            elif callable(existing):
                self[key] = Namespace(dict(call_target=existing), {rest_path: value})
            else:
                # Unable to promote to Namespace, just overwrite
                self[key] = Namespace({rest_path: value})
        else:
            if is_shortcut(existing):
                # Avoid merging Shortcuts
                self[key] = value
            elif isinstance(existing, dict):
                type_of_namespace = get_type_of_namespace(existing)
                if isinstance(value, dict):
                    self[key] = type_of_namespace(existing, value)
                elif callable(value):
                    self[key] = type_of_namespace(existing, call_target=value)
                else:
                    # Unable to promote to Namespace, just overwrite
                    self[key] = value
            elif callable(existing):
                if isinstance(value, dict):
                    type_of_namespace = get_type_of_namespace(value)
                    self[key] = type_of_namespace(Namespace(call_target=existing), value)
                else:
                    self[key] = value
            else:
                self[key] = value

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, ", ".join('%s=%r' % (k, v) for k, v in sorted(flatten_items(self), key=lambda x: x[0])))

    def __str__(self):
        return "%s(%s)" % (type(self).__name__, ", ".join('%s=%s' % (k, v) for k, v in sorted(flatten_items(self), key=lambda x: x[0])))

    def __call__(self, *args, **kwargs):
        params = Namespace(self, kwargs)

        try:
            call_target = params.pop('call_target')
        except KeyError:
            raise TypeError('Namespace was used as a function, but no call_target was specified. The namespace is: %s' % self)

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
