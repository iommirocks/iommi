.. image:: https://travis-ci.org/TriOptima/tri.declarative.svg?branch=master
    :target: https://travis-ci.org/TriOptima/tri.declarative
.. image:: http://codecov.io/github/TriOptima/tri.declarative/coverage.svg?branch=master
    :target: http://codecov.io/github/TriOptima/tri.declarative?branch=master
    
tri.declarative
===============

tri.declarative contains tools that make it easy to write declarative code. This includes:

- `class decorators`_ to define classes with subclass semantics in the style of django Model classes
- recursively evaluating_ embedded lambda expressions in complex data structures
- recursively filtering_ of complex data structures
- `keyword argument dispatching`_
- `get/set attribute given a path string`_ (e.g. 'foo__bar__baz')


Class decorators
----------------

With just a few lines of code, turn your API from:

.. code-block:: python

    quux = Foo(things=[Bar(name='a', param=1), Bar(name='b', param=2), Bar(name='c', param=2)], baz=3)

into:

.. code-block:: python

    class Quux(Foo):
        a = Bar(param=1)
        b = Bar(param=2)
        c = Bar(param=2)

        class Meta:
            baz = 3

And you can still use the first style when it's more convenient!

More detailed usage examples on `@declarative`_ below.


Evaluating
----------

.. code-block:: python

    d = dict(
        foo=lambda x: x*2,
        bar=lambda y: y+5,
        baz=[
            foo=lambda x: x*6,
        ],
    )

    # evaluate only one level
    assert evaluate(d, x=2) == dict(
        foo=4,
        bar=lambda y: y+5,  # this function doesn't match the signature so isn't evaluated
        baz=[
            foo=lambda x: x*6,  # one level down so isn't evaluated
        ],
    )

    # evaluate recursively
    assert evaluate_recursive(d, x=2) == dict(
        foo=4,
        bar=lambda y: y+5,  # this function doesn't match the signature so isn't evaluated
        baz=[
            foo=12,
        ],
    )


Filtering
---------

.. code-block:: python

    d = dict(
        foo=dict(
            show=False,
            x=1,
        ),
        bar=dict(
            show=True,
            x=2,
        ),
    )

    assert filter_show_recursive(d) == dict(
        bar=dict(
            show=True,
            x=2,
        ),
    )


Keyword argument dispatching
----------------------------

@dispatch:

.. code-block:: python

    @dispatch(
        bar={},
        baz__foo=2)
    def foo(bar, baz):
        do_bar(**bar)
        do_baz(**baz)



Get/set attribute given a path string
-------------------------------------

.. code-block:: python

    class Foo(object):
        def __init__(a):
            self.a = a

    class Bar(object):
        def __init__(b):
            self.b = b

    class Baz(object):
        def __init__(c):
            self.c = c

    x = Foo(Bar(Baz(c=3)))

    assert getattr_path(x, 'a__b__c') == 3

    assert setattr_path(x, 'a__b__c', 10)
    assert getattr_path(x, 'a__b__c') == 10


Running tests
-------------

You need tox installed then just `make test`.


License
-------

BSD


Documentation
-------------

https://trideclarative.readthedocs.org.


Usage
=====


@declarative
------------

In the example below, the :code:`@declarative(str)` decorator will ensure that all :code:`str` members of class Foo will be
collected and sent as :code:`members` constructor keyword argument.

.. code-block:: python

    from tri.declarative import declarative

    @declarative(str)
    class Foo(object):
        bar = 'barbar'
        baz = 'bazbaz'
        boink = 17

        def __init__(self, members):
            assert members['bar'] == 'barbar'
            assert members['baz'] == 'bazbaz'
            assert 'boink' not in members

    f = Foo()

The value of the :code:`members` argument will also be collected from sub-classes:

.. code-block:: python

    from tri.declarative import declarative

    @declarative(str)
    class Foo(object):

        def __init__(self, members):
            assert members['bar'] == 'barbar'
            assert members['baz'] == 'bazbaz'

    class MyFoo(Foo):
        bar = 'barbar'
        baz = 'bazbaz'

        def __init__(self):
            super(MyFoo, self).__init__()

    f = MyFoo()


