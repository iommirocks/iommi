.. image:: https://travis-ci.org/TriOptima/tri.declarative.svg?branch=master
    :target: https://travis-ci.org/TriOptima/tri.declarative

tri.declarative
===============

tri.declarative contains class decorators to define classes with subclass semantics in the style of django Model classes.


Example
-------

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


is roughly equivalent to:

.. code:: python

    class Foo(object):
        def __init__(self, foo, members):
            assert foo == 'foo'
            assert members == OrderedDict([('bar', 'barbar'), ('baz', 'bazbaz')])

    f = Foo(foo='foo', members=OrderedDict([('bar', 'barbar'), ('baz', 'bazbaz')])



Running tests
-------------

You need tox installed then just `make test`.


License
-------

BSD


Documentation
-------------

http://declarative.readthedocs.org.
