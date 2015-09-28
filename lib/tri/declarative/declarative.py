from collections import OrderedDict
from functools import total_ordering
import functools
import itertools
from tri.struct import Struct


def with_meta(class_to_decorate=None, add_init_kwargs=True):
    """
        Class decorator to enable a class (and it's sub-classes) to have a 'Meta' class attribute.
        The members of the Meta class will be injected as arguments to constructor calls. e.g.:

        .. code:: python

            @with_meta
            class Foo(object):

                class Meta:
                    foo = 'bar'

                def __init__(self, foo, buz):
                    assert foo == 'bar'
                    assert buz == 'buz'

            foo = Foo(buz='buz')

            # Members of the 'Meta' class can be accessed thru the get_meta() class method.
            assert foo.get_meta() == {'foo': 'bar'}
            assert Foo.get_meta() == {'foo': 'bar'}

            Foo()  # Crashes, has 'foo' parameter, but no has no 'buz' parameter.


        Another example:

        .. code:: python

            class Foo(object):

                class Meta:
                    foo = 'bar'
                    bar = 'bar'

            @with_meta
            class Bar(Foo):

                class Meta:
                    foo = 'foo'
                    buz = 'buz'

                def __init__(self, *args, **kwargs):
                    assert kwargs['foo'] == 'foo'  # from Bar (overrides Foo)
                    assert kwargs['bar'] == 'bar'  # from Foo
                    assert kwargs['buz'] == 'buz'  # from Bar


        This can be used e.g to enable sub-classes to modify constructor default arguments.

        The passing of the merged name space to the constructor is optional.
        It can be disabled by passing add_init_kwargs=False to the decorator.

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

        .. code:: python

        @declarative_member
        class Thing(object):
            pass

        t1 = Thing()
        t2 = Thing()
        t3 = Thing()

        assert sorted([t2, t3, t1]) == [t1, t2, t3]

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
        That is, @declarative classes will get an additional argument to constructor,
        containing an OrderedDict with all class members matching the specified type.


        .. code:: python

            @declarative(str)
            class Foo(object):
                bar = 'barbar'
                baz = 'bazbaz'
                boink = 17

                def __init__(self, members):
                    assert members == OrderedDict([('bar', 'barbar'), ('baz', 'bazbaz')])
                    assert 'boink' not in members

            f = Foo()

        The class members will also be collected from sub-classes:

        .. code:: python

            @declarative(str)
            class Foo(object):

                def __init__(self, members):
                    assert members == OrderedDict([('bar', 'barbar'), ('baz', 'bazbaz')])

            class MyFoo(Foo):
                bar = 'barbar'
                baz = 'bazbaz'

                def __init__(self):
                    super(MyFoo, self).__init__()

            f = MyFoo()


        The parameter can be given another name:

        .. code:: python

            @declarative(str, 'things')
            class Foo(object):

                bar = 'barbar'

                def __init__(self, things):
                    assert things == OrderedDict([('bar', 'barbar')])

            f = Foo()


        The class members will be collected from all sub-classes. Note that the collected dict will be ordered by
        sorting on the values (in the 'str' example, in alphabetical order). If creation order is needed, use the
         @declarative_member decorator.

        Also note that the collection of class members based on their class does NOT interfere with
        instance constructor argument of the same type.

        .. code:: python

            @declarative(str)
            class Foo(object):
                a_thing = 'foo'
                def __init__(self, members):
                    assert members == OrderedDict([('bar', 'barbar'), ('baz', 'bazbaz'), ('a_thing', 'foo'])
                    assert 'other_string' not in members


            class MyFoo(Foo):
                bar = 'barbar'

            class MyOtherFoo(MyFoo):
                baz = 'bazbaz'

                def __init__(self, other_string)
                    assert other_string == 'elephant'

            f = MyOtherFoo('elephant)

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
