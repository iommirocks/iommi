from collections import OrderedDict
from functools import total_ordering
import functools
import itertools
from tri.struct import Struct


def with_meta(class_to_decorate=None, add_init_kwargs=True):
    """
        Class decorator to enable a class (and it's sub-classes) to have a 'Meta' class attribute.

        The members of the Meta class will be injected to constructor calls. e.g.:

        .. code:: python

            @with_meta
            class Foo(object):

                class Meta:
                    foo = 'bar'

                def __init__(self, foo):
                    assert foo == 'bar'


        This can be used e.g to enable sub-classes to modify constructor defaults.

        The passing of the merged name space to the constructor is optional (there is a getter class
        method to obtain the same value:

        .. code:: python

            @with_meta(add_init_kwargs=False)
            class Foo(object):
                class Meta:
                    foo = 'bar'

            assert Foo().get_meta() == {'foo': 'bar'}

    """

    if class_to_decorate is None:
        return functools.partial(with_meta, add_init_kwargs=add_init_kwargs)

    if 'Meta' not in class_to_decorate.__dict__:
        blank_meta = type('Meta', (object, ), {})
        setattr(class_to_decorate, 'Meta', blank_meta)

    if add_init_kwargs:
        __init__orig = class_to_decorate.__init__

        def __init__(self, *args, **kwargs):
            new_kwargs = {}
            new_kwargs.update((k, v) for k, v in self.get_meta().items() if not k.startswith('_'))
            new_kwargs.update(kwargs)
            __init__orig(self, *args, **new_kwargs)

        setattr(class_to_decorate, '__init__', __init__)

    def get_meta(cls):
        merged_attributes = Struct()
        for class_ in reversed(cls.mro()):
            if hasattr(class_, 'Meta'):
                for key, value in class_.Meta.__dict__.items():
                    if key.startswith('__'):  # Skip internal attributes
                        continue
                    merged_attributes[key] = value
        return merged_attributes

    setattr(class_to_decorate, 'get_meta', classmethod(get_meta))

    return class_to_decorate


def declarative_member(class_to_decorate):
    """
        Class decorator that ensures that instances will be ordered after creation order when sorted.

        This is useful for classes intended to be used as members of a @declarative class when member order matters.
    """

    next_index = itertools.count().next

    __init__orig = class_to_decorate.__init__

    def __init__(self, *args, **kwargs):
        object.__setattr__(self, '_index', next_index())
        __init__orig(self, *args, **kwargs)

    setattr(class_to_decorate, '__init__', __init__)

    # noinspection PyProtectedMember
    def __lt__(self, other):
        return self._index < other._index

    setattr(class_to_decorate, '__lt__', __lt__)

    class_to_decorate = total_ordering(class_to_decorate)

    return class_to_decorate


def declarative(member_class, parameter='members', add_init_kwargs=True):
    """
        Class decorator to enable classes to be defined in the style of django models.

        .. code:: python

            @declarative(str)
            class Foo(object):
                def __init__(self, foo, members):
                    assert foo == 'foo'
                    assert members == OrderedDict([('bar', 'barbar'), ('baz', 'bazbaz')])

            class MyFoo(Foo):
                class Meta:
                    foo = 'foo'

                bar = 'barbar'
                baz = 'bazbaz'

            f = MyFoo()


        is equivalent to:

        .. code:: python

            class Foo(object):
                def __init__(self, foo, members):
                    assert foo == 'foo'
                    assert members == OrderedDict([('bar', 'barbar'), ('baz', 'bazbaz')])

            f = Foo(foo='foo', members=OrderedDict([('bar', 'barbar'), ('baz', 'bazbaz')])
    """

    def get_members(cls):
        members = OrderedDict()
        for base in cls.__bases__:
            meta = getattr(base, 'Meta', None)
            if meta is not None:
                inherited_members = getattr(meta, parameter, {})
                members.update(inherited_members)

        def generate_member_bindings():
            for name, obj in cls.__dict__.items():
                if isinstance(obj, member_class):
                    yield name, obj

        members.update(sorted(generate_member_bindings(), key=lambda x: x[1]))

        return members

    def decorator(class_to_decorate):

        class DeclarativeMeta(type):
            def __init__(cls, name, bases, dict):
                if 'Meta' not in cls.__dict__:
                    setattr(cls, 'Meta', type('Meta', (object, ), {}))
                setattr(cls.Meta, parameter, get_members(cls))
                super(DeclarativeMeta, cls).__init__(name, bases, dict)

        new_class = DeclarativeMeta(class_to_decorate.__name__,
                                    class_to_decorate.__bases__,
                                    dict(class_to_decorate.__dict__))
        new_class = with_meta(add_init_kwargs=add_init_kwargs)(new_class)
        return new_class

    return decorator
