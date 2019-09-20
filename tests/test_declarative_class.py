from collections import OrderedDict
from random import shuffle

import pytest
from tri_declarative import (
    add_args_to_init_call,
    creation_ordered,
    declarative,
    with_meta,
)
from tri_struct import Struct


@creation_ordered
class Member(Struct):
    pass


@declarative(Member)
class Declarative:
    def __init__(self, members):
        self.members = members


def test_constructor_noop():
    subject = Declarative(members={'foo': Member(foo='bar')})
    assert subject.members == {'foo': Member(foo='bar')}


def test_find_members():
    class MyDeclarative(Declarative):
        foo = Member(foo='bar')

    subject = MyDeclarative()
    assert subject.members == OrderedDict([('foo', Member(foo='bar'))])


def test_find_members_by_check_function():
    @declarative(
        is_member=lambda x: x == "foo",
        sort_key=lambda x: x,
    )
    class Declarative:
        foo = "foo"
        bar = "bar"

        def __init__(self, members):
            self.members = members

    subject = Declarative()
    assert dict(foo='foo') == subject.members


def test_required_parameter():
    with pytest.raises(TypeError) as e:
        declarative()

    assert str(
        e.value) == "The @declarative decorator needs either a member_class parameter or an is_member check function (or both)"


def test_non_copyable_members():
    @declarative(
        is_member=lambda x: True,
        sort_key=lambda x: x,
    )
    class Declarative:
        x = object.__init__

        def __init__(self, members):
            self.members = members

    subject = Declarative()
    assert list(subject.members.keys()) == ['x']


def test_find_member_fail_on_tuple():
    with pytest.raises(TypeError):
        class MyDeclarative(Declarative):
            foo = Member(foo='bar'),


def test_missing_ordering():
    with pytest.raises(TypeError):
        @declarative(str)
        class Fail:
            x = "x"

        Fail()


def test_constructor_injector_attribute_retention():
    def my_wrapper(f):
        f.my_attribute = 17
        return f

    @declarative(str, sort_key=lambda x: x)
    class Declarative:
        @my_wrapper
        def __init__(self, members):
            super(Declarative, self).__init__()

    assert Declarative().__init__.my_attribute == 17


def test_constructor_init_hook_attribute_retention():
    def my_wrapper(f):
        f.my_attribute = 17
        return f

    @declarative(str, add_init_kwargs=False, sort_key=lambda x: x)
    class Declarative:
        @my_wrapper
        def __init__(self):
            """foo"""
            super(Declarative, self).__init__()

    assert Declarative().__init__.my_attribute == 17
    assert Declarative.__init__.__doc__ == 'foo'


def test_sort_key():
    @declarative(str, sort_key=lambda x: x)
    class Ok:
        a = "y"
        b = "x"

        def __init__(self, members):
            assert list(members.keys()) == ['b', 'a']

    Ok()


def test_find_members_not_shadowed_by_meta():
    class MyDeclarative(Declarative):
        foo = Member(foo='bar')

        class Meta:
            pass

    subject = MyDeclarative()
    assert subject.members == OrderedDict([
        ('foo', Member(foo='bar')),
    ])


def test_find_members_inherited():
    class MyDeclarative(Declarative):
        foo = Member(foo='bar')

    class MyDeclarativeSubclass(MyDeclarative):
        bar = Member(foo='baz')

    subject = MyDeclarativeSubclass()
    assert subject.members == OrderedDict([
        ('foo', Member(foo='bar')),
        ('bar', Member(foo='baz')),
    ])


def test_isolated_inheritance():
    @declarative(int, add_init_kwargs=False, sort_key=lambda x: x)
    class Base:
        a = 1

    class Foo(Base):
        b = 2

    class Bar(Base):
        c = 3

    assert Base.get_declared() == OrderedDict([('a', 1)])
    assert Foo.get_declared() == OrderedDict([('a', 1), ('b', 2)])
    assert Bar.get_declared() == OrderedDict([('a', 1), ('c', 3)])


