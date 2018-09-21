from random import shuffle

from collections import OrderedDict
import pytest
from tri.struct import Struct

from tri.declarative import creation_ordered, declarative, with_meta, add_args_to_init_call


@creation_ordered
class Member(Struct):
    pass


@declarative(Member)
class Declarative(object):
    def __init__(self, members):
        self.members = members


def test_constructor_noop():
    subject = Declarative(members={'foo': Member(foo='bar')})
    assert {'foo': Member(foo='bar')} == subject.members


def test_find_members():
    class MyDeclarative(Declarative):
        foo = Member(foo='bar')

    subject = MyDeclarative()
    assert OrderedDict([('foo', Member(foo='bar'))]) == subject.members


def test_find_members_by_check_function():
    @declarative(
        is_member=lambda x: x == "foo",
        sort_key=lambda x: x,
    )
    class Declarative(object):
        foo = "foo"
        bar = "bar"

        def __init__(self, members):
            self.members = members

    subject = Declarative()
    assert dict(foo='foo') == subject.members


def test_required_parameter():
    with pytest.raises(TypeError) as e:
        declarative()

    assert "The @declarative decorator needs either a member_class parameter or an is_member check function (or both)" == str(e.value)


def test_non_copyable_members():
    @declarative(
        is_member=lambda x: True,
        sort_key=lambda x: x,
    )
    class Declarative(object):
        x = object.__init__

        def __init__(self, members):
            self.members = members

    subject = Declarative()
    assert ['x'] == list(subject.members.keys())


def test_find_member_fail_on_tuple():
    with pytest.raises(TypeError):
        class MyDeclarative(Declarative):
            foo = Member(foo='bar'),


def test_missing_ordering():
    with pytest.raises(TypeError):
        @declarative(str)
        class Fail(object):
            x = "x"

        Fail()


def test_constructor_injector_attribute_retention():
    def my_wrapper(f):
        f.my_attribute = 17
        return f

    @declarative(str, sort_key=lambda x: x)
    class Declarative(object):
        @my_wrapper
        def __init__(self, members):
            super(Declarative, self).__init__()

    assert 17 == Declarative().__init__.my_attribute


def test_constructor_init_hook_attribute_retention():
    def my_wrapper(f):
        f.my_attribute = 17
        return f

    @declarative(str, add_init_kwargs=False, sort_key=lambda x: x)
    class Declarative(object):
        @my_wrapper
        def __init__(self):
            super(Declarative, self).__init__()

    assert 17 == Declarative().__init__.my_attribute


def test_sort_key():
    @declarative(str, sort_key=lambda x: x)
    class Ok(object):
        a = "y"
        b = "x"

        def __init__(self, members):
            assert ['b', 'a'] == list(members.keys())

    Ok()


def test_find_members_not_shadowed_by_meta():

    class MyDeclarative(Declarative):
        foo = Member(foo='bar')

        class Meta:
            pass

    subject = MyDeclarative()
    assert OrderedDict([('foo', Member(foo='bar'))]) == subject.members


def test_find_members_inherited():

    class MyDeclarative(Declarative):
        foo = Member(foo='bar')

    class MyDeclarativeSubclass(MyDeclarative):
        bar = Member(foo='baz')

    subject = MyDeclarativeSubclass()
    assert OrderedDict([('foo', Member(foo='bar')), ('bar', Member(foo='baz'))]) == subject.members


def test_isolated_inheritance():
    @declarative(int, add_init_kwargs=False, sort_key=lambda x: x)
    class Base(object):
        a = 1

    class Foo(Base):
        b = 2

    class Bar(Base):
        c = 3

    assert OrderedDict([('a', 1)]) == Base.get_declared()
    assert OrderedDict([('a', 1), ('b', 2)]) == Foo.get_declared()
    assert OrderedDict([('a', 1), ('c', 3)]) == Bar.get_declared()


def test_find_members_from_base():

    @declarative(Member)
    class Base(object):
        foo = Member(foo='foo')

    class Sub(Base):
        bar = Member(bar='bar')

    assert OrderedDict([('foo', Member(foo='foo')), ('bar', Member(bar='bar'))]) == Sub._declarative_members


def test_find_members_shadow():
    @declarative(Member)
    class Base(object):
        foo = Member(bar='bar')

    class Sub(Base):
        foo = Member(bar='baz')

    assert OrderedDict([('foo', Member(bar='baz'))]) == Sub._declarative_members


def test_member_attribute_naming():

    @declarative(Member, 'foo')
    class Declarative(object):
        def __init__(self, foo):
            self.foo = foo

    class MyDeclarative(Declarative):
        bar = Member(baz='buzz')

    subject = MyDeclarative()
    assert OrderedDict([('bar', Member(baz='buzz'))]) == subject.foo


def test_string_members():

    @declarative(str, sort_key=lambda x: x)
    class Declarative(object):

        foo = 'bar'

    assert Declarative.get_declared() == OrderedDict([('foo', 'bar')])


def test_declarative_and_meta():

    @with_meta
    @declarative(str, sort_key=lambda x: x)
    class Foo(object):
        foo = 'foo'

        class Meta:
            bar = 'bar'

        def __init__(self, members, bar):
            assert OrderedDict([('foo', 'foo')]) == members
            assert 'bar' == bar

    Foo()


