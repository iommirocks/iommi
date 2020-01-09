Architecture overview
=====================

Declarative/programmatic hybrid API
-----------------------------------

The ``@declarative``, ``@with_meta`` and ``@creation_ordered``
decorators from tri.declarative enables us to very easily write an API
that can look both like a normal simple python API:

.. code:: python

    my_table = Table(
        columns=[
            Column(name='foo'),
            Column('bar'),
        ],
        sortable=False)

This code is hopefully pretty self explanatory. But the cool thing is
that we can do the exact same thing with a declarative style:

.. code:: python

    class MyTable(Table):
        foo = Column()
        bar = Column()

        class Meta:
            sortable = False

    my_table = MyTable()

This style can be much more readable. There's a subtle different though
between the first and second styles: the second is really a way to
declare defaults, not hard coding values. This means we can create
instances of the class and set the values in the call to the
constructor:

.. code:: python

    my_table = MyTable(
        column__foo__show=False,  # <- hides the column foo
        sortable=True,            # <- turns on sorting again
    )

...without having to create a new class inheriting from ``MyTable``. So
the API keeps all the power of the simple style and also getting the
nice syntax of a declarative API.

Namespace dispatching
---------------------

I've already hinted at this above in the example where we do
``column__foo__show=False``. This is an example of the powerful
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

This is really useful for the Table class as it means we can expose the full
feature set of the underling Query and Form classes by just
dispatching keyword arguments downstream. It also enables us to bundle
commonly used features in what we call "shortcuts", which are pre
packaged sets of defaults.