def test_find_members_from_base():
    @declarative(Member)
    class Base:
        foo = Member(foo='foo')

    class Sub(Base):
        bar = Member(bar='bar')

    assert Sub._declarative_members == OrderedDict([
        ('foo', Member(foo='foo')),
        ('bar', Member(bar='bar')),
    ])


def test_find_members_shadow():
    @declarative(Member)
    class Base:
        foo = Member(bar='bar')

    class Sub(Base):
        foo = Member(bar='baz')

    assert Sub._declarative_members == OrderedDict([('foo', Member(bar='baz'))])


def test_member_attribute_naming():
    @declarative(Member, 'foo')
    class Declarative:
        def __init__(self, foo):
            self.foo = foo

    class MyDeclarative(Declarative):
        bar = Member(baz='buzz')

    subject = MyDeclarative()
    assert subject.foo == OrderedDict([('bar', Member(baz='buzz'))])


def test_string_members():
    @declarative(str, sort_key=lambda x: x)
    class Declarative:
        foo = 'bar'

    assert Declarative.get_declared() == OrderedDict([('foo', 'bar')])


def test_declarative_and_meta():
    @with_meta
    @declarative(str, sort_key=lambda x: x)
    class Foo:
        foo = 'foo'

        class Meta:
            bar = 'bar'

        def __init__(self, members, bar):
            assert OrderedDict([('foo', 'foo')]) == members
            assert 'bar' == bar

    Foo()


def test_declarative_and_meta_subclass_no_constructor_hack_workaround():
    @declarative(str, sort_key=lambda x: x)
    class Foo:

        def __init__(self, members, bar):
            assert OrderedDict() == members
            assert 'bar' == bar

    @with_meta
    class Bar(Foo):
        class Meta:
            bar = 'bar'

        # This is a hack to make the @with_meta argument injector not tripping up when finding the paren constructor
        def __init__(self, *args, **kwargs):
            super(Bar, self).__init__(*args, **kwargs)

    Bar()


def test_declarative_and_meta_other_order():
    @declarative(str, sort_key=lambda x: x)
    @with_meta
    class Foo:
        foo = 'foo'

        class Meta:
            bar = 'bar'

        def __init__(self, members, bar):
            assert members == OrderedDict([('foo', 'foo')])
            assert bar == 'bar'

    Foo()


def test_multiple_types():
    @declarative(int, 'ints', sort_key=lambda x: x)
    @declarative(str, 'strs', sort_key=lambda x: x)
    class Foo:
        a = 1
        b = "b"

        def __init__(self, ints, strs):
            assert ints == OrderedDict([('a', 1)])
            assert strs == OrderedDict([('b', 'b')])

    Foo()


def test_multiple_types_inheritance():
    @declarative(int, 'ints', sort_key=lambda x: x)
    class Foo:
        i = 1
        a = 'a'

        def __init__(self, ints):
            assert ints == OrderedDict([('i', 1), ('j', 2), ('k', 3)])
            super(Foo, self).__init__()

    @declarative(str, 'strs', sort_key=lambda x: x)
    class Bar(Foo):
        j = 2
        b = "b"

        def __init__(self, strs):
            assert strs == OrderedDict([('b', 'b'), ('c', 'c')])
            super(Bar, self).__init__()

    class Baz(Bar):
        k = 3
        c = 'c'

        def __init__(self):
            super(Baz, self).__init__()

    Baz()


def test_add_args_to_init_call():
    class C:
        def __init__(self, x, y=None):
            self.x = x
            self.y = y

    add_args_to_init_call(C, lambda self: dict(x=17))

    c = C()
    assert c.x == 17
    assert c.y is None

    add_args_to_init_call(C, lambda self: dict(y=42))

    c = C()
    assert c.x == 17
    assert c.y == 42

    c = C(x=1, y=2)
    assert c.x == 1
    assert c.y == 2

    c = C(1, 2)
    assert c.x == 1
    assert c.y == 2