# Not yet working...
@pytest.mark.skipif(True, reason="Not yet working")
def test_declarative_and_meta_subclass_no_constructor():
    @declarative(str, sort_key=lambda x: x)
    class Foo(object):

        def __init__(self, members, bar):
            assert OrderedDict() == members
            assert 'bar' == bar

    @with_meta
    class Bar(Foo):
        class Meta:
            bar = 'bar'

    Bar()


def test_declarative_and_meta_subclass_no_constructor_hack_workaround():
    @declarative(str, sort_key=lambda x: x)
    class Foo(object):

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
    class Foo(object):
        foo = 'foo'

        class Meta:
            bar = 'bar'

        def __init__(self, members, bar):
            assert OrderedDict([('foo', 'foo')]) == members
            assert 'bar' == bar

    Foo()


def test_multiple_types():

    @declarative(int, 'ints', sort_key=lambda x: x)
    @declarative(str, 'strs', sort_key=lambda x: x)
    class Foo(object):
        a = 1
        b = "b"

        def __init__(self, ints, strs):
            assert OrderedDict([('a', 1)]) == ints
            assert OrderedDict([('b', 'b')]) == strs

    Foo()


def test_multiple_types_inheritance():

    @declarative(int, 'ints', sort_key=lambda x: x)
    class Foo(object):
        i = 1
        a = 'a'

        def __init__(self, ints):
            assert OrderedDict([('i', 1), ('j', 2), ('k', 3)]) == ints
            super(Foo, self).__init__()

    @declarative(str, 'strs', sort_key=lambda x: x)
    class Bar(Foo):
        j = 2
        b = "b"

        def __init__(self, strs):
            assert OrderedDict([('b', 'b'), ('c', 'c')]) == strs
            super(Bar, self).__init__()

    class Baz(Bar):
        k = 3
        c = 'c'

        def __init__(self):
            super(Baz, self).__init__()

    Baz()


def test_add_args_to_init_call():

    class C(object):
        def __init__(self, x, y=None):
            self.x = x
            self.y = y

    add_args_to_init_call(C, lambda self: dict(x=17))

    c = C()
    assert 17 == c.x
    assert None is c.y

    add_args_to_init_call(C, lambda self: dict(y=42))

    c = C()
    assert 17 == c.x
    assert 42 == c.y

    c = C(x=1, y=2)
    assert 1 == c.x
    assert 2 == c.y

    c = C(1, 2)
    assert 1 == c.x
    assert 2 == c.y


def test_copy_of_constructor_args():

    @declarative(list, sort_key=lambda x: x)
    class C(object):
        x = []

        def __init__(self, members):
            members['x'].append('foo')

    a = C()
    C()

    assert ['foo'] == a.x  # Only added once for each instance


def test_copy_of_attributes():

    @declarative(list, sort_key=lambda x: x)
    class C(object):
        x = []

        def __init__(self, members):
            pass

    a = C()
    b = C()

    a.x.append('bar')
    assert [] == b.x  # No leak from other instance


def test_copy_of_attributes_no_kwargs_injection():

    @declarative(list, add_init_kwargs=False, sort_key=lambda x: x)
    class C(object):
        x = []

        def __init__(self):
            pass

    a = C()
    b = C()

    a.x.append('bar')
    assert [] == b.x  # No leak from other instance


def test_copy_of_attributes_no_kwargs_injection_with_no_init():

    @declarative(list, add_init_kwargs=False, sort_key=lambda x: x)
    class C(object):
        x = []

    a = C()
    b = C()

    a.x.append('bar')
    assert [] == b.x  # No leak from other instance


def test_copy_of_attributes_no_kwargs_injection_with_no_init_shadow_base():

    class MyException(Exception):
        pass

    class C(object):
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
    assert test_list == sorted(shuffled_list)


def test_creation_ordered_attribute_retention():
    def my_wrapper(f):
        f.my_attribute = 17
        return f

    @creation_ordered
    class Foo(object):
        @my_wrapper
        def __init__(self):
            pass

    assert 17 == Foo().__init__.my_attribute


def test_getter_and_setter_interface():
    @declarative(str, sort_key=lambda x: x, add_init_kwargs=False)
    class Foo(object):
        foo = "foo"
        bar = "bar"

    assert dict(foo="foo", bar="bar") == Foo.get_declared()
    assert dict(foo="foo", bar="bar") == Foo().get_declared()

    class Bar(Foo):
        pass

    assert dict(foo='foo', bar='bar') == Bar.get_declared()
    Bar.set_declared(dict(baz='baz'))
    assert dict(baz='baz') == Bar.get_declared()


def test_init_hook():
    @declarative(str, sort_key=lambda x: x, add_init_kwargs=False)
    class Foo(object):
        foo = "foo"

        def __init__(self):
            self.called_init = True

    assert Foo().called_init


def test_whitelist_dunder_weakref():

    class Foo(object):
        pass

    Bar = declarative(str)(Foo)

    assert Bar.__dict__ is not Foo.__dict__
    assert Bar.__weakref__ is None or Bar.__weakref__ is not Foo.__weakref__


def test_require_ordering():

    with pytest.raises(TypeError) as e:
        @declarative(str)
        class Foo(object):
            foo = "foo"

    assert 'Missing member ordering definition. Use @creation_ordered or specify sort_key' == str(e.value)
