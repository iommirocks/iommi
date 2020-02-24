Architecture
============

.. contents::
    :local:

Execution phases
----------------

`Part` objects have this life cycle:

1. Definition
2. Construction
3. `Bind`_
4. Traversal (e.g. render to html, respond to ajax, custom report creation)


At definition time we can have just a bunch of dicts. This is really a stacking and merging of namespaces.

At construction time we take the definition namespaces and materialize them into proper :code:`Table`, :code:`Column`, :code:`Form` etc objects.

At bind time we:

- register parents
- evaluate callables into real values
- invoke any user defined :code:`on_bind` handlers

At traversal time we are good to go and can now invoke the final methods of all objects. We can now render html, respond to ajax, etc.


.. _bind:

Bind
----

"Bind" is when we take an abstract declaration of what we want and convert it into the "bound" concrete expression of that. It consists of these parts:

1. Copy of the part. (We set a member `_declared` to point to the original definition if you need to refer to it for debugging purposes.)
2. Set the `parent` and set `_is_bound` to `True`
3. Style application
4. Call the parts `on_bind` method

The parts are responsible for calling `bind(parent=self)` on all their children in `on_bind`.

The root object of the graph is initialized with `bind(request=request)`. Only one object can be the root.

.. _dispatching:

Namespace dispatching
---------------------

I've already hinted at this above in the example where we do
``columns__foo__include=False``. This is an example of the powerful
namespace dispatch mechanism from tri.declarative. It's inspired by the
query syntax of Django where you use ``__`` to jump namespace. (If
you're not familiar with Django, here's the gist of it: you can do
``Table.objects.filter(foreign_key__column='foo')``
to filter.) We really like this style and have expanded on it. It
enables functions to expose the *full* API of functions it calls while
still keeping the code simple. Here's a contrived example:

.. code:: python

    from tri_declarative import dispatch, EMPTY


    @dispatch(
        b__x=1,  # these are default values. "b" here is implicitly
                 # defining a namespace with a member "x" set to 1
        c__y=2,
    )
    def a(foo, b, c):
        print('foo:', foo)
        some_function(**b)
        another_function(**c)


    @dispatch (
        d=EMPTY,  # explicit namespace
    )
    def some_function(x, d):
        print('x:', x)
        another_function(**d)


    def another_function(y=None, z=None):
        if y:
            print('y:', y)
        if z:
            print('z:', z)

    # now to call a()!
    a('q')
    # output:
    # foo: q
    # x: 1
    # y: 2


    a('q', b__x=5)
    # foo: q
    # x: 5
    # y: 2

    a('q', b__d__z=5)
    # foo: q
    # x: 1
    # z: 5
    # y: 2

This is really useful for the `Table` class as it means we can expose the full
feature set of the underling `Query` and `Form` classes by just
dispatching keyword arguments downstream. It also enables us to bundle
commonly used features in what we call "shortcuts", which are pre-packaged sets of defaults.