def test_copy_of_constructor_args():
    @declarative(list, sort_key=lambda x: x)
    class C:
        x = []

        def __init__(self, members):
            members['x'].append('foo')

    a = C()
    C()

    assert a.x == ['foo']  # Only added once for each instance


def test_copy_of_attributes():
    @declarative(list, sort_key=lambda x: x)
    class C:
        x = []

        def __init__(self, members):
            pass

    a = C()
    b = C()

    a.x.append('bar')
    assert b.x == []  # No leak from other instance


def test_copy_of_attributes_no_kwargs_injection():
    @declarative(list, add_init_kwargs=False, sort_key=lambda x: x)
    class C:
        x = []

        def __init__(self):
            pass

    a = C()
    b = C()

    a.x.append('bar')
    assert b.x == []  # No leak from other instance


def test_copy_of_attributes_no_kwargs_injection_with_no_init():
    @declarative(list, add_init_kwargs=False, sort_key=lambda x: x)
    class C:
        x = []

    a = C()
    b = C()

    a.x.append('bar')
    assert b.x == []  # No leak from other instance


def test_copy_of_attributes_no_kwargs_injection_with_no_init_shadow_base():
    class MyException(Exception):
        pass

    class C:
        def __init__(self):
            raise MyException()

    @declarative(list, add_init_kwargs=False)
    class D(C):
        pass

    with pytest.raises(MyException):
        D()


def test_creation_ordered():
    test_list = [Member() for _ in range(10)]
    shuffled_list = test_list[:]
    shuffle(shuffled_list)
    assert sorted(shuffled_list) == test_list


def test_creation_ordered_attribute_retention():
    def my_wrapper(f):
        f.my_attribute = 17
        return f

    @creation_ordered
    class Foo:
        @my_wrapper
        def __init__(self):
            pass

    assert Foo().__init__.my_attribute == 17


def test_getter_and_setter_interface():
    @declarative(str, sort_key=lambda x: x, add_init_kwargs=False)
    class Foo:
        foo = "foo"
        bar = "bar"

    assert Foo.get_declared() == dict(foo="foo", bar="bar")
    assert Foo().get_declared() == dict(foo="foo", bar="bar")

    class Bar(Foo):
        pass

    assert Bar.get_declared() == dict(foo='foo', bar='bar')
    Bar.set_declared(dict(baz='baz'))
    assert Bar.get_declared() == dict(baz='baz')


def test_init_hook():
    @declarative(str, sort_key=lambda x: x, add_init_kwargs=False)
    class Foo:
        foo = "foo"

        def __init__(self):
            self.called_init = True

    assert Foo().called_init


def test_init_hook2():
    @declarative(str, sort_key=lambda x: x, add_init_kwargs=False)
    class Foo(dict):
        foo = "foo"

    assert Foo(x=1)['x'] == 1


def test_whitelist_dunder_weakref():
    class Foo:
        pass

    Bar = declarative(str)(Foo)

    assert Bar.__dict__ is not Foo.__dict__
    assert Bar.__weakref__ is None or Bar.__weakref__ is not Foo.__weakref__


def test_require_ordering():
    with pytest.raises(TypeError) as e:
        @declarative(str)
        class Foo:
            foo = "foo"

    assert str(e.value) == 'Missing member ordering definition. ' \
                           'Use @creation_ordered or specify sort_key'


def test_wrap_creation_ordered_preserves_doc_string():
    @creation_ordered
    class Foo(Struct):
        def __init__(self):
            """foo"""

    assert Foo.__init__.__doc__ == 'foo'


def test_wrap_with_meta_preserves_doc_string():
    @with_meta
    class Foo(Struct):
        def __init__(self):
            """foo"""

    assert Foo.__init__.__doc__ == 'foo'