The :code:`members` argument can be given another name (:code:`things` in the example below).

.. code-block:: python

    from tri.declarative.declarative import declarative

    @declarative(str, 'things')
    class Foo(object):

        bar = 'barbar'

        def __init__(self, **kwargs):
            assert 'things' in kwargs
            assert kwargs['things']['bar'] == 'barbar'

    f = Foo()


Note that the collected dict is an :code:`OrderedDict` and will be ordered by class inheritance and by using
:code:`sorted` of the values within each class. (In the 'str' example, :code:`sorted` yields in alphabetical order).

Also note that the collection of *class* members based on their class does *not* interfere with *instance* constructor
argument of the same type.

.. code-block:: python

    from tri.declarative import declarative

    @declarative(str)
    class Foo(object):
        charlie = '3'
        alice = '1'

        def __init__(self, members):
            assert members == OrderedDict([('alice', '1'), ('charlie', '3'),
                                           ('bob', '2'), ('dave', '4'),
                                           ('eric', '5')])
            assert 'animal' not in members


    class MyFoo(Foo):
        dave = '4'
        bob = '2'

    class MyOtherFoo(MyFoo):
        eric = '5'

        def __init__(self, animal)
            assert animal == 'elephant'

    f = MyOtherFoo('elephant')


@creation_ordered
-----------------

Class decorator that ensures that instances will be ordered after creation order when sorted.

This is useful for classes intended to be used as members of a :code:`@declarative` class when member order matters.

.. code-block:: python

    from tri.declarative import creation_ordered

    @creation_ordered
    class Thing(object):
        pass

    t1 = Thing()
    t2 = Thing()
    t3 = Thing()

    assert sorted([t2, t3, t1]) == [t1, t2, t3]


Real world use-case
-------------------

Below is a more complete example of using @declarative:

.. code-block:: python

    from tri.declarative import declarative, creation_ordered


    @creation_ordered
    class Field(object):
        pass


    class IntField(Field):
        def render(self, value):
            return '%s' % value


    class StringField(Field):
        def render(self, value):
            return "'%s'" % value


    @declarative(Field, 'table_fields')
    class SimpleSQLModel(object):

        def __init__(self, **kwargs):
            self.table_fields = kwargs.pop('table_fields')

            for name in kwargs:
                assert name in self.table_fields
                setattr(self, name, kwargs[name])

        def insert_statement(self):
            return 'INSERT INTO %s(%s) VALUES (%s)' % (self.__class__.__name__,
                                                     ', '.join(self.table_fields.keys()),
                                                     ', '.join([field.render(getattr(self, name))
                                                                for name, field in self.table_fields.items()]))


    class User(SimpleSQLModel):
        username = StringField()
        password = StringField()
        age = IntField()


    my_user = User(username='Bruce_Wayne', password='Batman', age=42)
    assert my_user.username == 'Bruce_Wayne'
    assert my_user.password == 'Batman'
    assert my_user.insert_statement() == "INSERT INTO User(username, password, age) VALUES ('Bruce_Wayne', 'Batman', 42)"

    # Fields are ordered by creation time (due to having used the @creation_ordered decorator)
    assert my_user.get_meta().table_fields.keys() == ['username', 'password', 'age']


@with_meta
----------

Class decorator to enable a class (and it's sub-classes) to have a 'Meta' class attribute.

The members of the Meta class will be injected as arguments to constructor calls. e.g.:

.. code-block:: python

    from tri.declarative import with_meta

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


The passing of the merged name space to the constructor is optional.
It can be disabled by passing :code:`add_init_kwargs=False` to the decorator.

.. code-block:: python

    from tri.declarative import with_meta

    @with_meta(add_init_kwargs=False)
    class Foo(object):
        class Meta:
            foo = 'bar'

    Foo()  # No longer crashes
    assert Foo().get_meta() == {'foo': 'bar'}


Another example:

.. code-block:: python

    from tri.declarative import with_meta

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
