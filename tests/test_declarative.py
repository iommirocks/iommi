import pytest
from tri_struct import Struct

from tri_declarative import (
    declarative,
    with_meta,
)
from tri_declarative.declarative import get_members
from tri_declarative.util import add_args_to_init_call


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

    # noinspection PyArgumentList
    subject = MyDeclarative()
    assert subject.members == dict(foo=Member(foo='bar'))


def test_declarative_with_dunder_in_name():
    @declarative(str)
    class Foo:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    assert Foo(
        members=Struct(bink__bonk=4711),
    ).kwargs == dict(
        members=dict(bink__bonk=4711),
    )


def test_find_members_by_check_function():
    @declarative(
        is_member=lambda x: x == "foo",
        sort_key=lambda x: x,
    )
    class MyDeclarative:
        foo = "foo"
        bar = "bar"

        def __init__(self, members):
            self.members = members

    # noinspection PyArgumentList
    subject = MyDeclarative()
    assert dict(foo='foo') == subject.members


def test_required_parameter():
    with pytest.raises(TypeError) as e:
        declarative()

    assert str(
        e.value) == "The @declarative decorator needs either a member_class parameter or an is_member check function (or both)"


# noinspection PyUnusedLocal
def test_find_member_fail_on_tuple():
    with pytest.raises(TypeError) as e:
        class MyDeclarative(Declarative):
            foo = Member(foo='bar'),

    assert str(e.value) == "'foo' is a one-tuple containing what we are looking for.  " \
                           "Trailing comma much?  Don't... just don't."


# noinspection PyUnusedLocal
def test_find_member_fail_on_tuple_with_is_member_lambda():
    with pytest.raises(TypeError) as e:
        @declarative(
            is_member=lambda obj: isinstance(obj, Member)
        )
        class MyDeclarative:
            foo = Member(foo='bar'),

    assert str(e.value) == "'foo' is a one-tuple containing what we are looking for.  " \
                           "Trailing comma much?  Don't... just don't."


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
    class MyDeclarative:
        # noinspection PyUnusedLocal
        @my_wrapper
        def __init__(self, members):
            super(MyDeclarative, self).__init__()

    assert MyDeclarative().__init__.my_attribute == 17


def test_constructor_init_hook_attribute_retention():
    def my_wrapper(f):
        f.my_attribute = 17
        return f

    @declarative(str, add_init_kwargs=False, sort_key=lambda x: x)
    class MyDeclarative:
        @my_wrapper
        def __init__(self):
            """foo"""
            super(MyDeclarative, self).__init__()

    assert MyDeclarative().__init__.my_attribute == 17
    assert MyDeclarative.__init__.__doc__ == 'foo'


def test_sort_key():
    @declarative(str, sort_key=lambda x: x)
    class Ok:
        a = "y"
        b = "x"

        def __init__(self, members):
            assert list(members.keys()) == ['b', 'a']

    # noinspection PyArgumentList
    Ok()


def test_find_members_not_shadowed_by_meta():
    class MyDeclarative(Declarative):
        foo = Member(foo='bar')

        class Meta:
            pass

    # noinspection PyArgumentList
    subject = MyDeclarative()
    assert subject.members == dict(foo=Member(foo='bar'))


def test_find_members_inherited():
    class MyDeclarative(Declarative):
        foo = Member(foo='bar')

    class MyDeclarativeSubclass(MyDeclarative):
        bar = Member(foo='baz')

    # noinspection PyArgumentList
    subject = MyDeclarativeSubclass()
    assert list(subject.members.items()) == [
        ('foo', Member(foo='bar')),
        ('bar', Member(foo='baz')),
    ]


def test_isolated_inheritance():
    @declarative(int, add_init_kwargs=False, sort_key=lambda x: x)
    class Base:
        a = 1

    class Foo(Base):
        b = 2

    class Bar(Base):
        c = 3

    assert list(Base.get_declared().items()) == [('a', 1)]
    assert list(Foo.get_declared().items()) == [('a', 1), ('b', 2)]
    assert list(Bar.get_declared().items()) == [('a', 1), ('c', 3)]


def test_find_members_from_base():
    @declarative(Member)
    class Base:
        foo = Member(foo='foo')

    class Sub(Base):
        bar = Member(bar='bar')

    assert list(Sub._declarative_members.items()) == [
        ('foo', Member(foo='foo')),
        ('bar', Member(bar='bar')),
    ]


