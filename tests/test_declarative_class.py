from collections import OrderedDict
from tri.struct import Struct

from tri.declarative import creation_ordered, declarative


@creation_ordered
class Member(Struct):
    pass


@declarative(Member)
class Declarative(object):
    def __init__(self, members):
        self.members = members


def test_constructor_noop():

    subject = Declarative(members={'foo': Member(foo='bar')})

    assert subject.members == {'foo': Member(foo='bar')}


def test_find_members():

    class MyDeclarative(Declarative):
        foo = Member(foo='bar')

    subject = MyDeclarative()
    assert OrderedDict([('foo', Member(foo='bar'))]) == subject.members


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


def test_find_members_from_base():

    @declarative(Member)
    class Base(object):
        foo = Member(foo='foo')

    class Sub(Base):
        bar = Member(bar='bar')

    assert OrderedDict([('foo', Member(foo='foo')), ('bar', Member(bar='bar'))]) == Sub.Meta.members


def test_find_members_shadow():
    @declarative(Member)
    class Base(object):
        foo = Member(bar='bar')

    class Sub(Base):
        foo = Member(bar='baz')

    assert OrderedDict([('foo', Member(bar='baz'))]) == Sub.Meta.members


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

    @declarative(str)
    class Declarative(object):

        foo = 'bar'

    assert OrderedDict([('foo', 'bar')]) == Declarative.Meta.members


def test_multiple_types():

    @declarative(int, 'ints')
    @declarative(str, 'strs')
    class Foo(object):
        a = 1
        b = "b"

        def __init__(self, ints, strs):
            assert OrderedDict([('a', 1)]) == ints
            assert OrderedDict([('b', 'b')]) == strs

    Foo()


def test_multiple_types_inheritance():

    @declarative(int, 'ints')
    class Foo(object):
        i = 1
        a = 'a'

        def __init__(self, **kwargs):
            assert OrderedDict([('i', 1), ('j', 2), ('k', 3)]) == kwargs['ints']
            super(Foo, self).__init__()

    @declarative(str, 'strs')
    class Bar(Foo):
        j = 2
        b = "b"

        def __init__(self, **kwargs):
            assert OrderedDict([('i', 1), ('j', 2), ('k', 3)]) == kwargs['ints']
            assert OrderedDict([('b', 'b'), ('c', 'c')]) == kwargs['strs']
            super(Bar, self).__init__()

    class Baz(Bar):
        k = 3
        c = 'c'

        def __init__(self):
            super(Baz, self).__init__()

    Baz()