def test_find_members_shadow():
    @declarative(Member)
    class Base:
        foo = Member(bar='bar')

    class Sub(Base):
        foo = Member(bar='baz')

    assert Sub._declarative_members == dict(foo=Member(bar='baz'))


def test_member_attribute_naming():
    @declarative(Member, 'foo')
    class MyBaseDeclarative:
        def __init__(self, foo):
            self.foo = foo

    class MyDeclarative(MyBaseDeclarative):
        bar = Member(baz='buzz')

    # noinspection PyArgumentList
    subject = MyDeclarative()
    assert subject.foo == dict(bar=Member(baz='buzz'))


def test_string_members():
    @declarative(str, sort_key=lambda x: x)
    class MyDeclarative:
        foo = 'bar'

    assert MyDeclarative.get_declared() == dict(foo='bar')


def test_declarative_and_meta():
    @with_meta
    @declarative(str, sort_key=lambda x: x)
    class Foo:
        foo = 'foo'

        class Meta:
            bar = 'bar'

        def __init__(self, members, bar):
            assert members == dict(foo='foo')
            assert bar == 'bar'

    # noinspection PyArgumentList
    Foo()


def test_declarative_and_meta_subclass_no_constructor_hack_workaround():
    @declarative(str, sort_key=lambda x: x)
    class Foo:

        def __init__(self, members, bar):
            assert members == dict()
            assert bar == 'bar'

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
            assert members == dict(foo='foo')
            assert bar == 'bar'

    # noinspection PyArgumentList
    Foo()


def test_multiple_types():
    @declarative(int, 'ints', sort_key=lambda x: x)
    @declarative(str, 'strs', sort_key=lambda x: x)
    class Foo:
        a = 1
        b = "b"

        def __init__(self, ints, strs):
            assert ints == dict(a=1)
            assert strs == dict(b='b')

    # noinspection PyArgumentList
    Foo()


def test_multiple_types_inheritance():
    @declarative(int, 'ints', sort_key=lambda x: x)
    class Foo:
        i = 1
        a = 'a'

        def __init__(self, ints):
            assert list(ints.items()) == [('i', 1), ('j', 2), ('k', 3)]
            super(Foo, self).__init__()

    @declarative(str, 'strs', sort_key=lambda x: x)
    class Bar(Foo):
        j = 2
        b = "b"

        def __init__(self, strs):
            assert list(strs.items()) == [('b', 'b'), ('c', 'c')]
            # noinspection PyArgumentList
            super(Bar, self).__init__()

    class Baz(Bar):
        k = 3
        c = 'c'

        def __init__(self):
            # noinspection PyArgumentList
            super(Baz, self).__init__()

    Baz()


def test_add_args_to_init_call():
    class C:
        def __init__(self, x, y=None):
            self.x = x
            self.y = y

    add_args_to_init_call(C, lambda self: dict(x=17))

    # noinspection PyArgumentList
    c = C()
    assert c.x == 17
    assert c.y is None

    add_args_to_init_call(C, lambda self: dict(y=42))

    # noinspection PyArgumentList
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

    # noinspection PyArgumentList
    a = C()
    # noinspection PyArgumentList
    C()

    assert a.x == ['foo']  # Only added once for each instance


def test_copy_of_attributes():
    @declarative(list, sort_key=lambda x: x)
    class C:
        x = []

        # noinspection PyUnusedLocal
        def __init__(self, members):
            pass

    # noinspection PyArgumentList
    a = C()
    # noinspection PyArgumentList
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

    # noinspection PyPep8Naming
    Bar = declarative(str)(Foo)

    assert Bar.__dict__ is not Foo.__dict__
    # noinspection PyUnresolvedReferences
    assert Bar.__weakref__ is None or Bar.__weakref__ is not Foo.__weakref__


def test_wrap_with_meta_preserves_doc_string():
    @with_meta
    class Foo(Struct):
        # noinspection PyMissingConstructor
        def __init__(self):
            """foo"""

    assert Foo.__init__.__doc__ == 'foo'


def test_get_members_error_message():
    with pytest.raises(TypeError) as e:
        get_members(None)

    assert str(e.value) == "get_members either needs a member_class parameter or an is_member check function (or both)"
